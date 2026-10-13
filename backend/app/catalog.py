"""Product catalog router and SQLite data access for MORPH AI storefront."""
import math
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Query, Request

from .db import (
    get_categories as db_get_categories,
    get_product_by_slug_or_id,
    get_products as db_get_products,
    get_related_products as db_get_related_products,
)

router = APIRouter(tags=["catalog"])
categories_router = APIRouter(prefix="/api/categories", tags=["categories"])


def get_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    color: Optional[str] = None,
    size: Optional[str] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
    db_path: Optional[str] = None,
    minPrice: Optional[int] = None,
    maxPrice: Optional[int] = None,
    price_range: Optional[str] = None,
    priceRange: Optional[str] = None,
):
    """Data access helper delegating to db.get_products with normalized price filters."""
    effective_min = min_price if min_price is not None else minPrice
    effective_max = max_price if max_price is not None else maxPrice
    range_preset = (price_range or priceRange or "").strip().lower()
    if range_preset:
        if range_preset in {"under-500", "under-500k", "<500k", "<500"}:
            if effective_max is None:
                effective_max = 500000
        elif range_preset in {"500-1000", "500k-1000k", "500k-1m", "500-1m"}:
            if effective_min is None:
                effective_min = 500000
            if effective_max is None:
                effective_max = 1000000
        elif range_preset in {"over-1000", "over-1000k", "over-1m", ">1000k", ">1m", ">1000"}:
            if effective_min is None:
                effective_min = 1000000

    return db_get_products(
        category=category,
        search=search,
        sort=sort,
        min_price=effective_min,
        max_price=effective_max,
        color=color,
        size=size,
        page=page,
        limit=limit,
        db_path=db_path,
    )


def get_product_by_slug(slug: str, db_path: Optional[str] = None) -> Optional[dict]:
    """Finds a product by slug or id from SQLite."""
    return get_product_by_slug_or_id(slug, db_path=db_path)


def get_related_products(slug: str, limit: int = 4, db_path: Optional[str] = None) -> list[dict]:
    """Finds related products excluding the product itself."""
    return db_get_related_products(slug, limit=limit, db_path=db_path)


def get_categories(db_path: Optional[str] = None):
    """Returns list of categories from SQLite."""
    return db_get_categories(db_path=db_path)


class _LazyProducts(list):
    """Lazy sequence for backward compatibility with code importing PRODUCTS."""
    def __iter__(self):
        items = db_get_products()
        return iter(items if isinstance(items, list) else items[0])

    def __len__(self):
        items = db_get_products()
        return len(items if isinstance(items, list) else items[0])

    def __getitem__(self, item):
        items = db_get_products()
        target = items if isinstance(items, list) else items[0]
        return target[item]


PRODUCTS = _LazyProducts()


@router.get("/api/products/categories")
@router.get("/api/categories")
@categories_router.get("")
@categories_router.get("/")
def list_categories():
    """Returns all product categories with product count."""
    return get_categories()


@router.get("/api/products", response_model=None)
@router.get("/api/products/", include_in_schema=False)
def list_products(
    request: Request,
    category: Optional[str] = Query(None, description="Lọc theo danh mục (vd: ao-thun, so-mi, quan, vay, ao-khoac)"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo tên hoặc mô tả"),
    sort: Optional[str] = Query(None, description="Sắp xếp (featured, price_asc, price_desc, name_asc, newest)"),
    min_price: Optional[int] = Query(None, alias="min_price", description="Giá tối thiểu VND"),
    minPrice: Optional[int] = Query(None, alias="minPrice", description="Giá tối thiểu VND (camelCase)"),
    max_price: Optional[int] = Query(None, alias="max_price", description="Giá tối đa VND"),
    maxPrice: Optional[int] = Query(None, alias="maxPrice", description="Giá tối đa VND (camelCase)"),
    price_range: Optional[str] = Query(None, alias="price_range", description="Khoảng giá preset (under-500, 500-1000, over-1000)"),
    priceRange: Optional[str] = Query(None, alias="priceRange", description="Khoảng giá preset (camelCase)"),
    color: Optional[str] = Query(None, description="Lọc theo màu hoặc nhóm màu"),
    size: Optional[str] = Query(None, description="Lọc theo size"),
    page: Optional[int] = Query(None, ge=1, description="Trang hiển thị (bắt đầu từ 1)"),
    limit: int = Query(default=24, ge=1, le=250, description="Số sản phẩm mỗi trang (tối đa 250)"),
    paginated: Optional[bool] = Query(None, description="Bắt buộc trả về kết quả phân trang"),
):
    """
    List products with filtering, search, sorting, and pagination.
    Supports limit up to 250, camelCase & snake_case price filtering, and priceRange presets.
    For backward compatibility: if page is None, limit was not explicitly requested, and not paginated, returns list[dict].
    Otherwise returns paginated dict with items, total, page, page_size, total_pages.
    """
    # Normalize price parameters
    effective_min_price = min_price if min_price is not None else minPrice
    effective_max_price = max_price if max_price is not None else maxPrice

    range_preset = (price_range or priceRange or "").strip().lower()
    if range_preset:
        if range_preset in {"under-500", "under-500k", "<500k", "<500"}:
            if effective_max_price is None:
                effective_max_price = 500000
        elif range_preset in {"500-1000", "500k-1000k", "500k-1m", "500-1m"}:
            if effective_min_price is None:
                effective_min_price = 500000
            if effective_max_price is None:
                effective_max_price = 1000000
        elif range_preset in {"over-1000", "over-1000k", "over-1m", ">1000k", ">1m", ">1000"}:
            if effective_min_price is None:
                effective_min_price = 1000000

    query_keys = set(request.query_params.keys()) if request else set()
    is_paginated = (
        ("page" in query_keys)
        or ("limit" in query_keys)
        or (page is not None)
        or (paginated is True)
    )

    if is_paginated:
        p = page or 1
        lim = limit or 24
        result = db_get_products(
            category=category,
            search=search,
            sort=sort,
            min_price=effective_min_price,
            max_price=effective_max_price,
            color=color,
            size=size,
            page=p,
            limit=lim,
        )
        items, total = result if isinstance(result, tuple) else (result, len(result))
        total_pages = math.ceil(total / lim) if lim > 0 else 1
        return {
            "items": items,
            "total": total,
            "page": p,
            "page_size": lim,
            "limit": lim,
            "total_pages": total_pages,
            "totalPages": total_pages,
        }

    items = db_get_products(
        category=category,
        search=search,
        sort=sort,
        min_price=effective_min_price,
        max_price=effective_max_price,
        color=color,
        size=size,
    )
    return items if isinstance(items, list) else items[0]


@router.get("/api/products/{slug}/related")
@router.get("/api/products/{slug}/related/", include_in_schema=False)
def list_related_products(slug: str, limit: int = Query(4, ge=1, le=20)):
    """Retrieves products related to the specified product by category/style."""
    product = get_product_by_slug_or_id(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    return get_related_products(slug, limit=limit)


@router.get("/api/products/{slug}")
def get_product(slug: str):
    """Retrieves a single product by slug or id."""
    product = get_product_by_slug_or_id(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    return product

