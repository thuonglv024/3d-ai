import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(".runtime/orders.db")
c = conn.cursor()
c.execute("SELECT p.id, p.slug, pi.url, pi.is_primary FROM products p JOIN product_images pi ON p.id = pi.product_id WHERE p.slug = 'ao-thun-essential'")
print("ao-thun-essential in DB:")
for r in c.fetchall():
    print(" ", r)

# Also check how frontend static catalog defines ao-thun-essential
from pathlib import Path
fe_cat = Path("frontend/lib/catalog.ts")
if fe_cat.exists():
    text = fe_cat.read_text(encoding="utf-8")
    idx = text.find("ao-thun-essential")
    if idx != -1:
        print("\nfrontend/lib/catalog.ts has ao-thun-essential:")
        print(text[idx:idx+300])

conn.close()
