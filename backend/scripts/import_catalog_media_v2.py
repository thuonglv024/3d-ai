"""
MORPH Studio — Safe, Idempotent Catalog Media Import v2
Updates SQLite `product_images` with curated v2 photography.
Preserves users, orders, scans, variants, stock, prices intact.
"""

import sys
import json
import sqlite3
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / ".runtime" / "orders.db"
MANIFEST_PATH = ROOT / "backend" / "scripts" / "catalog_asset_manifest_v2.json"

def import_v2_media(db_path: Path, manifest_path: Path, dry_run: bool = False):
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Loaded {len(manifest)} items from {manifest_path}")
    print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    updated_products = 0
    updated_images = 0

    try:
        if not dry_run:
            cursor.execute("BEGIN TRANSACTION")

        for item in manifest:
            slug = item["slug"]
            pid = item["product_id"]
            
            # Check if product exists
            cursor.execute("SELECT id, name FROM products WHERE id = ? OR slug = ?", (pid, slug))
            prod = cursor.fetchone()
            if not prod:
                print(f"WARNING: Product {slug} not found in database!")
                continue

            actual_pid = prod["id"]
            prod_name = prod["name"]

            # Query existing color for this product
            cursor.execute("SELECT color_name FROM product_variants WHERE product_id = ? LIMIT 1", (actual_pid,))
            c_row = cursor.fetchone()
            color_name = c_row["color_name"] if c_row else "Mặc định"

            primary_url = item["primary_url"]
            detail_url = item["detail_url"]

            if dry_run:
                print(f"[DRY-RUN] Would update {actual_pid} ({prod_name}):")
                print(f"  Primary: {primary_url}")
                print(f"  Detail:  {detail_url}")
                updated_products += 1
                updated_images += 2
                continue

            # Update product_images table: delete old images for this product and insert new curated v2 images
            cursor.execute("DELETE FROM product_images WHERE product_id = ?", (actual_pid,))
            
            # Insert primary
            cursor.execute("""
                INSERT INTO product_images (id, product_id, url, alt, color_name, display_order, is_primary)
                VALUES (?, ?, ?, ?, ?, 0, 1)
            """, (f"img-{slug}-0-v2", actual_pid, primary_url, f"{prod_name} - Mặt trước", color_name))

            # Insert detail
            cursor.execute("""
                INSERT INTO product_images (id, product_id, url, alt, color_name, display_order, is_primary)
                VALUES (?, ?, ?, ?, ?, 1, 0)
            """, (f"img-{slug}-1-v2", actual_pid, detail_url, f"{prod_name} - Chi tiết chất liệu (phóng to)", color_name))

            # Update products.updated_at
            cursor.execute("UPDATE products SET updated_at = datetime('now') WHERE id = ?", (actual_pid,))

            updated_products += 1
            updated_images += 2
            print(f"Updated {actual_pid} -> Primary: {primary_url}, Detail: {detail_url}")

        if not dry_run:
            conn.commit()
            print("\nTRANSACTION COMMITTED SUCCESSFULLY.")
        else:
            print("\nDRY-RUN COMPLETE. NO CHANGES MADE.")

        print(f"Summary: {updated_products} products updated, {updated_images} images written.")

    except Exception as e:
        if not dry_run:
            conn.rollback()
            print(f"\nERROR: Transaction rolled back due to: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import v2 catalog media into SQLite")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without modifying the database")
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="Path to SQLite database")
    parser.add_argument("--manifest", type=str, default=str(MANIFEST_PATH), help="Path to manifest JSON")
    args = parser.parse_args()

    import_v2_media(Path(args.db), Path(args.manifest), dry_run=args.dry_run)
