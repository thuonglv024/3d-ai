import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def search_commons(query, limit=10):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6", # File namespace
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "format": "json"
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'MorphApparelCurator/1.0 (info@morph.vn)'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    
    results = []
    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        title = page.get("title", "")
        imgs = page.get("imageinfo", [])
        if not imgs:
            continue
        info = imgs[0]
        meta = info.get("extmetadata", {})
        
        # filter out svg, non-photos, tiny icons
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png", "image/webp"):
            continue
        w, h = info.get("width", 0), info.get("height", 0)
        if max(w, h) < 800:
            continue
            
        results.append({
            "title": title,
            "url": info.get("url"),
            "width": w,
            "height": h,
            "license": meta.get("LicenseShortName", {}).get("value", "CC"),
            "license_url": meta.get("LicenseUrl", {}).get("value", "https://creativecommons.org"),
            "artist": meta.get("Artist", {}).get("value", "Commons Contributor"),
            "desc": meta.get("ImageDescription", {}).get("value", "")[:120]
        })
    return results

print("=== SEARCHING COMMONS FOR TARGET GARMENTS ===")
for q in ['"double-breasted" blazer OR suit', '"varsity jacket" OR "letterman jacket"', 'poncho wool OR knit -military']:
    print(f"\n--- Query: {q} ---")
    res = search_commons(q, 5)
    for r in res:
        print(f"Title: {r['title']}")
        print(f"  Dims: {r['width']}x{r['height']} | License: {r['license']}")
        print(f"  URL: {r['url']}")
