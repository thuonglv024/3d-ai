import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(".runtime/orders.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

targets = [
    "ao-blazer-dang-rong-2-hang-khuy",
    "ao-choang-len-det-poncho-phong-khoang",
    "ao-khoac-varsity-bong-chay-phoi-da",
    "so-mi-oxford-classic",
    "ao-thun-essential",
    "quan-tay-pleated-wide-leg",
    "chan-vay-pleated-midi"
]

print("=== VERIFYING PRODUCT IMAGES IN SQLITE ===")
for slug in targets:
    c.execute("SELECT id, name FROM products WHERE slug = ?", (slug,))
    p = c.fetchone()
    print(f"\nProduct: {p['name']} ({p['id']})")
    c.execute("SELECT url, is_primary, alt FROM product_images WHERE product_id = ? ORDER BY display_order", (p["id"],))
    for img in c.fetchall():
        print(f"  Image: {img['url']} (primary={img['is_primary']}) - {img['alt']}")

# Also verify that users, orders, variants are unchanged
c.execute("SELECT COUNT(*) FROM users")
print(f"\nTotal users: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM orders")
print(f"Total orders: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM product_variants")
print(f"Total variants: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM products")
print(f"Total products: {c.fetchone()[0]}")

conn.close()
