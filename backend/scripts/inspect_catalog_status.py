import sqlite3
import json

conn = sqlite3.connect('.runtime/orders.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM products')
print('Total products:', cursor.fetchone()[0])

cursor.execute("SELECT COUNT(DISTINCT product_id) FROM product_images WHERE url LIKE '/products/v2/%'")
print('Products with v2 images:', cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM product_images WHERE url LIKE '/products/v2/%'")
print('Total v2 images in product_images:', cursor.fetchone()[0])

cursor.execute("SELECT category_id, count(*) FROM products GROUP BY category_id")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Get all products without v2 images
cursor.execute("""
    SELECT p.id, p.slug, p.name, p.category_id 
    FROM products p 
    WHERE p.id NOT IN (
        SELECT DISTINCT product_id FROM product_images WHERE url LIKE '/products/v2/%'
    )
    ORDER BY p.category_id, p.id
""")
missing = cursor.fetchall()
print(f"Products missing v2 images: {len(missing)}")

category_counts = {}
for pid, slug, name, cat in missing:
    category_counts[cat] = category_counts.get(cat, 0) + 1
for cat, cnt in category_counts.items():
    print(f"  Missing in {cat}: {cnt}")
