import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(".runtime/orders.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT p.id, p.slug, p.name, p.category_id, p.description
    FROM products p
    WHERE p.slug LIKE '%blazer%' 
       OR p.slug LIKE '%poncho%' 
       OR p.slug LIKE '%varsity%' 
       OR p.name LIKE '%Blazer%' 
       OR p.name LIKE '%Poncho%' 
       OR p.name LIKE '%Varsity%'
""")
products = c.fetchall()
print(f"Found {len(products)} target products:")
for p in products:
    print(f"\nProduct: {p['name']} (slug: {p['slug']}, id: {p['id']}, cat: {p['category_id']})")
    print(f"Description: {p['description']}")
    c.execute("SELECT id, url, alt, color_name, display_order, is_primary FROM product_images WHERE product_id = ?", (p["id"],))
    imgs = c.fetchall()
    for img in imgs:
        print(f"  Image: url={img['url']}, primary={img['is_primary']}, color={img['color_name']}, alt={img['alt']}")

conn.close()
