import sqlite3, json, sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(".runtime/orders.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

gate_slugs = [
    # Coats/Jackets (mandatory 3)
    "ao-blazer-dang-rong-2-hang-khuy",
    "ao-choang-len-det-poncho-phong-khoang",
    "ao-khoac-varsity-bong-chay-phoi-da",
    # Shirts
    "so-mi-oxford-classic",
    "so-mi-co-tru-minimal",
    "so-mi-cuban-collar",
    # T-shirts
    "ao-thun-essential",
    "ao-thun-oversized-heavyweight",
    "ao-thun-striped-relaxed",
    # Pants
    "quan-tay-pleated-wide-leg",
    "quan-khaki-chino-straight",
    "quan-linen-cap-chun",
    # Skirts/Dresses
    "chan-vay-pleated-midi",
    "chan-vay-chu-a-linen",
    "dam-suong-linen-minimal"
]

print(f"=== 15 QUALITY GATE CANDIDATES DETAILS ===")
for slug in gate_slugs:
    c.execute("SELECT id, slug, name, category_id, description FROM products WHERE slug = ?", (slug,))
    p = c.fetchone()
    if not p:
        print(f"MISSING: {slug}")
        continue
    c.execute("SELECT DISTINCT color_name FROM product_variants WHERE product_id = ?", (p["id"],))
    colors = [r[0] for r in c.fetchall()]
    c.execute("SELECT id, url, alt, color_name, display_order, is_primary FROM product_images WHERE product_id = ?", (p["id"],))
    imgs = [dict(r) for r in c.fetchall()]
    print(f"\n[{p['category_id']}] {p['slug']}")
    print(f"  Name: {p['name']}")
    print(f"  Desc: {p['description']}")
    print(f"  Colors: {colors}")
    for img in imgs:
        print(f"  Current image: {img['url']} (primary={img['is_primary']}, color={img['color_name']})")

conn.close()
