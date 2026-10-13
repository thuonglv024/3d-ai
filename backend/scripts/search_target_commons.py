import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def search_commons_detailed(query, limit=15):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
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
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png"):
            continue
        w, h = info.get("width", 0), info.get("height", 0)
        
        results.append({
            "title": title,
            "url": info.get("url"),
            "width": w,
            "height": h,
            "size_bytes": info.get("size", 0),
            "license": meta.get("LicenseShortName", {}).get("value", "CC"),
            "license_url": meta.get("LicenseUrl", {}).get("value", "https://creativecommons.org"),
            "artist": meta.get("Artist", {}).get("value", "Commons Contributor"),
            "desc": meta.get("ImageDescription", {}).get("value", "")[:200]
        })
    # sort by long edge descending
    results.sort(key=lambda x: max(x["width"], x["height"]), reverse=True)
    return results

queries = {
    "double_breasted": '"double-breasted" (blazer OR jacket OR suit)',
    "poncho": 'poncho (knit OR wool OR cape OR shawl) -drawing',
    "varsity": '"varsity jacket" OR "letterman jacket"'
}

for key, q in queries.items():
    print(f"\n==================== QUERY: {key} ({q}) ====================")
    res = search_commons_detailed(q, 15)
    for r in res:
        print(f"* {r['title']} ({r['width']}x{r['height']})")
        print(f"  URL: {r['url']}")
        print(f"  License: {r['license']} | Artist: {r['artist'][:40]}")
        print(f"  Desc: {r['desc'][:100]}")
