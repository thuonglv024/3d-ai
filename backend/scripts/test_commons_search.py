import urllib.request
import urllib.parse
import json

def search_commons(query, limit=5):
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
    req = urllib.request.Request(url, headers={'User-Agent': 'MorphFashionBot/1.0 (test@morph.local)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        pages = data.get('query', {}).get('pages', {})
        results = []
        for pid, p in pages.items():
            info = p.get('imageinfo', [{}])[0]
            w = info.get('width', 0)
            h = info.get('height', 0)
            meta = info.get('extmetadata', {})
            license_name = meta.get('LicenseShortName', {}).get('value', 'CC/Public Domain')
            results.append({
                'title': p.get('title'),
                'url': info.get('url'),
                'width': w,
                'height': h,
                'license': license_name,
                'desc_url': info.get('descriptionurl')
            })
        return results
    except Exception as e:
        print(f"Error {query}: {e}")
        return []

if __name__ == '__main__':
    items = ["trench coat", "denim jacket", "cardigan sweater", "trousers pants", "pencil skirt"]
    for it in items:
        res = search_commons(it, 3)
        print(f"\nCommons '{it}': {len(res)} results")
        for r in res:
            print(f"  {r['title']} | {r['width']}x{r['height']} | {r['license']} | {r['url'][:70]}")
