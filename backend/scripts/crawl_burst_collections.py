import urllib.request
import re
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

collections = [
    "jackets",
    "suit",
    "clothes",
    "mens-fashion",
    "womens-fashion",
    "t-shirts",
    "dress"
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

all_photos = {}

for coll in collections:
    url = f"https://www.shopify.com/stock-photos/{coll}"
    print(f"Fetching {url}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
        # extract photo links and titles
        matches = re.findall(r'href="(/stock-photos/photos/([a-zA-Z0-9\-]+))"[^>]*>.*?alt="([^"]*)"', html, re.DOTALL)
        print(f"  Found {len(matches)} photos in {coll}")
        for link, slug, alt in matches:
            if slug not in all_photos:
                # also find img url
                img_url = f"https://burst.shopifycdn.com/photos/{slug}.jpg"
                all_photos[slug] = {
                    "source_page": f"https://www.shopify.com{link}",
                    "slug": slug,
                    "alt": alt,
                    "image_url": img_url,
                    "collection": coll,
                    "license": "Shopify Burst License (Free commercial & non-commercial use)",
                    "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved"
                }
    except Exception as e:
        print(f"  Error fetching {coll}: {e}")

print(f"\nTotal unique Burst photos gathered: {len(all_photos)}")
out_path = Path("backend/scripts/burst_photos_index.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(all_photos, f, ensure_ascii=False, indent=2)
print(f"Saved to {out_path}")
