import sqlite3, json, sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(".runtime/orders.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

candidate_slugs = [
    # Coats/Jackets
    "ao-blazer-dang-rong-2-hang-khuy",
    "ao-choang-len-det-poncho-phong-khoang",
    "ao-khoac-varsity-bong-chay-phoi-da",
    # Shirts
    "ao-so-mi-oxford-regular-fit",
    "ao-so-mi-linen-co-tru-thoang-mat",
    "ao-so-mi-denim-wash-nhe",
    # T-shirts
    "ao-thun-cotton-compact-chong-nhan",
    "ao-thun-heavyweight-dinh-luong-cao",
    "ao-polo-det-kim-vintage",
    # Pants
    "quan-tay-xep-ly-dang-rong",
    "quan-khaki-chino-ong-dung",
    "quan-short-linen-cap-chun",
    # Skirts/Dresses
    "chan-vay-chu-a-linen-xanh-olive",
    "dam-suong-linen-co-v-minimal",
    "chan-vay-xep-ly-midi-thanh-lich"
]

print("CHECKING CANDIDATES:")
found = []
for slug in candidate_slugs:
    c.execute("SELECT id, slug, name, category_id, description FROM products WHERE slug = ?", (slug,))
    p = c.fetchone()
    if p:
        # get variants and images
        c.execute("SELECT DISTINCT color_name FROM product_variants WHERE product_id = ?", (p["id"],))
        colors = [r[0] for r in c.fetchall()]
        c.execute("SELECT id, url, alt, color_name, display_order, is_primary FROM product_images WHERE product_id = ?", (p["id"],))
        imgs = [dict(r) for r in c.fetchall()]
        found.append({
            "id": p["id"],
            "slug": p["slug"],
            "name": p["name"],
            "category_id": p["category_id"],
            "description": p["description"],
            "colors": colors,
            "images": imgs
        })

print(f"Matched {len(found)} out of {len(candidate_slugs)}:")
for item in found:
    print(f"- [{item['category_id']}] {item['slug']}: {item['name']} | Colors: {item['colors']}")
    for img in item['images']:
        print(f"    img: {img['url']} (primary={img['is_primary']}, color={img['color_name']})")

if len(found) < 15:
    print("\nListing some other slugs in categories to find 15 perfect candidates:")
    for cat in ["cat-so-mi", "cat-ao-thun", "cat-quan", "cat-vay"]:
        c.execute("SELECT slug, name FROM products WHERE category_id = ? LIMIT 5", (cat,))
        print(f"Cat {cat}:", [f"{r[0]} ({r[1]})" for r in c.fetchall()])

conn.close()
