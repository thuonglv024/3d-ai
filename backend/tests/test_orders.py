"""Regression tests for MORPH Studio Orders and Checkout API.
Verifies quote calculations, variant validations, atomic order transactions,
idempotency guarantees, and token-based authentication security.
"""
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.orders import (
    FREE_SHIPPING_THRESHOLD_VND,
    STANDARD_SHIPPING_FEE_VND,
    get_db_connection,
    init_db,
)


@pytest.fixture(autouse=True)
def isolated_orders_db(tmp_path, monkeypatch):
    """Provides an isolated SQLite database for each test function."""
    db_file = tmp_path / "test_orders.db"
    monkeypatch.setenv("MORPH_ORDERS_DB", str(db_file))
    init_db(db_file)
    return db_file


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


# 1. Quote Endpoint Tests
def test_quote_valid_below_threshold(client):
    """Verifies quote calculation with shipping fee when subtotal is below 500k VND."""
    payload = {
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 1,
            }
        ]
    }
    response = client.post("/api/orders/quote", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["subtotal_vnd"] == 390000
    assert data["shipping_fee_vnd"] == STANDARD_SHIPPING_FEE_VND
    assert data["total_vnd"] == 390000 + STANDARD_SHIPPING_FEE_VND
    assert data["free_shipping_threshold_vnd"] == FREE_SHIPPING_THRESHOLD_VND

    items = data["items"]
    assert len(items) == 1
    item = items[0]
    assert item["productId"] == "ao-thun-essential"
    assert item["slug"] == "ao-thun-essential"
    assert item["name"] == "Áo thun Essential Cotton"
    assert item["color"] == "Trắng ngà"
    assert item["size"] == "M"
    assert item["unit_price_vnd"] == 390000
    assert item["quantity"] == 1
    assert item["subtotal_vnd"] == 390000
    assert "image" in item and item["image"]


def test_quote_free_shipping_threshold(client):
    """Verifies 0 VND shipping fee when order subtotal meets or exceeds 500k VND."""
    # 2 items of 390,000 VND = 780,000 VND (> 500,000 VND)
    payload = {
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Đen tuyền",
                "size": "L",
                "quantity": 2,
            }
        ]
    }
    response = client.post("/api/orders/quote", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["subtotal_vnd"] == 780000
    assert data["shipping_fee_vnd"] == 0
    assert data["total_vnd"] == 780000


def test_quote_accepts_raw_item_list(client):
    """Verifies quote endpoint accepts raw array of items as well as object wrapper."""
    payload = [
        {
            "productId": "ao-thun-essential",
            "color": "Xanh forest",
            "size": "S",
            "quantity": 1,
        }
    ]
    response = client.post("/api/orders/quote", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["subtotal_vnd"] == 390000


def test_quote_error_empty_items(client):
    """Verifies 400 error when items array is empty."""
    response = client.post("/api/orders/quote", json={"items": []})
    assert response.status_code == 400
    assert "trống" in response.json()["detail"].lower()


def test_quote_error_invalid_product(client):
    """Verifies 400 error when product ID does not exist in catalog."""
    payload = {
        "items": [
            {
                "productId": "ao-khong-ton-tai",
                "color": "Đen",
                "size": "M",
                "quantity": 1,
            }
        ]
    }
    response = client.post("/api/orders/quote", json=payload)
    assert response.status_code == 400
    assert "không tồn tại" in response.json()["detail"].lower()


def test_quote_error_invalid_color_variant(client):
    """Verifies 400 error when color is not available for the product."""
    payload = {
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Hồng cánh sen dạ quang",
                "size": "M",
                "quantity": 1,
            }
        ]
    }
    response = client.post("/api/orders/quote", json=payload)
    assert response.status_code == 400
    assert "màu sắc" in response.json()["detail"].lower()


def test_quote_error_invalid_size_variant(client):
    """Verifies 400 error when size is not available for the product."""
    payload = {
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "XXXL_INVALID",
                "quantity": 1,
            }
        ]
    }
    response = client.post("/api/orders/quote", json=payload)
    assert response.status_code == 400
    assert "kích thước" in response.json()["detail"].lower()


def test_quote_error_invalid_quantity(client):
    """Verifies validation error when quantity is less than 1."""
    payload = {
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 0,
            }
        ]
    }
    response = client.post("/api/orders/quote", json=payload)
    assert response.status_code in (400, 422)


# 2. Order Creation Tests
def test_create_order_success(client, isolated_orders_db):
    """Verifies successful order creation with transaction and snapshot records."""
    payload = {
        "customer": {
            "name": "Nguyễn Văn A",
            "phone": "0901234567",
            "email": "nguyenvana@example.com",
            "address": "123 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
            "note": "Giao vào giờ hành chính",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 2,
            }
        ],
    }

    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201
    data = response.json()

    # Check top-level envelope
    assert "order" in data
    assert "token" in data
    token = data["token"]
    assert isinstance(token, str) and len(token) >= 24

    order = data["order"]
    assert order["id"].startswith("ord_")
    assert order["order_code"].startswith("MPH-")
    assert order["status"] == "received"
    assert order["status_label"] == "Đã tiếp nhận"
    assert order["customer"]["name"] == "Nguyễn Văn A"
    assert order["customer"]["phone"] == "0901234567"
    assert order["customer"]["email"] == "nguyenvana@example.com"
    assert order["customer"]["address"] == "123 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh"
    assert order["customer"]["note"] == "Giao vào giờ hành chính"
    assert order["subtotal_vnd"] == 780000
    assert order["shipping_fee_vnd"] == 0
    assert order["total_vnd"] == 780000

    # Verify database persistence and transaction integrity
    with get_db_connection(isolated_orders_db) as conn:
        order_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        assert order_row is not None
        assert order_row["order_code"] == order["order_code"]
        assert order_row["token"] == token
        assert order_row["customer_phone"] == "0901234567"

        item_rows = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],)).fetchall()
        assert len(item_rows) == 1
        assert item_rows[0]["product_id"] == "ao-thun-essential"
        assert item_rows[0]["unit_price_vnd"] == 390000
        assert item_rows[0]["quantity"] == 2
        assert item_rows[0]["subtotal_vnd"] == 780000


def test_create_order_customer_validation_errors(client):
    """Verifies validation rules on customer fields."""
    valid_items = [
        {"productId": "ao-thun-essential", "color": "Trắng ngà", "size": "M", "quantity": 1}
    ]

    # Name too short (< 2 chars)
    res = client.post("/api/orders", json={
        "customer": {"name": "A", "phone": "0901234567", "address": "123 Le Loi Street"},
        "items": valid_items,
    })
    assert res.status_code == 400
    assert "tên khách hàng" in res.json()["detail"].lower()

    # Phone too short
    res = client.post("/api/orders", json={
        "customer": {"name": "Nguyen Van A", "phone": "12345", "address": "123 Le Loi Street"},
        "items": valid_items,
    })
    assert res.status_code == 400
    assert "số điện thoại" in res.json()["detail"].lower()

    # Phone not VN format (does not start with 0 or +84)
    res = client.post("/api/orders", json={
        "customer": {"name": "Nguyen Van A", "phone": "1901234567", "address": "123 Le Loi Street"},
        "items": valid_items,
    })
    assert res.status_code == 400

    # Address too short (< 5 chars)
    res = client.post("/api/orders", json={
        "customer": {"name": "Nguyen Van A", "phone": "0901234567", "address": "HN"},
        "items": valid_items,
    })
    assert res.status_code == 400
    assert "địa chỉ" in res.json()["detail"].lower()

    # Invalid email format
    res = client.post("/api/orders", json={
        "customer": {"name": "Nguyen Van A", "phone": "0901234567", "email": "invalid-email", "address": "123 Le Loi Street"},
        "items": valid_items,
    })
    assert res.status_code == 400
    assert "email" in res.json()["detail"].lower()


# 3. Idempotency Tests
def test_order_idempotency_prevents_duplicates(client, isolated_orders_db):
    """Verifies that duplicate requests with the same idempotency key return the original order."""
    idem_key = "idempotent-test-key-998877"
    payload = {
        "idempotency_key": idem_key,
        "customer": {
            "name": "Trần Thị B",
            "phone": "0912345678",
            "address": "456 Đường Nguyễn Trãi, Quận 5, TP.HCM",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "S",
                "quantity": 1,
            }
        ],
    }

    # First request
    res1 = client.post("/api/orders", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()
    order1 = data1["order"]
    token1 = data1["token"]

    # Second request with the same idempotency_key in body
    res2 = client.post("/api/orders", json=payload)
    assert res2.status_code in (200, 201)
    data2 = res2.json()
    order2 = data2["order"]
    token2 = data2["token"]

    # Must return exact same order and token
    assert order1["id"] == order2["id"]
    assert order1["order_code"] == order2["order_code"]
    assert token1 == token2

    # Verify only ONE order row exists in the database
    with get_db_connection(isolated_orders_db) as conn:
        count = conn.execute("SELECT COUNT(*) as cnt FROM orders WHERE idempotency_key = ?", (idem_key,)).fetchone()["cnt"]
        assert count == 1


def test_order_idempotency_via_header(client, isolated_orders_db):
    """Verifies Idempotency-Key passed via HTTP header."""
    header_key = "header-idem-key-112233"
    payload = {
        "customer": {
            "name": "Lê Hoàng C",
            "phone": "0987654321",
            "address": "789 Đường Hai Bà Trưng, Quận 3, TP.HCM",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Đen tuyền",
                "size": "L",
                "quantity": 1,
            }
        ],
    }

    res1 = client.post("/api/orders", json=payload, headers={"Idempotency-Key": header_key})
    assert res1.status_code == 201
    data1 = res1.json()

    res2 = client.post("/api/orders", json=payload, headers={"Idempotency-Key": header_key})
    assert res2.status_code in (200, 201)
    data2 = res2.json()

    assert data1["order"]["id"] == data2["order"]["id"]
    assert data1["token"] == data2["token"]


# 4. Token Security and Retrieval Tests
def test_order_retrieval_with_valid_token(client):
    """Verifies retrieving order details with the valid secret token via query param and header."""
    payload = {
        "customer": {
            "name": "Hoàng Minh D",
            "phone": "0977889900",
            "address": "12 Đường số 5, KDC Nam Long, Quận 7, TP.HCM",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 1,
            }
        ],
    }
    create_res = client.post("/api/orders", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    order_id = created_data["order"]["id"]
    order_code = created_data["order"]["order_code"]
    token = created_data["token"]

    # 1. Retrieve by internal order ID with query param ?token=
    res_id = client.get(f"/api/orders/{order_id}?token={token}")
    assert res_id.status_code == 200
    retrieved = res_id.json()["order"]
    assert retrieved["id"] == order_id
    assert retrieved["order_code"] == order_code
    assert retrieved["customer"]["name"] == "Hoàng Minh D"

    # 2. Retrieve by public order_code with query param ?token=
    res_code = client.get(f"/api/orders/{order_code}?token={token}")
    assert res_code.status_code == 200
    assert res_code.json()["order"]["id"] == order_id

    # 3. Retrieve with X-Order-Token header
    res_hdr = client.get(f"/api/orders/{order_code}", headers={"X-Order-Token": token})
    assert res_hdr.status_code == 200
    assert res_hdr.json()["order"]["id"] == order_id

    # 4. Retrieve with Bearer authorization header
    res_bearer = client.get(f"/api/orders/{order_code}", headers={"Authorization": f"Bearer {token}"})
    assert res_bearer.status_code == 200
    assert res_bearer.json()["order"]["id"] == order_id


def test_order_access_denied_without_or_wrong_token(client):
    """Verifies 404 access denial when token is missing, empty, or wrong."""
    payload = {
        "customer": {
            "name": "Bảo Mật E",
            "phone": "0933445566",
            "address": "99 Phố Huế, Quận Hai Bà Trưng, Hà Nội",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 1,
            }
        ],
    }
    create_res = client.post("/api/orders", json=payload)
    order_code = create_res.json()["order"]["order_code"]
    expected_error_detail = "Không tìm thấy đơn hàng hoặc phiên truy cập không hợp lệ."

    # A. Missing token
    res_no_token = client.get(f"/api/orders/{order_code}")
    assert res_no_token.status_code == 404
    assert res_no_token.json()["detail"] == expected_error_detail

    # B. Empty token
    res_empty_token = client.get(f"/api/orders/{order_code}?token=")
    assert res_empty_token.status_code == 404
    assert res_empty_token.json()["detail"] == expected_error_detail

    # C. Wrong token
    res_wrong_token = client.get(f"/api/orders/{order_code}?token=completely_incorrect_token_value")
    assert res_wrong_token.status_code == 404
    assert res_wrong_token.json()["detail"] == expected_error_detail

    # D. Non-existent order code even with valid-looking token
    res_non_existent = client.get("/api/orders/MPH-99999999-0000?token=any_token_string")
    assert res_non_existent.status_code == 404
    assert res_non_existent.json()["detail"] == expected_error_detail


# 6. Upgraded Orders & Checkout Tests
def test_order_variant_stock_insufficient(client, isolated_orders_db):
    """Verifies 400 error when ordered quantity exceeds available variant stock."""
    payload = {
        "customer": {
            "name": "Nguyễn Văn Test",
            "phone": "0912345678",
            "address": "123 Đường Nguyễn Trãi, Quận 1, TP.HCM",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 99999,  # Far exceeds stock
            }
        ],
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400
    assert "tồn kho" in res.json()["detail"].lower()


def test_order_multi_item_variant_aggregation(client, isolated_orders_db):
    """Verifies that multiple lines of the same variant are aggregated before stock check."""
    # Find variant stock (default is 10)
    payload = {
        "customer": {
            "name": "Nguyễn Văn Test",
            "phone": "0912345678",
            "address": "123 Đường Nguyễn Trãi, Quận 1, TP.HCM",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 10,
            },
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 10,  # 10 + 10 = 20 > 15
            },
        ],
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400

    assert "tồn kho" in res.json()["detail"].lower()


def test_order_atomic_stock_deduction_and_oversell_prevention(client, isolated_orders_db):
    """Verifies that creating an order deducts variant stock in DB and prevents overselling."""
    # 1. Get initial stock
    with get_db_connection(isolated_orders_db) as conn:
        row = conn.execute(
            """
            SELECT id, stock FROM product_variants
            WHERE product_id = 'ao-thun-essential' AND LOWER(color_name) = 'trắng ngà' AND UPPER(size) = 'S'
            """
        ).fetchone()
        assert row is not None
        initial_stock = row["stock"]
        variant_id = row["id"]

    # 2. Order 2 items
    payload = {
        "customer": {
            "name": "Trần Thị C",
            "phone": "0987654321",
            "address": "456 Đường CMT8, Quận 3, TP.HCM",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "S",
                "quantity": 2,
            }
        ],
    }
    res1 = client.post("/api/orders", json=payload)
    assert res1.status_code == 201

    # 3. Verify stock is reduced by 2
    with get_db_connection(isolated_orders_db) as conn:
        stock_after = conn.execute(
            "SELECT stock FROM product_variants WHERE id = ?", (variant_id,)
        ).fetchone()["stock"]
        assert stock_after == initial_stock - 2

    # 4. Try ordering remaining + 1 (oversell attempt)
    oversell_payload = {
        "customer": {
            "name": "Người mua muộn",
            "phone": "0900000000",
            "address": "789 Phố Huế, Hà Nội",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "S",
                "quantity": stock_after + 1,
            }
        ],
    }
    res2 = client.post("/api/orders", json=oversell_payload)
    assert res2.status_code == 400
    assert "tồn kho" in res2.json()["detail"].lower()


def test_order_idempotency_payload_fingerprint_conflict(client, isolated_orders_db):
    """Verifies that reusing the same idempotency key with a DIFFERENT payload returns 409 Conflict."""
    idem_key = "test-fingerprint-conflict-key-1234"
    payload1 = {
        "idempotency_key": idem_key,
        "customer": {
            "name": "Khách Hàng Ban Đầu",
            "phone": "0911223344",
            "address": "12 Lê Lợi, TP Huế",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 1,
            }
        ],
    }
    res1 = client.post("/api/orders", json=payload1)
    assert res1.status_code == 201

    # Same key, DIFFERENT customer name / items -> 409 Conflict
    payload2 = {
        "idempotency_key": idem_key,
        "customer": {
            "name": "Khách Hàng Khác Nhau",
            "phone": "0911223344",
            "address": "12 Lê Lợi, TP Huế",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 2,
            }
        ],
    }
    res2 = client.post("/api/orders", json=payload2)
    assert res2.status_code == 409
    assert "idempotency" in res2.json()["detail"].lower()


def test_order_customer_notes_and_note_unification(client, isolated_orders_db):
    """Verifies that either 'notes' or 'note' is accepted and both are returned."""
    payload = {
        "customer": {
            "name": "Nguyễn Ghi Chú",
            "phone": "0944556677",
            "address": "34 Trần Hưng Đạo, Quận Hoàn Kiếm, Hà Nội",
            "notes": "Giao giờ hành chính, gọi trước khi đến",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 1,
            }
        ],
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 201
    order = res.json()["order"]
    assert order["customer"]["note"] == "Giao giờ hành chính, gọi trước khi đến"
    assert order["customer"]["notes"] == "Giao giờ hành chính, gọi trước khi đến"


def test_quote_calculates_real_db_price(client, isolated_orders_db):
    """Verifies quote calculates price strictly from DB products and ignores client spoofed price."""
    payload = {
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 1,
                "price": 999,  # Spoofed price
                "unit_price": 999,
                "subtotal": 999,
            }
        ]
    }
    res = client.post("/api/orders/quote", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["items"][0]["unit_price_vnd"] == 390000
    assert data["subtotal_vnd"] == 390000

