import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("backend/scripts/remaining_145_products.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("backend/scripts/remaining_products_detailed.txt", "w", encoding="utf-8") as out:
    for cat_id, items in data.items():
        out.write(f"\n==================== {cat_id} ({len(items)} items) ====================\n")
        for idx, p in enumerate(items, 1):
            out.write(f"{idx:2d}. {p['slug']}\n")
            out.write(f"    Name: {p['name']}\n")
            out.write(f"    Material: {p['material']}\n")
            out.write(f"    Fit: {p['fit']}\n")
            out.write(f"    Desc: {p['description']}\n")
