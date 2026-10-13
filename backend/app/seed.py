"""Standalone, idempotent catalog database seeder for MORPH AI."""
import argparse
from pathlib import Path
import sys
from typing import Optional, Union

# Handle direct script invocation or module import
try:
    from .catalog_seed_data import CATEGORIES, SIZE_CHARTS, PRODUCTS
    from .db import get_db_connection, get_db_path, run_migrations
except ImportError:
    # When executed as `python backend/app/seed.py`
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from app.catalog_seed_data import CATEGORIES, SIZE_CHARTS, PRODUCTS
    from app.db import get_db_connection, get_db_path, run_migrations


def seed_catalog(db_path: Optional[Union[Path, str]] = None) -> str:
    """
    Seeds categories, size_charts, products, variants, and images into the SQLite database.
    Idempotent: safe to run repeatedly without violating unique constraints.
    """
    path = Path(db_path) if db_path else get_db_path()
    run_migrations(path)

    with get_db_connection(path) as conn:
        # 1. Categories
        for cat in CATEGORIES:
            conn.execute(
                """
                INSERT INTO categories (id, slug, name, description, display_order)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    slug = excluded.slug,
                    name = excluded.name,
                    description = excluded.description,
                    display_order = excluded.display_order;
                """,
                (
                    cat["id"],
                    cat["slug"],
                    cat["name"],
                    cat.get("description", ""),
                    cat.get("display_order", 0),
                ),
            )

        # 2. Size charts
        for chart in SIZE_CHARTS:
            conn.execute(
                """
                INSERT INTO size_charts (id, name, garment, source, measurement_basis, table_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    name = excluded.name,
                    garment = excluded.garment,
                    source = excluded.source,
                    measurement_basis = excluded.measurement_basis,
                    table_json = excluded.table_json;
                """,
                (
                    chart["id"],
                    chart["name"],
                    chart["garment"],
                    chart.get("source", "illustrative"),
                    chart.get("measurement_basis", "body_cm"),
                    chart["table_json"],
                ),
            )

        # 3. Products
        for prod in PRODUCTS:
            conn.execute(
                """
                INSERT INTO products (
                    id, slug, name, subtitle, category_id, price, original_price,
                    description, material, fit, details_json, size_chart_id,
                    is_new, is_featured, is_active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    slug = excluded.slug,
                    name = excluded.name,
                    subtitle = excluded.subtitle,
                    category_id = excluded.category_id,
                    price = excluded.price,
                    original_price = excluded.original_price,
                    description = excluded.description,
                    material = excluded.material,
                    fit = excluded.fit,
                    details_json = excluded.details_json,
                    size_chart_id = excluded.size_chart_id,
                    is_new = excluded.is_new,
                    is_featured = excluded.is_featured,
                    is_active = excluded.is_active,
                    updated_at = excluded.updated_at;
                """,
                (
                    prod["id"],
                    prod["slug"],
                    prod["name"],
                    prod.get("subtitle", ""),
                    prod["category_id"],
                    int(prod["price"]),
                    int(prod["original_price"]) if prod.get("original_price") is not None else None,
                    prod.get("description", ""),
                    prod.get("material", ""),
                    prod.get("fit", ""),
                    prod.get("details_json", "[]"),
                    prod.get("size_chart_id"),
                    1 if prod.get("is_new") or prod.get("isNew") else 0,
                    1 if prod.get("is_featured") or prod.get("isFeatured") else 0,
                    1 if prod.get("is_active", 1) else 0,
                    prod.get("created_at", "2026-10-01T00:00:00Z"),
                    prod.get("updated_at", "2026-10-12T00:00:00Z"),
                ),
            )

            # 4. Product Variants
            for var in prod.get("variants", []):
                conn.execute(
                    """
                    INSERT INTO product_variants (
                        id, product_id, sku, color_name, color_hex, size, stock, is_active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO UPDATE SET
                        product_id = excluded.product_id,
                        sku = excluded.sku,
                        color_name = excluded.color_name,
                        color_hex = excluded.color_hex,
                        size = excluded.size;
                    """,
                    (
                        var["id"],
                        prod["id"],
                        var["sku"],
                        var["color_name"],
                        var.get("color_hex", "#000000"),
                        var["size"],
                        var.get("stock", 10),
                        1 if var.get("is_active", 1) else 0,
                    ),
                )

            # 5. Product Images
            # Do not overwrite or delete approved v2 images during reseed
            cursor_v2 = conn.execute(
                "SELECT COUNT(*) FROM product_images WHERE product_id = ? AND url LIKE '/products/v2/%'",
                (prod["id"],)
            )
            has_v2 = cursor_v2.fetchone()[0] > 0
            if not has_v2:
                conn.execute("DELETE FROM product_images WHERE product_id = ?", (prod["id"],))
                for img in prod.get("images", []):
                    conn.execute(
                        """
                        INSERT INTO product_images (
                            id, product_id, url, alt, color_name, display_order, is_primary
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (id) DO UPDATE SET
                            product_id = excluded.product_id,
                            url = excluded.url,
                            alt = excluded.alt,
                            color_name = excluded.color_name,
                            display_order = excluded.display_order,
                            is_primary = excluded.is_primary;
                        """,
                        (
                            img["id"],
                            prod["id"],
                            img["url"],
                            img.get("alt", ""),
                            img.get("color_name"),
                            img.get("display_order", 0),
                            1 if img.get("is_primary") else 0,
                        ),
                    )

        conn.commit()

        # Gather counts
        cat_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        chart_count = conn.execute("SELECT COUNT(*) FROM size_charts").fetchone()[0]
        prod_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        var_count = conn.execute("SELECT COUNT(*) FROM product_variants").fetchone()[0]
        img_count = conn.execute("SELECT COUNT(*) FROM product_images").fetchone()[0]

    summary = (
        f"Seeded {cat_count} categories, {chart_count} size charts, "
        f"{prod_count} products, {var_count} variants, {img_count} images."
    )
    print(summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Seed MORPH Studio SQLite catalog.")
    parser.add_argument("--db", type=str, default=None, help="Custom SQLite DB path")
    args = parser.parse_args()

    seed_catalog(args.db)


if __name__ == "__main__":
    main()
