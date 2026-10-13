import os
import sys
import json
import sqlite3
import hashlib
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / ".runtime" / "orders.db"
PUBLIC_PRODUCTS = ROOT / "frontend" / "public" / "products"
OUT_FILE = ROOT / "survey_report.json"

def sha256_file(filepath: Path) -> str:
    if not filepath.is_file():
        return "MISSING"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    products = cursor.execute("""
        SELECT p.id, p.slug, p.name, p.category_id,
               (SELECT color_name FROM product_variants WHERE product_id = p.id LIMIT 1) as color_name,
               (SELECT color_hex FROM product_variants WHERE product_id = p.id LIMIT 1) as color_hex
        FROM products p
        ORDER BY p.id
    """).fetchall()

    images = cursor.execute("""
        SELECT product_id, url, is_primary, display_order
        FROM product_images
        ORDER BY product_id, is_primary DESC, display_order ASC
    """).fetchall()

    product_images_map = defaultdict(list)
    for img in images:
        product_images_map[img["product_id"]].append(dict(img))

    report = {
        "total_products": len(products),
        "total_image_rows": len(images),
        "primary_images": [],
        "all_images": [],
        "missing_files": [],
        "hash_to_products": defaultdict(list),
        "primary_hash_to_products": defaultdict(list)
    }

    for p in products:
        p_dict = dict(p)
        p_imgs = product_images_map[p["id"]]
        primary_img = next((img for img in p_imgs if img["is_primary"]), p_imgs[0] if p_imgs else None)
        
        if primary_img:
            rel_name = primary_img["url"].replace("/products/", "")
            file_path = PUBLIC_PRODUCTS / rel_name
            file_hash = sha256_file(file_path)
            
            item_info = {
                "product_id": p["id"],
                "slug": p["slug"],
                "name": p["name"],
                "category_id": p["category_id"],
                "color_name": p["color_name"],
                "color_hex": p["color_hex"],
                "primary_url": primary_img["url"],
                "filename": rel_name,
                "file_exists": file_path.is_file(),
                "file_size": file_path.stat().st_size if file_path.is_file() else 0,
                "sha256": file_hash
            }
            report["primary_images"].append(item_info)
            if file_hash != "MISSING":
                report["primary_hash_to_products"][file_hash].append({
                    "product_id": p["id"],
                    "slug": p["slug"],
                    "name": p["name"],
                    "category_id": p["category_id"],
                    "color_name": p["color_name"],
                    "filename": rel_name
                })
            else:
                report["missing_files"].append(primary_img["url"])

        for img in p_imgs:
            rel_name = img["url"].replace("/products/", "")
            file_path = PUBLIC_PRODUCTS / rel_name
            file_hash = sha256_file(file_path)
            report["all_images"].append({
                "product_id": p["id"],
                "url": img["url"],
                "is_primary": bool(img["is_primary"]),
                "filename": rel_name,
                "sha256": file_hash,
                "exists": file_path.is_file()
            })
            if file_hash != "MISSING":
                report["hash_to_products"][file_hash].append({
                    "product_id": p["id"],
                    "url": img["url"],
                    "is_primary": bool(img["is_primary"])
                })

    # Summary of primary duplicate clusters
    primary_dup_clusters = {h: prods for h, prods in report["primary_hash_to_products"].items() if len(prods) > 1}
    report["primary_duplicate_clusters_count"] = len(primary_dup_clusters)
    report["products_in_primary_duplicate_clusters"] = sum(len(prods) for prods in primary_dup_clusters.values())
    report["unique_primary_hashes_count"] = len(report["primary_hash_to_products"])

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Products: {len(products)}")
    print(f"Total image records: {len(images)}")
    print(f"Unique primary hashes: {len(report['primary_hash_to_products'])}")
    print(f"Primary duplicate clusters: {len(primary_dup_clusters)} clusters containing {report['products_in_primary_duplicate_clusters']} products")
    print(f"Missing primary files: {len(report['missing_files'])}")

if __name__ == "__main__":
    main()
