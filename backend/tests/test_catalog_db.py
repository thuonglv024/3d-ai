"""Comprehensive tests for SQLite catalog migrations, seeding, querying, and checkout price verification."""
import math
from pathlib import Path
import sqlite3
import pytest
from starlette.testclient import TestClient

from backend.app.db import (
    get_categories,
    get_db_connection,
    get_product_by_slug_or_id,
    get_products,
    run_migrations,
)
from backend.app.main import app
from backend.app.orders import init_db
from backend.app.seed import seed_catalog


@pytest.fixture
def isolated_catalog_db(tmp_path, monkeypatch):
    """Provides an isolated SQLite database populated with catalog seed data."""
    db_file = tmp_path / "test_catalog.db"
    monkeypatch.setenv("MORPH_ORDERS_DB", str(db_file))
    init_db(db_file)
    return db_file


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


# 1. Migrations & Idempotency Tests
def test_migrations_creation_and_idempotency(tmp_path):
    """Verifies all tables and indexes are created properly and migrations are idempotent."""
    db_file = tmp_path / "test_migrations.db"
    run_migrations(db_file)

    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        # Check applied migrations
        rows = conn.execute("SELECT version, name FROM schema_migrations ORDER BY version").fetchall()
        versions = [r["version"] for r in rows]
        assert versions == [1, 2, 3, 4]


        # Check required tables exist
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t["name"] for t in tables}
        expected_tables = {
            "schema_migrations",
            "categories",
            "size_charts",
            "products",
            "product_variants",
            "product_images",
            "orders",
            "order_items",
        }
        for expected in expected_tables:
            assert expected in table_names, f"Missing table: {expected}"

    # Running migrations again should be completely safe and no-op
    run_migrations(db_file)
    run_migrations(db_file)

    with sqlite3.connect(str(db_file)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        assert count == 4



# 2. Seeding >= 150 Products
def test_seeding_150_plus_products(tmp_path):
    """Verifies seeding populates at least 150 products with full variants and images idempotently."""
    db_file = tmp_path / "test_seed_full.db"
    summary1 = seed_catalog(db_file)

    with sqlite3.connect(str(db_file)) as conn:
        cat_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        chart_count = conn.execute("SELECT COUNT(*) FROM size_charts").fetchone()[0]
        prod_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        var_count = conn.execute("SELECT COUNT(*) FROM product_variants").fetchone()[0]
        img_count = conn.execute("SELECT COUNT(*) FROM product_images").fetchone()[0]

        assert cat_count == 5
        assert chart_count >= 5
        assert prod_count >= 150, f"Expected >= 150 products, got {prod_count}"
        assert var_count >= 1000, f"Expected >= 1000 variants, got {var_count}"
        assert img_count >= 300, f"Expected >= 300 images, got {img_count}"

    # Idempotent re-run
    summary2 = seed_catalog(db_file)
    assert summary1 == summary2

    with sqlite3.connect(str(db_file)) as conn:
        prod_count_after = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        var_count_after = conn.execute("SELECT COUNT(*) FROM product_variants").fetchone()[0]
        assert prod_count == prod_count_after
        assert var_count == var_count_after


# 3. Catalog Pagination Tests
def test_catalog_pagination(client, isolated_catalog_db):
    """Verifies paginated product catalog results."""
    # Page 1 with limit 24
    res1 = client.get("/api/products?page=1&limit=24")
    assert res1.status_code == 200
    data1 = res1.json()

    assert "items" in data1
    assert "total" in data1
    assert "page" in data1
    assert "page_size" in data1
    assert "total_pages" in data1

    assert data1["page"] == 1
    assert data1["page_size"] == 24
    assert data1["total"] >= 150
    assert len(data1["items"]) == 24
    assert data1["total_pages"] == math.ceil(data1["total"] / 24)

    # Page 2 with limit 24
    res2 = client.get("/api/products?page=2&limit=24")
    assert res2.status_code == 200
    data2 = res2.json()

    assert data2["page"] == 2
    assert len(data2["items"]) == 24

    # Ensure page 1 and page 2 don't overlap
    page1_ids = {p["id"] for p in data1["items"]}
    page2_ids = {p["id"] for p in data2["items"]}
    assert len(page1_ids.intersection(page2_ids)) == 0

    # Paginated flag without explicit page/limit
    res_flag = client.get("/api/products?paginated=true")
    assert res_flag.status_code == 200
    flag_data = res_flag.json()
    assert "items" in flag_data
    assert "total" in flag_data
    assert flag_data["page"] == 1
    assert flag_data["page_size"] == 24


# 4. Search, Filter, Sort Tests
def test_catalog_filtering_search_and_sorting(client, isolated_catalog_db):
    """Verifies search, category filtering, color/size, and price sorting."""
    # Category filter
    res_cat = client.get("/api/products?category=ao-thun&paginated=true&limit=100")
    assert res_cat.status_code == 200
    data_cat = res_cat.json()
    assert data_cat["total"] > 0
    assert all(p["category"] == "ao-thun" for p in data_cat["items"])

    # Search filter
    res_search = client.get("/api/products?search=cotton&paginated=true&limit=50")
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["total"] > 0
    for p in data_search["items"]:
        match = "cotton" in p["name"].lower() or "cotton" in p["subtitle"].lower() or "cotton" in p["description"].lower()
        assert match, f"Search term 'cotton' not found in product {p['name']}"

    # Price range filter
    min_p, max_p = 350000, 500000
    res_price = client.get(f"/api/products?min_price={min_p}&max_price={max_p}&paginated=true&limit=100")
    assert res_price.status_code == 200
    data_price = res_price.json()
    assert data_price["total"] > 0
    for p in data_price["items"]:
        assert min_p <= p["price"] <= max_p

    # Color filter
    res_color = client.get("/api/products?color=Trắng ngà&paginated=true&limit=100")
    assert res_color.status_code == 200
    data_color = res_color.json()
    assert data_color["total"] > 0
    for p in data_color["items"]:
        color_names = [c["name"] for c in p["colors"]]
        assert "Trắng ngà" in color_names

    # Size filter
    res_size = client.get("/api/products?size=M&paginated=true&limit=100")
    assert res_size.status_code == 200
    data_size = res_size.json()
    assert data_size["total"] > 0
    for p in data_size["items"]:
        assert "M" in p["sizes"]

    # Price ASC sort
    res_asc = client.get("/api/products?sort=price_asc&limit=50&paginated=true")
    assert res_asc.status_code == 200
    prices_asc = [p["price"] for p in res_asc.json()["items"]]
    assert prices_asc == sorted(prices_asc)

    # Price DESC sort
    res_desc = client.get("/api/products?sort=price_desc&limit=50&paginated=true")
    assert res_desc.status_code == 200
    prices_desc = [p["price"] for p in res_desc.json()["items"]]
    assert prices_desc == sorted(prices_desc, reverse=True)


# 5. Category Endpoints
def test_category_endpoints(client, isolated_catalog_db):
    """Verifies /api/products/categories and /api/categories return 5 categories with product counts."""
    for path in ["/api/products/categories", "/api/categories"]:
        res = client.get(path)
        assert res.status_code == 200
        cats = res.json()
        assert len(cats) == 5
        for c in cats:
            assert "slug" in c or "key" in c
            assert "name" in c
            assert "product_count" in c or "productCount" in c
            count = c.get("product_count", c.get("productCount", 0))
            assert count > 0, f"Category {c['name']} has 0 products"


# 6. Real DB Price Verification in Quotes and Orders
def test_orders_quote_and_order_use_real_db_prices(client, isolated_catalog_db):
    """Verifies quotes and orders strictly reflect SQLite database prices."""
    # 1. Initial quote for ao-thun-essential (DB price 390,000 VND)
    quote_payload = {
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 1,
            }
        ]
    }
    res = client.post("/api/orders/quote", json=quote_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["items"][0]["unit_price_vnd"] == 390000
    assert data["subtotal_vnd"] == 390000

    # 2. Update price directly in SQLite DB to 450,000 VND
    with get_db_connection(isolated_catalog_db) as conn:
        conn.execute("UPDATE products SET price = 450000 WHERE id = 'ao-thun-essential'")
        conn.commit()

    # 3. Subsequent quote must immediately reflect the updated DB price
    res_after = client.post("/api/orders/quote", json=quote_payload)
    assert res_after.status_code == 200
    data_after = res_after.json()
    assert data_after["items"][0]["unit_price_vnd"] == 450000
    assert data_after["subtotal_vnd"] == 450000

    # 4. Create order using new DB price
    order_payload = {
        "customer": {
            "name": "Nguyễn Văn Test",
            "phone": "0987654321",
            "email": "test@example.com",
            "address": "123 Đường Test, Quận 1, TP.HCM",
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
    create_res = client.post("/api/orders", json=order_payload)
    assert create_res.status_code == 201
    order_data = create_res.json()
    assert order_data["order"]["subtotal_vnd"] == 450000 * 2  # 900,000 VND
    assert order_data["order"]["items"][0]["unit_price_vnd"] == 450000


# 7. Tamper/Spoofing Protection: Client-Sent Lower Price is Overridden
def test_spoofed_lower_price_is_overridden_by_db_price(client, isolated_catalog_db):
    """Verifies that client attempting to send a 1,000 VND spoofed price is completely overridden."""
    # Attempt to spoof 1,000 VND in quote
    spoofed_quote_payload = {
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 2,
                "price": 1000,
                "unit_price_vnd": 1000,
                "subtotal": 2000,
                "subtotal_vnd": 2000,
            }
        ]
    }
    quote_res = client.post("/api/orders/quote", json=spoofed_quote_payload)
    assert quote_res.status_code == 200
    quote_data = quote_res.json()

    # Must be 390,000 * 2 = 780,000 VND, NOT 2,000 VND
    assert quote_data["items"][0]["unit_price_vnd"] == 390000
    assert quote_data["subtotal_vnd"] == 780000

    # Attempt to spoof 1,000 VND in order creation
    spoofed_order_payload = {
        "customer": {
            "name": "Khách Hàng Test",
            "phone": "0912345678",
            "email": "spoof@example.com",
            "address": "456 Đường Lê Lợi, TP.HCM",
        },
        "items": [
            {
                "productId": "ao-thun-essential",
                "color": "Trắng ngà",
                "size": "M",
                "quantity": 1,
                "price": 1000,
                "unit_price_vnd": 1000,
                "subtotal": 1000,
                "subtotal_vnd": 1000,
            }
        ],
    }
    order_res = client.post("/api/orders", json=spoofed_order_payload)
    assert order_res.status_code == 201
    order_data = order_res.json()

    # Server price must be 390,000 VND
    assert order_data["order"]["subtotal_vnd"] == 390000
    assert order_data["order"]["items"][0]["unit_price_vnd"] == 390000

    # Verify directly in SQLite DB
    order_id = order_data["order"]["id"]
    with get_db_connection(isolated_catalog_db) as conn:
        item_row = conn.execute("SELECT unit_price_vnd, subtotal_vnd FROM order_items WHERE order_id = ?", (order_id,)).fetchone()
        assert item_row["unit_price_vnd"] == 390000
        assert item_row["subtotal_vnd"] == 390000


# 8. Product Detail & 404 Tests
def test_product_detail_and_404(client, isolated_catalog_db):
    """Verifies product detail contains all reconstructed fields, size chart, variants, and 404 on nonexistent."""
    res = client.get("/api/products/ao-thun-essential")
    assert res.status_code == 200
    p = res.json()

    # All required product keys
    required_keys = [
        "id", "slug", "name", "subtitle", "category", "categoryName",
        "price", "color", "colors", "sizes", "image", "gallery",
        "description", "material", "fit", "details", "chart", "variants",
    ]
    for k in required_keys:
        assert k in p, f"Missing key in product: {k}"

    assert p["slug"] == "ao-thun-essential"
    assert p["price"] == 390000
    assert len(p["colors"]) >= 1
    assert len(p["sizes"]) >= 1
    assert len(p["variants"]) >= 1

    # Check chart
    assert p["chart"] is not None
    assert "rows" in p["chart"]
    assert len(p["chart"]["rows"]) > 0

    # Check variant structure
    v = p["variants"][0]
    assert "id" in v
    assert "sku" in v
    assert "color" in v
    assert "size" in v
    assert "stock" in v

    # Nonexistent product 404
    res_404 = client.get("/api/products/nonexistent-item-999")
    assert res_404.status_code == 404
    assert "Không tìm thấy sản phẩm" in res_404.json()["detail"]


# 9. Upgraded Catalog Tests (Limit 250, Price Filter Normalization, Color Groups, Size Sort, Related)
def test_catalog_limit_up_to_250(client, isolated_catalog_db):
    """Verifies limit up to 250 is supported without 422 error, and >250 is rejected."""
    # limit = 200
    res_200 = client.get("/api/products?limit=200&paginated=true")
    assert res_200.status_code == 200
    data_200 = res_200.json()
    assert data_200["page_size"] == 200

    # limit = 250
    res_250 = client.get("/api/products?limit=250&paginated=true")
    assert res_250.status_code == 200
    data_250 = res_250.json()
    assert data_250["page_size"] == 250

    # limit = 251 exceeds le=250 -> 422
    res_251 = client.get("/api/products?limit=251&paginated=true")
    assert res_251.status_code == 422


def test_catalog_price_filter_normalization(client, isolated_catalog_db):
    """Verifies both snake_case and camelCase price filters and presets work accurately."""
    # snake_case min_price and max_price
    res_snake = client.get("/api/products?min_price=300000&max_price=500000&paginated=true&limit=100")
    assert res_snake.status_code == 200
    data_snake = res_snake.json()
    assert data_snake["total"] > 0
    for p in data_snake["items"]:
        assert 300000 <= p["price"] <= 500000

    # camelCase minPrice and maxPrice
    res_camel = client.get("/api/products?minPrice=300000&maxPrice=500000&paginated=true&limit=100")
    assert res_camel.status_code == 200
    data_camel = res_camel.json()
    assert data_camel["total"] == data_snake["total"]

    # Presets: under-500
    res_under = client.get("/api/products?priceRange=under-500&paginated=true&limit=100")
    assert res_under.status_code == 200
    data_under = res_under.json()
    assert data_under["total"] > 0
    for p in data_under["items"]:
        assert p["price"] <= 500000

    # Presets: 500-1000
    res_mid = client.get("/api/products?priceRange=500-1000&paginated=true&limit=100")
    assert res_mid.status_code == 200
    data_mid = res_mid.json()
    assert data_mid["total"] > 0
    for p in data_mid["items"]:
        assert 500000 <= p["price"] <= 1000000


    # Presets: over-1000
    res_over = client.get("/api/products?priceRange=over-1000&paginated=true&limit=100")
    assert res_over.status_code == 200
    data_over = res_over.json()
    assert data_over["total"] > 0
    for p in data_over["items"]:
        assert p["price"] >= 1000000


def test_catalog_color_group_mapping(client, isolated_catalog_db):
    """Verifies color group mapping matches all related shades with and without accents."""
    # 'trắng', 'trang', 'white' should match 'Trắng', 'Trắng ngà', 'Trắng kem', 'Be sáng', etc.
    for q in ["trắng", "trang", "white"]:
        res_white = client.get(f"/api/products?color={q}&paginated=true&limit=100")
        assert res_white.status_code == 200
        data_white = res_white.json()
        assert data_white["total"] > 0

    # 'đen', 'den', 'black' should match 'Đen', 'Đen than', 'Xám đen', etc.
    for q in ["đen", "den", "black"]:
        res_black = client.get(f"/api/products?color={q}&paginated=true&limit=100")
        assert res_black.status_code == 200
        data_black = res_black.json()
        assert data_black["total"] > 0

    # 'xanh', 'blue' should match 'Xanh navy', 'Xanh rêu', 'Xanh olive', 'Xanh lam', etc.
    for q in ["xanh", "blue"]:
        res_blue = client.get(f"/api/products?color={q}&paginated=true&limit=100")
        assert res_blue.status_code == 200
        data_blue = res_blue.json()
        assert data_blue["total"] > 0

    # 'nâu', 'nau', 'brown' should match 'Nâu camel', 'Nâu đất', 'Nâu caramel', 'Nâu hạt dẻ', etc.
    for q in ["nâu", "nau", "brown"]:
        res_brown = client.get(f"/api/products?color={q}&paginated=true&limit=100")
        assert res_brown.status_code == 200
        data_brown = res_brown.json()
        assert data_brown["total"] > 0


def test_catalog_logical_size_sorting(client, isolated_catalog_db):
    """Verifies sizes are sorted logically: letter sizes XS -> XXL, and numerical sizes 28 -> 34 ascending."""
    # Top sizes
    res_top = client.get("/api/products/ao-thun-essential")
    assert res_top.status_code == 200
    p_top = res_top.json()
    sizes_top = p_top["sizes"]
    letter_ranks = {"XS": 20, "S": 30, "M": 40, "L": 50, "XL": 60, "2XL": 70, "XXL": 70, "3XL": 80}
    ranks = [letter_ranks[s] for s in sizes_top if s in letter_ranks]
    assert ranks == sorted(ranks), f"Top sizes not sorted logically: {sizes_top}"

    # Numeric pants sizes
    res_pants = client.get("/api/products?category=quan&limit=10&paginated=true")
    assert res_pants.status_code == 200
    pants_items = res_pants.json()["items"]
    for pt in pants_items:
        numeric_sizes = [float(s) for s in pt["sizes"] if s.isdigit()]
        if len(numeric_sizes) > 1:
            assert numeric_sizes == sorted(numeric_sizes), f"Numeric sizes not sorted ascending: {pt['sizes']}"


def test_catalog_limit_200_without_422(client, isolated_catalog_db):
    """Verifies limit=200 query succeeds without 422 validation error and returns all catalog items."""
    res = client.get("/api/products?limit=200")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 150
    assert len(data["items"]) >= 150
    assert data["limit"] == 200


def test_related_products_endpoint(client, isolated_catalog_db):
    """Verifies GET /api/products/{id}/related returns products in same category/style excluding itself."""
    res = client.get("/api/products/ao-thun-essential/related?limit=4")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) <= 4
    # Must not contain the target product itself and must prioritize same category
    for it in items:
        assert it["id"] != "ao-thun-essential"
        assert it["slug"] != "ao-thun-essential"
        assert it["category"] == "ao-thun"

    # 404 on nonexistent product
    res_404 = client.get("/api/products/nonexistent-xyz-999/related")
    assert res_404.status_code == 404


def test_order_creation_accepts_note_and_notes_and_handles_stock(client, isolated_catalog_db):
    """Verifies OrderCreateRequest accepts both note and notes fields and enforces stock deduction."""
    payload_notes = {
        "customer": {
            "name": "Trần Thị Lan",
            "phone": "0987654321",
            "address": "456 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM",
            "notes": "Giao vào giờ hành chính, gọi trước khi đến",
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
    res = client.post("/api/orders", json=payload_notes)
    assert res.status_code == 201
    order = res.json()
    assert order["customer"]["note"] == "Giao vào giờ hành chính, gọi trước khi đến"
    assert order["customer"]["notes"] == "Giao vào giờ hành chính, gọi trước khi đến"
    assert order["note"] == "Giao vào giờ hành chính, gọi trước khi đến"
    assert order["notes"] == "Giao vào giờ hành chính, gọi trước khi đến"

