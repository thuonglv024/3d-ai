import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_product_by_slug_or_id

p = get_product_by_slug_or_id("ao-blazer-dang-rong-2-hang-khuy")
print("Product:", p["name"])
print("Image:", p["image"])
print("Gallery:", p["gallery"])
print("Images count:", len(p.get("images", [])))
for img in p.get("images", []):
    print(" ", img)
