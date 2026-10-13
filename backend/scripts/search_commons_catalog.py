import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def search_commons(query, limit=10):
    endpoint = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "format": "json",
        "gsrlimit": limit
    }
    url = f"{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'MorphStudioFashion/1.0 (fashion-curator@morph.local)'})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        pages = data.get('query', {}).get('pages', {})
        results = []
        for pid, p in pages.items():
            info = p.get('imageinfo', [{}])[0]
            w = info.get('width', 0)
            h = info.get('height', 0)
            # Must be high resolution
            if max(w, h) < 1600:
                continue
            meta = info.get('extmetadata', {})
            license_name = meta.get('LicenseShortName', {}).get('value', 'CC/Public Domain')
            # Exclude non-clothing files like maps, coins, stamps, books, drawings, buildings
            title = p.get('title', '').lower()
            if any(x in title for x in ['map', 'coin', 'stamp', 'book', 'building', 'drawing', 'car', 'plane', 'flag']):
                continue
            results.append({
                'title': p.get('title'),
                'url': info.get('url'),
                'width': w,
                'height': h,
                'license': license_name,
                'source_page': info.get('descriptionurl')
            })
        return results
    except Exception as e:
        print(f"Error {query}: {e}")
        return []

if __name__ == '__main__':
    queries = [
        "field jacket military",
        "harrington jacket",
        "leather jacket studio",
        "trench coat studio",
        "corduroy jacket",
        "chambray shirt",
        "flannel shirt plaid",
        "gingham shirt",
        "seersucker shirt",
        "cargo pants",
        "chino pants",
        "denim shorts",
        "sweatpants",
        "pencil skirt",
        "tennis skirt pleated",
        "wrap dress",
        "slip dress",
        "shirt dress"
    ]
    for q in queries:
        res = search_commons(q, 5)
        print(f"\nQuery: '{q}' -> {len(res)} high-res matches")
        for r in res[:2]:
            print(f"  {r['title']} ({r['width']}x{r['height']}) [{r['license']}]")
            print(f"    URL: {r['url']}")
