"""SQLite database management, migrations, and catalog data access for MORPH AI."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Optional, Union
import unicodedata

from .config import ROOT

logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    """Returns the path to the SQLite database (compatible with MORPH_ORDERS_DB env var)."""
    custom = os.getenv("MORPH_ORDERS_DB")
    if custom:
        p = Path(custom)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # Preferred: workspace .runtime/orders.db
    workspace_runtime = ROOT.parent / ".runtime"
    try:
        workspace_runtime.mkdir(parents=True, exist_ok=True)
        return workspace_runtime / "orders.db"
    except Exception:
        pass

    # Fallback: backend/app/orders.db
    fallback = Path(__file__).resolve().parent / "orders.db"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


@contextmanager
def get_db_connection(db_path: Optional[Union[Path, str]] = None):
    """Context manager for SQLite database connection."""
    path = Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.create_function("lower", 1, lambda s: s.lower() if s is not None else None)
    try:
        yield conn
    finally:
        conn.close()


def run_migrations(db_path: Optional[Union[Path, str]] = None) -> None:
    """Executes schema migrations idempotently on the specified database."""
    path = Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(path), timeout=15.0) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        if str(path) != ":memory:":
            try:
                conn.execute("PRAGMA journal_mode = WAL;")
            except Exception:
                pass

        # Migration tracking table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
        """)
        conn.commit()

        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}
        now_str = datetime.now(timezone.utc).isoformat()

        # 001_orders_schema
        if 1 not in applied:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    order_code TEXT UNIQUE NOT NULL,
                    token TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE,
                    payload_hash TEXT,
                    status TEXT NOT NULL,
                    status_label TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    customer_phone TEXT NOT NULL,
                    customer_email TEXT,
                    customer_address TEXT NOT NULL,
                    customer_note TEXT,
                    subtotal_vnd INTEGER NOT NULL,
                    shipping_fee_vnd INTEGER NOT NULL,
                    total_vnd INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    product_slug TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    color TEXT NOT NULL,
                    size TEXT NOT NULL,
                    image TEXT NOT NULL,
                    unit_price_vnd INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    subtotal_vnd INTEGER NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_orders_order_code ON orders (order_code);
                CREATE INDEX IF NOT EXISTS idx_orders_idempotency_key ON orders (idempotency_key);
                CREATE INDEX IF NOT EXISTS idx_orders_payload_hash ON orders (payload_hash);
                CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
            """)
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (1, "001_orders_schema", now_str),
            )
            conn.commit()


        # 002_catalog_schema
        if 2 not in applied:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY,
                    slug TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    display_order INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS size_charts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    garment TEXT NOT NULL,
                    source TEXT,
                    measurement_basis TEXT,
                    table_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    slug TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    subtitle TEXT,
                    category_id TEXT REFERENCES categories(id),
                    price INTEGER NOT NULL,
                    original_price INTEGER,
                    description TEXT,
                    material TEXT,
                    fit TEXT,
                    details_json TEXT,
                    size_chart_id TEXT REFERENCES size_charts(id),
                    is_new INTEGER DEFAULT 0,
                    is_featured INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS product_variants (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    sku TEXT UNIQUE NOT NULL,
                    color_name TEXT NOT NULL,
                    color_hex TEXT,
                    size TEXT NOT NULL,
                    stock INTEGER DEFAULT 10,
                    is_active INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS product_images (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    alt TEXT,
                    color_name TEXT,
                    display_order INTEGER DEFAULT 0,
                    is_primary INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories (slug);
                CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id);
                CREATE INDEX IF NOT EXISTS idx_products_slug ON products (slug);
                CREATE INDEX IF NOT EXISTS idx_products_is_active ON products (is_active);
                CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants (product_id);
                CREATE INDEX IF NOT EXISTS idx_product_variants_sku ON product_variants (sku);
                CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON product_images (product_id);
            """)
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (2, "002_catalog_schema", now_str),
            )
            conn.commit()

        # 003_auth_and_history_schema
        if 3 not in applied:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    auto_save_scans INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS auth_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS login_attempts (
                    ip TEXT,
                    email TEXT,
                    attempts INTEGER,
                    last_attempt TEXT,
                    locked_until TEXT,
                    UNIQUE(ip, email)
                );

                CREATE TABLE IF NOT EXISTS body_scans (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    source_scan_id TEXT,
                    captured_at TEXT NOT NULL,
                    saved_at TEXT NOT NULL,
                    capture_mode TEXT NOT NULL,
                    height_input_cm REAL NOT NULL,
                    engine_version TEXT NOT NULL,
                    measurement_schema_version INTEGER DEFAULT 1,
                    warnings TEXT,
                    note TEXT,
                    UNIQUE(user_id, source_scan_id)
                );

                CREATE TABLE IF NOT EXISTS body_measurements (
                    id TEXT PRIMARY KEY,
                    body_scan_id TEXT NOT NULL REFERENCES body_scans(id) ON DELETE CASCADE,
                    metric_key TEXT NOT NULL,
                    value_cm REAL,
                    source TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
                CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash ON auth_sessions (token_hash);
                CREATE INDEX IF NOT EXISTS idx_body_scans_user_time ON body_scans (user_id, captured_at DESC);
                CREATE INDEX IF NOT EXISTS idx_body_measurements_scan_id ON body_measurements (body_scan_id);
                CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_email ON login_attempts (ip, email);
            """)
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (3, "003_auth_and_history_schema", now_str),
            )
            conn.commit()

        # 004_order_payload_hash
        if 4 not in applied:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall()]
            if "payload_hash" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN payload_hash TEXT;")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_payload_hash ON orders (payload_hash);")
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (4, "004_order_payload_hash", now_str),
            )
            conn.commit()



def get_categories(db_path: Optional[Union[Path, str]] = None) -> list[dict]:
    """Returns list of categories with product_count."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT c.id, c.slug, c.name, c.description, c.display_order,
                   COUNT(p.id) AS product_count
            FROM categories c
            LEFT JOIN products p ON p.category_id = c.id AND p.is_active = 1
            GROUP BY c.id
            ORDER BY c.display_order ASC, c.name ASC
        """).fetchall()

        return [
            {
                "id": r["id"],
                "key": r["slug"],
                "slug": r["slug"],
                "name": r["name"],
                "description": r["description"] or "",
                "display_order": r["display_order"],
                "product_count": r["product_count"],
                "productCount": r["product_count"],
            }
            for r in rows
        ]


def strip_vietnamese_accents(text: str) -> str:
    """Removes Vietnamese tone marks and normalizes text for flexible matching."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", text).lower().strip()


LETTER_SIZE_RANKS: dict[str, int] = {
    "3XS": 5,
    "XXXS": 5,
    "2XS": 10,
    "XXS": 10,
    "XS": 20,
    "S": 30,
    "M": 40,
    "L": 50,
    "XL": 60,
    "2XL": 70,
    "XXL": 70,
    "3XL": 80,
    "XXXL": 80,
    "4XL": 90,
    "XXXXL": 90,
    "5XL": 100,
    "FREE": 990,
    "FREESIZE": 990,
    "ONE SIZE": 990,
}


def size_sort_key(s: str) -> tuple[int, Union[int, float], str]:
    """
    Sort sizes logically:
    - Letter sizes: XS -> S -> M -> L -> XL -> XXL -> 3XL
    - Numeric sizes: 28 -> 29 -> 30 -> 31 -> 32 -> 33 -> 34 -> 35 -> 36 ascending
    """
    cleaned = str(s).strip()
    upper = cleaned.upper()
    if upper in LETTER_SIZE_RANKS:
        return (0, LETTER_SIZE_RANKS[upper], upper)

    # Numeric sizes like 28, 29, 30... or with suffix 28W, 29W...
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(.*)$", cleaned)
    if m:
        try:
            num = float(m.group(1))
            suffix = m.group(2).upper()
            return (1, num, suffix)
        except ValueError:
            pass
    return (2, 0, upper)


COLOR_GROUPS: dict[str, list[str]] = {
    # White / Trắng
    "trắng": ["trắng", "trắng ngà", "trắng kem", "trắng ngọc", "trắng tinh", "trắng sọc", "kem", "be sáng", "white", "ecru", "off-white"],
    "white": ["trắng", "trắng ngà", "trắng kem", "trắng ngọc", "trắng tinh", "trắng sọc", "kem", "be sáng", "white", "ecru", "off-white"],
    "trang": ["trắng", "trắng ngà", "trắng kem", "trắng ngọc", "trắng tinh", "trắng sọc", "kem", "be sáng", "white", "ecru", "off-white"],

    # Black / Đen
    "đen": ["đen", "đen than", "đen nhám", "đen tuyền", "đen wash", "xám đen", "xám than", "black"],
    "black": ["đen", "đen than", "đen nhám", "đen tuyền", "đen wash", "xám đen", "xám than", "black"],
    "den": ["đen", "đen than", "đen nhám", "đen tuyền", "đen wash", "xám đen", "xám than", "black"],

    # Blue / Green / Xanh
    "xanh": [
        "xanh", "xanh navy", "xanh rêu", "xanh olive", "xanh lam", "xanh mint",
        "xanh cobalt", "xanh baby", "xanh chàm", "xanh chàm đậm", "xanh forest",
        "xanh indigo", "xanh ngọc", "xanh ngọc râm", "xanh nhạt", "xanh sọc lam",
        "xanh wash", "xanh wash sáng", "blue", "navy", "green"
    ],
    "blue": [
        "xanh", "xanh navy", "xanh rêu", "xanh olive", "xanh lam", "xanh mint",
        "xanh cobalt", "xanh baby", "xanh chàm", "xanh chàm đậm", "xanh forest",
        "xanh indigo", "xanh ngọc", "xanh ngọc râm", "xanh nhạt", "xanh sọc lam",
        "xanh wash", "xanh wash sáng", "blue", "navy", "green"
    ],
    "green": [
        "xanh", "xanh rêu", "xanh olive", "xanh mint", "xanh ngọc", "xanh ngọc râm",
        "xanh forest", "green"
    ],
    "navy": ["xanh navy", "navy"],

    # Beige / Be
    "be": ["be", "be sáng", "be cát", "be kaki", "be nhạt", "nâu be", "kem", "beige", "sand", "ecru"],
    "beige": ["be", "be sáng", "be cát", "be kaki", "be nhạt", "nâu be", "kem", "beige", "sand", "ecru"],

    # Brown / Nâu
    "nâu": ["nâu", "nâu camel", "nâu đất", "nâu caramel", "nâu hạt dẻ", "nâu cà phê", "nâu be", "nâu lạc đà", "nâu olive", "nâu tây", "brown", "coffee"],
    "brown": ["nâu", "nâu camel", "nâu đất", "nâu caramel", "nâu hạt dẻ", "nâu cà phê", "nâu be", "nâu lạc đà", "nâu olive", "nâu tây", "brown", "coffee"],
    "nau": ["nâu", "nâu camel", "nâu đất", "nâu caramel", "nâu hạt dẻ", "nâu cà phê", "nâu be", "nâu lạc đà", "nâu olive", "nâu tây", "brown", "coffee"],

    # Gray / Xám
    "xám": ["xám", "xám chì", "xám ghi", "xám nhạt", "xám than", "xám tiêu", "xám đen", "xám đậm", "gray", "grey"],
    "xam": ["xám", "xám chì", "xám ghi", "xám nhạt", "xám than", "xám tiêu", "xám đen", "xám đậm", "gray", "grey"],
    "gray": ["xám", "xám chì", "xám ghi", "xám nhạt", "xám than", "xám tiêu", "xám đen", "xám đậm", "gray", "grey"],
    "grey": ["xám", "xám chì", "xám ghi", "xám nhạt", "xám than", "xám tiêu", "xám đen", "xám đậm", "gray", "grey"],

    # Pink / Hồng
    "hồng": ["hồng", "hồng nhạt", "hồng pastel", "hồng phấn", "pink"],
    "hong": ["hồng", "hồng nhạt", "hồng pastel", "hồng phấn", "pink"],
    "pink": ["hồng", "hồng nhạt", "hồng pastel", "hồng phấn", "pink"],
}


def _reconstruct_product(
    row: sqlite3.Row,
    variant_rows: list[sqlite3.Row],
    image_rows: list[sqlite3.Row],
) -> dict:
    """Helper to reconstruct a complete Product dictionary from DB rows."""
    details = []
    if row["details_json"]:
        try:
            details = json.loads(row["details_json"])
        except Exception:
            details = []

    variants = []
    colors_seen = set()
    colors = []
    sizes_seen = set()
    sizes = []

    for v in variant_rows:
        v_dict = {
            "id": v["id"],
            "productId": v["product_id"],
            "product_id": v["product_id"],
            "sku": v["sku"],
            "color": v["color_name"],
            "color_name": v["color_name"],
            "colorName": v["color_name"],
            "color_hex": v["color_hex"] or "#000000",
            "colorHex": v["color_hex"] or "#000000",
            "size": v["size"],
            "stock": v["stock"],
            "isActive": bool(v["is_active"]),
            "is_active": v["is_active"],
        }
        variants.append(v_dict)

        cname = v["color_name"]
        if cname and cname not in colors_seen:
            colors_seen.add(cname)
            colors.append({"name": cname, "hex": v["color_hex"] or "#000000"})

        s = v["size"]
        if s and s not in sizes_seen:
            sizes_seen.add(s)
            sizes.append(s)

    sizes = sorted(sizes, key=size_sort_key)
    variants.sort(key=lambda v: (v["color_name"], size_sort_key(v["size"])))


    gallery = [img["url"] for img in image_rows]
    primary_img = next((img["url"] for img in image_rows if img["is_primary"]), None)
    if not primary_img and gallery:
        primary_img = gallery[0]
    image = primary_img or ""

    chart = None
    if row["chart_id"] and row["chart_table_json"]:
        try:
            parsed_chart = json.loads(row["chart_table_json"])
            if isinstance(parsed_chart, dict):
                chart = {
                    "name": row["chart_name"] or parsed_chart.get("name", ""),
                    "garment": row["chart_garment"] or parsed_chart.get("garment", "top"),
                    "source": row["chart_source"] or parsed_chart.get("source", "illustrative"),
                    "measurement_basis": row["chart_measurement_basis"] or parsed_chart.get("measurement_basis", "body_cm"),
                    "rows": parsed_chart.get("rows", []),
                    "garment_specs": parsed_chart.get("garment_specs", []),
                    "garment_source": parsed_chart.get("garment_source"),
                }
            elif isinstance(parsed_chart, list):
                chart = {
                    "name": row["chart_name"] or "",
                    "garment": row["chart_garment"] or "top",
                    "source": row["chart_source"] or "illustrative",
                    "measurement_basis": row["chart_measurement_basis"] or "body_cm",
                    "rows": parsed_chart,
                    "garment_specs": [],
                }
        except Exception:
            chart = None

    if chart and "rows" in chart and isinstance(chart["rows"], list):
        chart["rows"] = sorted(chart["rows"], key=lambda r: size_sort_key(r.get("size", "")))

    default_color = colors[0]["name"] if colors else ""

    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "subtitle": row["subtitle"] or "",
        "category": row["category_slug"] or row["category_id"] or "",
        "categoryName": row["category_name"] or "",
        "price": int(row["price"]),
        "originalPrice": int(row["original_price"]) if row["original_price"] is not None else None,
        "color": default_color,
        "colors": colors,
        "sizes": sizes,
        "image": image,
        "gallery": gallery,
        "description": row["description"] or "",
        "material": row["material"] or "",
        "fit": row["fit"] or "",
        "details": details,
        "isNew": bool(row["is_new"]),
        "isFeatured": bool(row["is_featured"]),
        "chart": chart,
        "garment_specs": (chart or {}).get("garment_specs", []),
        "garment_source": (chart or {}).get("garment_source"),
        "variants": variants,
        "images": [
            {
                "id": img["id"],
                "url": img["url"],
                "alt": img["alt"] or "",
                "color_name": img["color_name"] or "",
                "colorName": img["color_name"] or "",
                "display_order": img["display_order"],
                "is_primary": bool(img["is_primary"]),
            }
            for img in image_rows
        ],
    }


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
    db_path: Optional[Union[Path, str]] = None,
) -> Union[list[dict], tuple[list[dict], int]]:
    """
    Queries products from SQLite database matching filters and sorting.
    If page or limit is provided, returns (items, total_count).
    If page and limit are None, returns items list.
    """
    conditions = ["p.is_active = 1"]
    params: list[Any] = []

    if category:
        cat_clean = category.strip()
        conditions.append("(LOWER(c.slug) = LOWER(?) OR LOWER(c.id) = LOWER(?) OR LOWER(p.category_id) = LOWER(?))")
        params.extend([cat_clean, cat_clean, cat_clean])

    if search:
        term = f"%{search.strip().lower()}%"
        conditions.append("(LOWER(p.name) LIKE ? OR LOWER(COALESCE(p.subtitle, '')) LIKE ? OR LOWER(COALESCE(p.description, '')) LIKE ?)")
        params.extend([term, term, term])

    if min_price is not None:
        conditions.append("p.price >= ?")
        params.append(int(min_price))

    if max_price is not None:
        conditions.append("p.price <= ?")
        params.append(int(max_price))

    variant_conditions = ["pv.product_id = p.id", "pv.is_active = 1"]
    variant_params: list[Any] = []

    if color:
        c_clean = color.strip().lower()
        parts = [p.strip().lower() for p in re.split(r"[,/|]", c_clean) if p.strip()]
        targets = []
        for p in parts:
            p_no_acc = strip_vietnamese_accents(p)
            if p in COLOR_GROUPS:
                targets.extend(COLOR_GROUPS[p])
            elif p_no_acc in COLOR_GROUPS:
                targets.extend(COLOR_GROUPS[p_no_acc])
            else:
                targets.append(p)
        unique_targets = list(dict.fromkeys(targets))

        color_clauses = []
        for t in unique_targets:
            color_clauses.append("(LOWER(pv.color_name) = ? OR LOWER(pv.color_name) LIKE ?)")
            variant_params.extend([t, f"%{t}%"])
        if color_clauses:
            variant_conditions.append(f"({' OR '.join(color_clauses)})")

    if size:
        s_clean = size.strip().upper()
        variant_conditions.append("UPPER(pv.size) = ?")
        variant_params.append(s_clean)

    if color or size:
        conditions.append(f"EXISTS (SELECT 1 FROM product_variants pv WHERE {' AND '.join(variant_conditions)})")
        params.extend(variant_params)


    where_sql = " WHERE " + " AND ".join(conditions)

    if sort == "price_asc":
        order_sql = " ORDER BY p.price ASC, p.id ASC"
    elif sort == "price_desc":
        order_sql = " ORDER BY p.price DESC, p.id ASC"
    elif sort == "name_asc":
        order_sql = " ORDER BY p.name ASC, p.id ASC"
    elif sort == "newest":
        order_sql = " ORDER BY p.is_new DESC, p.created_at DESC, p.id ASC"
    else:
        order_sql = " ORDER BY p.is_featured DESC, p.created_at DESC, p.id ASC"

    is_paginated = (page is not None) or (limit is not None)

    with get_db_connection(db_path) as conn:
        total_count = 0
        if is_paginated:
            count_sql = f"SELECT COUNT(*) FROM products p LEFT JOIN categories c ON p.category_id = c.id {where_sql}"
            total_count = conn.execute(count_sql, params).fetchone()[0]

        select_sql = f"""
            SELECT p.id, p.slug, p.name, p.subtitle, p.category_id, p.price, p.original_price,
                   p.description, p.material, p.fit, p.details_json, p.size_chart_id,
                   p.is_new, p.is_featured, p.is_active, p.created_at, p.updated_at,
                   c.slug AS category_slug, c.name AS category_name,
                   sc.id AS chart_id, sc.name AS chart_name, sc.garment AS chart_garment,
                   sc.source AS chart_source, sc.measurement_basis AS chart_measurement_basis,
                   sc.table_json AS chart_table_json
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN size_charts sc ON p.size_chart_id = sc.id
            {where_sql}
            {order_sql}
        """

        if is_paginated:
            p_val = max(1, page or 1)
            lim_val = max(1, limit or 24)
            offset_val = (p_val - 1) * lim_val
            select_sql += " LIMIT ? OFFSET ?"
            query_params = list(params) + [lim_val, offset_val]
        else:
            query_params = params

        rows = conn.execute(select_sql, query_params).fetchall()
        if not rows:
            return ([], total_count) if is_paginated else []

        p_ids = [r["id"] for r in rows]
        placeholders = ",".join("?" for _ in p_ids)

        variant_rows = conn.execute(
            f"SELECT * FROM product_variants WHERE product_id IN ({placeholders}) ORDER BY id",
            p_ids,
        ).fetchall()
        image_rows = conn.execute(
            f"SELECT * FROM product_images WHERE product_id IN ({placeholders}) ORDER BY display_order ASC, is_primary DESC, id ASC",
            p_ids,
        ).fetchall()

        variants_by_pid: dict[str, list[sqlite3.Row]] = {}
        for vr in variant_rows:
            variants_by_pid.setdefault(vr["product_id"], []).append(vr)

        images_by_pid: dict[str, list[sqlite3.Row]] = {}
        for ir in image_rows:
            images_by_pid.setdefault(ir["product_id"], []).append(ir)

        items = [
            _reconstruct_product(
                r,
                variants_by_pid.get(r["id"], []),
                images_by_pid.get(r["id"], []),
            )
            for r in rows
        ]

        if is_paginated:
            return items, total_count
        return items


def get_product_by_slug_or_id(
    slug_or_id: str,
    db_path: Optional[Union[Path, str]] = None,
) -> Optional[dict]:
    """Finds a product by slug or id and reconstructs its complete dictionary."""
    if not slug_or_id:
        return None
    target = slug_or_id.strip()

    with get_db_connection(db_path) as conn:
        row = conn.execute("""
            SELECT p.id, p.slug, p.name, p.subtitle, p.category_id, p.price, p.original_price,
                   p.description, p.material, p.fit, p.details_json, p.size_chart_id,
                   p.is_new, p.is_featured, p.is_active, p.created_at, p.updated_at,
                   c.slug AS category_slug, c.name AS category_name,
                   sc.id AS chart_id, sc.name AS chart_name, sc.garment AS chart_garment,
                   sc.source AS chart_source, sc.measurement_basis AS chart_measurement_basis,
                   sc.table_json AS chart_table_json
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN size_charts sc ON p.size_chart_id = sc.id
            WHERE LOWER(p.slug) = LOWER(?) OR LOWER(p.id) = LOWER(?)
            LIMIT 1
        """, (target, target)).fetchone()

        if not row:
            return None

        pid = row["id"]
        v_rows = conn.execute(
            "SELECT * FROM product_variants WHERE product_id = ? ORDER BY id",
            (pid,),
        ).fetchall()
        img_rows = conn.execute(
            "SELECT * FROM product_images WHERE product_id = ? ORDER BY display_order ASC, is_primary DESC, id ASC",
            (pid,),
        ).fetchall()

        return _reconstruct_product(row, v_rows, img_rows)
 
 
def get_related_products(
    slug_or_id: str,
    limit: int = 4,
    db_path: Optional[Union[Path, str]] = None,
) -> list[dict]:
    """
    Returns related products for a given product slug or id.
    Prioritizes active products in the same category, strictly excluding the product itself.
    Falls back to featured/active products if needed to fulfill requested limit.
    """
    if not slug_or_id:
        return []

    target = get_product_by_slug_or_id(slug_or_id, db_path=db_path)
    if not target:
        return []

    target_id = target["id"]
    target_slug = target.get("slug", "")
    category_slug = target.get("category")
    related: list[dict] = []
    seen_ids: set[str] = {target_id}
    if target_slug:
        seen_ids.add(target_slug)

    if category_slug:
        cat_result = get_products(category=category_slug, limit=limit + 10, db_path=db_path)
        cat_items = cat_result[0] if isinstance(cat_result, tuple) else cat_result
        for p in cat_items:
            p_id = p.get("id")
            p_slug = p.get("slug", "")
            if p_id not in seen_ids and p_slug not in seen_ids:
                seen_ids.add(p_id)
                if p_slug:
                    seen_ids.add(p_slug)
                related.append(p)
                if len(related) >= limit:
                    break

    if len(related) < limit:
        fb_result = get_products(sort="featured", limit=limit + len(seen_ids) + 10, db_path=db_path)
        fb_items = fb_result[0] if isinstance(fb_result, tuple) else fb_result
        for p in fb_items:
            p_id = p.get("id")
            p_slug = p.get("slug", "")
            if p_id not in seen_ids and p_slug not in seen_ids:
                seen_ids.add(p_id)
                if p_slug:
                    seen_ids.add(p_slug)
                related.append(p)
                if len(related) >= limit:
                    break

    return related[:limit]
