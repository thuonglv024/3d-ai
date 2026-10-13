import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open("survey_report.json", encoding="utf-8") as f:
    d = json.load(f)

clusters = {h: prods for h, prods in d["primary_hash_to_products"].items() if len(prods) > 1}
print(f"Remaining clusters: {len(clusters)}")
for i, (h, prods) in enumerate(list(clusters.items())):
    print(f"\nCluster {i+1} [hash {h[:10]}...]:")
    for p in prods:
        print(f"  {p['product_id']} -> filename={p['filename']}")
