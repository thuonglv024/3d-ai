"""Orders and Checkout module for MORPH Studio.
Handles SQLite DB persistence, price & shipping quotes, order creation with idempotency,
and authenticated order lookup via secret token.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import secrets
import sqlite3
from typing import Any, Optional, Union
import uuid


from fastapi import APIRouter, Body, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, AliasChoices

from .catalog import PRODUCTS
from .config import ROOT
from .db import (
    get_db_connection,
    get_db_path,
    get_product_by_slug_or_id,
    run_migrations,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])

# Constants
FREE_SHIPPING_THRESHOLD_VND = 500000
STANDARD_SHIPPING_FEE_VND = 30000

STATUS_LABELS = {
    "received": "Đã tiếp nhận",
    "pending_confirmation": "Chờ xác nhận",
    "confirmed": "Đã xác nhận",
    "shipping": "Đang giao hàng",
    "completed": "Hoàn thành",
    "cancelled": "Đã hủy",
}


def init_db(db_path: Optional[Path | str] = None) -> None:
    """Initialize orders and catalog database schema, and seed catalog if empty."""
    path = Path(db_path) if db_path else get_db_path()
    run_migrations(path)

    # If products table has no rows, seed baseline catalog
    with get_db_connection(path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            from .seed import seed_catalog
            seed_catalog(db_path=path)


# Ensure database tables exist at import time
try:
    init_db()
except Exception as exc:
    logger.warning("Auto-init orders DB deferred: %s", exc)


# Helper & Validation Functions
def generate_order_code() -> str:
    """Generates order code matching MPH-YYYYMMDD-XXXX."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(2).upper()
    return f"MPH-{date_part}-{suffix}"


def validate_vn_phone(phone: str) -> str:
    """
    Validates a Vietnamese phone number.
    Returns cleaned phone number starting with 0.
    Raises ValueError if invalid.
    """
    if not phone or not isinstance(phone, str):
        raise ValueError("Số điện thoại không được để trống.")

    cleaned = re.sub(r"[\s\.\-\(\)]", "", phone.strip())
    if cleaned.startswith("+84"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("84") and len(cleaned) in (11, 12):
        cleaned = "0" + cleaned[2:]

    if not cleaned.isdigit():
        raise ValueError("Số điện thoại chỉ được chứa các chữ số.")

    if not (9 <= len(cleaned) <= 11):
        raise ValueError("Số điện thoại Việt Nam phải có từ 9 đến 11 chữ số.")

    if not cleaned.startswith("0"):
        raise ValueError("Số điện thoại Việt Nam phải bắt đầu bằng 0 hoặc +84.")

    return cleaned


def find_product(product_id: str, db_path: Optional[Path | str] = None) -> Optional[dict]:
    """Finds a product in catalog by id or slug from SQLite database."""
    return get_product_by_slug_or_id(product_id, db_path=db_path)


def get_product_colors(product: dict) -> list[str]:
    """Extracts valid color names from a product record."""
    colors = []
    for c in product.get("colors", []):
        if isinstance(c, dict) and "name" in c:
            colors.append(c["name"])
        elif isinstance(c, str):
            colors.append(c)
    if not colors and product.get("color"):
        colors.append(product["color"])
    return colors


def validate_cart_item(item: Any, db_path: Optional[Path | str] = None) -> dict:
    """Validates an order item against the product catalog and variant stock in SQLite DB."""
    if isinstance(item, dict):
        pid = item.get("productId") or item.get("product_id")
        color_in = item.get("color", "")
        size_in = item.get("size", "")
        quantity_in = item.get("quantity", 1)
    else:
        pid = getattr(item, "productId", None) or getattr(item, "product_id", None)
        color_in = getattr(item, "color", "")
        size_in = getattr(item, "size", "")
        quantity_in = getattr(item, "quantity", 1)

    if not pid or not str(pid).strip():
        raise HTTPException(status_code=400, detail="Mã sản phẩm (productId) không được để trống.")

    product = find_product(pid, db_path=db_path)
    if not product:
        raise HTTPException(status_code=400, detail=f"Sản phẩm '{pid}' không tồn tại trong danh mục.")

    if not isinstance(quantity_in, int) or quantity_in < 1:
        raise HTTPException(status_code=400, detail="Số lượng sản phẩm phải là số nguyên lớn hơn hoặc bằng 1.")

    # Validate product active status in DB
    with get_db_connection(db_path) as conn:
        p_row = conn.execute("SELECT id, name, is_active, price FROM products WHERE id = ?", (product["id"],)).fetchone()
        if not p_row or not p_row["is_active"]:
            raise HTTPException(status_code=400, detail=f"Sản phẩm '{product.get('name')}' hiện không còn kinh doanh.")

        # Validate color
        avail_colors = get_product_colors(product)
        color_clean = str(color_in).strip().lower()
        matched_color = None
        for ac in avail_colors:
            if ac.strip().lower() == color_clean:
                matched_color = ac
                break
        if not matched_color:
            color_options = ", ".join(avail_colors) if avail_colors else "Mặc định"
            raise HTTPException(
                status_code=400,
                detail=f"Màu sắc '{color_in}' không hợp lệ cho sản phẩm '{product.get('name')}'. Màu hiện có: {color_options}."
            )

        # Validate size
        avail_sizes = product.get("sizes", [])
        size_clean = str(size_in).strip().upper()
        matched_size = None
        for asize in avail_sizes:
            if asize.strip().upper() == size_clean:
                matched_size = asize
                break
        if not matched_size:
            size_options = ", ".join(avail_sizes) if avail_sizes else "Free size"
            raise HTTPException(
                status_code=400,
                detail=f"Kích thước '{size_in}' không hợp lệ cho sản phẩm '{product.get('name')}'. Kích thước hiện có: {size_options}."
            )

        # Query variant row for exact variant ID, active state and stock
        v_row = conn.execute(
            """
            SELECT id, sku, color_name, size, stock, is_active
            FROM product_variants
            WHERE product_id = ? AND LOWER(color_name) = LOWER(?) AND UPPER(size) = UPPER(?)
            LIMIT 1
            """,
            (product["id"], matched_color, matched_size)
        ).fetchone()

        if not v_row or not v_row["is_active"]:
            raise HTTPException(
                status_code=400,
                detail=f"Biến thể màu '{matched_color}', kích thước '{matched_size}' của sản phẩm '{product.get('name')}' hiện không khả dụng."
            )

        if v_row["stock"] < quantity_in:
            raise HTTPException(
                status_code=400,
                detail=f"Sản phẩm '{product.get('name')}' ({matched_color} / {matched_size}) không đủ tồn kho (chỉ còn {v_row['stock']} sản phẩm trong kho, bạn đặt {quantity_in})."
            )

        variant_id = v_row["id"]
        variant_sku = v_row["sku"]
        variant_stock = v_row["stock"]
        unit_price = int(p_row["price"])

    subtotal = unit_price * quantity_in
    image = product.get("image") or (product.get("gallery") or [""])[0]

    return {
        "productId": product.get("id"),
        "product_id": product.get("id"),
        "variantId": variant_id,
        "variant_id": variant_id,
        "sku": variant_sku,
        "stock": variant_stock,
        "slug": product.get("slug", product.get("id")),
        "name": product.get("name"),
        "color": matched_color,
        "size": matched_size,
        "image": image,
        "unit_price_vnd": unit_price,
        "price": unit_price,
        "quantity": quantity_in,
        "subtotal_vnd": subtotal,
        "subtotal": subtotal,
    }


def validate_and_aggregate_cart_items(items: list[Any], db_path: Optional[Path | str] = None) -> list[dict]:
    """
    Validates cart items and verifies combined quantity per variant does not exceed available stock.
    """
    if not items:
        raise HTTPException(status_code=400, detail="Danh sách sản phẩm không được để trống.")

    validated_items = [validate_cart_item(it, db_path=db_path) for it in items]

    # Aggregate quantities per variant_id
    totals_by_variant: dict[str, int] = {}
    for it in validated_items:
        v_id = it["variant_id"]
        totals_by_variant[v_id] = totals_by_variant.get(v_id, 0) + it["quantity"]

    for it in validated_items:
        v_id = it["variant_id"]
        req_total = totals_by_variant[v_id]
        if req_total > it["stock"]:
            raise HTTPException(
                status_code=400,
                detail=f"Sản phẩm '{it['name']}' ({it['color']} / {it['size']}) không đủ tồn kho (chỉ còn {it['stock']} sản phẩm trong kho, tổng số lượng trong giỏ là {req_total})."
            )

    return validated_items



def calculate_totals(validated_items: list[dict]) -> tuple[int, int, int]:
    """Calculates subtotal, shipping fee, and total in VND."""
    subtotal_vnd = sum(item["subtotal_vnd"] for item in validated_items)
    shipping_fee_vnd = 0 if subtotal_vnd >= FREE_SHIPPING_THRESHOLD_VND else STANDARD_SHIPPING_FEE_VND
    total_vnd = subtotal_vnd + shipping_fee_vnd
    return subtotal_vnd, shipping_fee_vnd, total_vnd


def _build_order_dict(order_row: sqlite3.Row, item_rows: list[sqlite3.Row]) -> dict:
    """Builds user-facing order dict (without the secret token)."""
    items = [
        {
            "id": r["id"],
            "productId": r["product_id"],
            "product_id": r["product_id"],
            "slug": r["product_slug"],
            "name": r["product_name"],
            "color": r["color"],
            "size": r["size"],
            "image": r["image"],
            "unit_price_vnd": r["unit_price_vnd"],
            "price": r["unit_price_vnd"],
            "quantity": r["quantity"],
            "subtotal_vnd": r["subtotal_vnd"],
            "subtotal": r["subtotal_vnd"],
        }
        for r in item_rows
    ]

    cust_note = order_row["customer_note"]
    return {
        "id": order_row["id"],
        "order_code": order_row["order_code"],
        "status": order_row["status"],
        "status_label": order_row["status_label"],
        "customer": {
            "name": order_row["customer_name"],
            "phone": order_row["customer_phone"],
            "email": order_row["customer_email"],
            "address": order_row["customer_address"],
            "note": cust_note,
            "notes": cust_note,
        },
        "items": items,
        "subtotal_vnd": order_row["subtotal_vnd"],
        "shipping_fee_vnd": order_row["shipping_fee_vnd"],
        "total_vnd": order_row["total_vnd"],
        "subtotal": order_row["subtotal_vnd"],
        "shipping_fee": order_row["shipping_fee_vnd"],
        "total": order_row["total_vnd"],
        "note": cust_note,
        "notes": cust_note,
        "created_at": order_row["created_at"],
        "updated_at": order_row["updated_at"],
    }


def get_order_by_idempotency_key(key: str, db_path: Optional[Path | str] = None) -> Optional[dict]:
    """Retrieves existing order, token, and payload_hash by idempotency key."""
    if not key or not str(key).strip():
        return None
    with get_db_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM orders WHERE idempotency_key = ?", (str(key).strip(),))
        row = cursor.fetchone()
        if not row:
            return None
        items_cursor = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (row["id"],))
        item_rows = items_cursor.fetchall()
        order_dict = _build_order_dict(row, item_rows)
        payload_hash = row["payload_hash"] if "payload_hash" in row.keys() else None
        return {
            "order": order_dict,
            "token": row["token"],
            "payload_hash": payload_hash,
        }


def get_order_by_id_or_code(identifier: str, token: str, db_path: Optional[Path | str] = None) -> Optional[dict]:
    """Retrieves order with timing-safe token authentication."""
    if not identifier or not token:
        return None
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM orders WHERE id = ? OR order_code = ?",
            (str(identifier).strip(), str(identifier).strip())
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(row["token"], str(token).strip()):
            return None

        items_cursor = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (row["id"],))
        item_rows = items_cursor.fetchall()
        return _build_order_dict(row, item_rows)


# Pydantic Schemas
class OrderItemInput(BaseModel):
    productId: str = Field(..., validation_alias=AliasChoices("productId", "product_id"))
    color: str
    size: str
    quantity: int = Field(default=1, ge=1)

    model_config = ConfigDict(populate_by_name=True)


class QuoteRequest(BaseModel):
    items: list[OrderItemInput]

    model_config = ConfigDict(populate_by_name=True)


class CustomerInput(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    address: str
    note: Optional[str] = Field(None, validation_alias=AliasChoices("note", "notes"))

    model_config = ConfigDict(populate_by_name=True)


class CreateOrderRequest(BaseModel):
    idempotency_key: Optional[str] = None
    customer: CustomerInput
    items: list[OrderItemInput]
    note: Optional[str] = Field(None, validation_alias=AliasChoices("note", "notes"))

    model_config = ConfigDict(populate_by_name=True)


def compute_payload_fingerprint(payload: CreateOrderRequest) -> str:
    """Computes a deterministic SHA-256 fingerprint of the order payload."""
    cust = payload.customer
    effective_note = (payload.note or cust.note or "").strip()
    cust_data = {
        "name": (cust.name or "").strip(),
        "phone": re.sub(r"[\s\.\-\(\)]", "", (cust.phone or "").strip()),
        "email": (cust.email or "").strip().lower() if cust.email else None,
        "address": (cust.address or "").strip(),
        "note": effective_note,
    }
    items_data = [
        {
            "productId": str(it.productId).strip(),
            "color": str(it.color).strip().lower(),
            "size": str(it.size).strip().upper(),
            "quantity": int(it.quantity),
        }
        for it in payload.items
    ]
    items_data.sort(key=lambda x: (x["productId"], x["color"], x["size"], x["quantity"]))
    canonical = json.dumps({"customer": cust_data, "items": items_data}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# API Routes
@router.post("/quote")
def quote_order(payload: Union[QuoteRequest, list[OrderItemInput]] = Body(...)):
    """
    Calculates subtotal, shipping fee, and total in VND for a list of items.
    Validates each product, color variant, size variant, and quantity against catalog.
    Prices are strictly derived from SQLite products table.
    """
    if isinstance(payload, QuoteRequest):
        items = payload.items
    elif isinstance(payload, list):
        items = payload
    else:
        raise HTTPException(status_code=400, detail="Dữ liệu giỏ hàng không hợp lệ.")

    if not items:
        raise HTTPException(status_code=400, detail="Danh sách sản phẩm không được để trống.")

    validated_items = validate_and_aggregate_cart_items(items)
    subtotal_vnd, shipping_fee_vnd, total_vnd = calculate_totals(validated_items)

    return {
        "subtotal_vnd": subtotal_vnd,
        "shipping_fee_vnd": shipping_fee_vnd,
        "total_vnd": total_vnd,
        "free_shipping_threshold_vnd": FREE_SHIPPING_THRESHOLD_VND,
        "items": validated_items,
        # Convenience aliases
        "subtotal": subtotal_vnd,
        "shipping_fee": shipping_fee_vnd,
        "total": total_vnd,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_order(
    request: Request,
    payload: CreateOrderRequest,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Creates a new checkout order with atomic stock deduction and idempotency protection.
    Returns the created order and its secret access token.
    """
    idem_key = payload.idempotency_key or idempotency_key_header
    if idem_key:
        idem_key = idem_key.strip() or None

    payload_hash = compute_payload_fingerprint(payload)

    # Idempotency check:
    if idem_key:
        existing = get_order_by_idempotency_key(idem_key)
        if existing:
            stored_hash = existing.get("payload_hash")
            if stored_hash and stored_hash != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key đã được sử dụng với nội dung đơn hàng khác."
                )
            order_dict = existing["order"]
            token = existing["token"]
            return {
                "order": order_dict,
                "token": token,
                **order_dict,
            }

    # Validate Customer Data
    cust = payload.customer
    name = (cust.name or "").strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Tên khách hàng phải có ít nhất 2 ký tự.")

    try:
        clean_phone = validate_vn_phone(cust.phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    email = None
    if cust.email and cust.email.strip():
        email = cust.email.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise HTTPException(status_code=400, detail="Địa chỉ email không hợp lệ.")

    address = (cust.address or "").strip()
    if len(address) < 5:
        raise HTTPException(status_code=400, detail="Địa chỉ nhận hàng phải có ít nhất 5 ký tự.")

    note = (payload.note or cust.note or "").strip() or None

    # Validate Items & Stock
    if not payload.items:
        raise HTTPException(status_code=400, detail="Đơn hàng phải có ít nhất 1 sản phẩm.")

    validated_items = validate_and_aggregate_cart_items(payload.items)
    subtotal_vnd, shipping_fee_vnd, total_vnd = calculate_totals(validated_items)

    # Order Metadata
    order_id = f"ord_{uuid.uuid4().hex[:16]}"
    order_code = generate_order_code()
    token = secrets.token_urlsafe(24)
    order_status = "received"
    status_label = STATUS_LABELS.get(order_status, "Đã tiếp nhận")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Aggregate quantities per variant for atomic deduction
    variant_quantities: dict[str, tuple[int, str, str, str]] = {}
    for it in validated_items:
        v_id = it["variant_id"]
        if v_id not in variant_quantities:
            variant_quantities[v_id] = (it["quantity"], it["name"], it["color"], it["size"])
        else:
            prev_qty, n, c, s = variant_quantities[v_id]
            variant_quantities[v_id] = (prev_qty + it["quantity"], n, c, s)

    # Atomic DB Insertion and Stock Deduction in transaction
    try:
        with get_db_connection() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                # 1. Deduct stock atomically for each variant
                for var_id, (total_qty, prod_name, col_name, size_name) in variant_quantities.items():
                    cur = conn.execute(
                        """
                        UPDATE product_variants
                        SET stock = stock - ?
                        WHERE id = ? AND is_active = 1 AND stock >= ?
                        """,
                        (total_qty, var_id, total_qty),
                    )
                    if cur.rowcount == 0:
                        row = conn.execute("SELECT stock, is_active FROM product_variants WHERE id = ?", (var_id,)).fetchone()
                        curr_stock = row["stock"] if row else 0
                        raise HTTPException(
                            status_code=400,
                            detail=f"Sản phẩm '{prod_name}' ({col_name} / {size_name}) không đủ tồn kho để đặt hàng (hiện còn {curr_stock}, yêu cầu {total_qty})."
                        )

                # 2. Insert order
                conn.execute(
                    """
                    INSERT INTO orders (
                        id, order_code, token, idempotency_key, payload_hash, status, status_label,
                        customer_name, customer_phone, customer_email, customer_address, customer_note,
                        subtotal_vnd, shipping_fee_vnd, total_vnd, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id, order_code, token, idem_key, payload_hash, order_status, status_label,
                        name, clean_phone, email, address, note,
                        subtotal_vnd, shipping_fee_vnd, total_vnd, now_iso, now_iso,
                    )
                )

                # 3. Insert order items
                item_records = [
                    (
                        f"item_{uuid.uuid4().hex[:16]}",
                        order_id,
                        it["productId"],
                        it["slug"],
                        it["name"],
                        it["color"],
                        it["size"],
                        it["image"],
                        it["unit_price_vnd"],
                        it["quantity"],
                        it["subtotal_vnd"],
                    )
                    for it in validated_items
                ]

                conn.executemany(
                    """
                    INSERT INTO order_items (
                        id, order_id, product_id, product_slug, product_name,
                        color, size, image, unit_price_vnd, quantity, subtotal_vnd
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    item_records,
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    except HTTPException:
        raise
    except sqlite3.IntegrityError as err:
        if idem_key:
            existing = get_order_by_idempotency_key(idem_key)
            if existing:
                stored_hash = existing.get("payload_hash")
                if stored_hash and stored_hash != payload_hash:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency-Key đã được sử dụng với nội dung đơn hàng khác."
                    )
                order_dict = existing["order"]
                return {
                    "order": order_dict,
                    "token": existing["token"],
                    **order_dict,
                }
        logger.error("DB Integrity error creating order: %s", err)
        raise HTTPException(
            status_code=409,
            detail=f"Xung đột dữ liệu khi tạo đơn hàng: {err}"
        )
    except Exception as exc:
        logger.exception("Unexpected error creating order: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Lỗi hệ thống khi lưu trữ đơn hàng. Vui lòng thử lại."
        )

    order_dict = {
        "id": order_id,
        "order_code": order_code,
        "status": order_status,
        "status_label": status_label,
        "customer": {
            "name": name,
            "phone": clean_phone,
            "email": email,
            "address": address,
            "note": note,
            "notes": note,
        },
        "items": validated_items,
        "subtotal_vnd": subtotal_vnd,
        "shipping_fee_vnd": shipping_fee_vnd,
        "total_vnd": total_vnd,
        "subtotal": subtotal_vnd,
        "shipping_fee": shipping_fee_vnd,
        "total": total_vnd,
        "note": note,
        "notes": note,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    return {
        "order": order_dict,
        "token": token,
        **order_dict,
    }



@router.get("/{order_identifier}")
def get_order(
    order_identifier: str,
    token: Optional[str] = Query(None),
    x_order_token: Optional[str] = Header(None, alias="X-Order-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    Retrieves order details using token authentication.
    If token is missing, wrong, or order does not exist, returns 404.
    """
    effective_token = token
    if not effective_token and x_order_token:
        effective_token = x_order_token.strip()
    if not effective_token and authorization:
        auth_clean = authorization.strip()
        if auth_clean.lower().startswith("bearer "):
            effective_token = auth_clean[7:].strip()

    if not effective_token or not effective_token.strip():
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng hoặc phiên truy cập không hợp lệ."
        )

    order = get_order_by_id_or_code(order_identifier, effective_token.strip())
    if not order:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng hoặc phiên truy cập không hợp lệ."
        )

    return {
        "order": order,
        **order,
    }
