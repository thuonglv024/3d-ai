import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent.parent
survey_path = ROOT / "survey_report.json"

with open(survey_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"Total products: {data['total_products']}")
print(f"Total images: {data['total_image_rows']}")
print(f"Unique primary hashes: {data['unique_primary_hashes_count']}")
print(f"Duplicate primary clusters: {data['primary_duplicate_clusters_count']}")
print(f"Products in duplicate clusters: {data['products_in_primary_duplicate_clusters']}")

clusters = {h: prods for h, prods in data["primary_hash_to_products"].items() if len(prods) > 1}

print("\n--- SAMPLE DUPLICATE CLUSTERS ---")
for i, (h, prods) in enumerate(clusters.items()):
    print(f"\nCluster {i+1} [SHA-256: {h[:12]}...] ({len(prods)} products):")
    for p in prods:
        print(f"  - [{p['category_id']}] {p['slug']} ({p['color_name']}) -> {p['filename']}")
