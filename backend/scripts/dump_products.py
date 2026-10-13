import sqlite3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / ".runtime" / "orders.db"

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

products = cursor.execute("""
    SELECT p.id, p.slug, p.name, p.category_id, p.description, p.material, p.fit,
           (SELECT color_name FROM product_variants WHERE product_id = p.id LIMIT 1) as color_name,
           (SELECT color_hex FROM product_variants WHERE product_id = p.id LIMIT 1) as color_hex
    FROM products p
    ORDER BY p.category_id, p.id
""").fetchall()

images = cursor.execute("""
    SELECT product_id, url, is_primary, display_order
    FROM product_images
    ORDER BY product_id, is_primary DESC, display_order ASC
""").fetchall()

img_map = {}
for img in images:
    pid = img["product_id"]
    if pid not in img_map:
        img_map[pid] = []
    img_map[pid].append(dict(img))

result = []
for p in products:
    p_imgs = img_map.get(p["id"], [])
    primary_url = next((i["url"] for i in p_imgs if i["is_primary"]), p_imgs[0]["url"] if p_imgs else None)
    detail_url = next((i["url"] for i in p_imgs if not i["is_primary"]), None)
    if not detail_url and primary_url:
        detail_url = primary_url.replace(".jpg", "-detail.jpg")
    
    result.append({
        "id": p["id"],
        "slug": p["slug"],
        "name": p["name"],
        "category_id": p["category_id"],
        "description": p["description"],
        "fabric": p["material"],
        "fit": p["fit"],
        "color_name": p["color_name"],
        "color_hex": p["color_hex"],
        "primary_url": primary_url,
        "detail_url": detail_url
    })

out_path = ROOT / "backend" / "scripts" / "products_160_summary.json"
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Exported {len(result)} products to {out_path}")
