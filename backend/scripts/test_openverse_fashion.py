import urllib.request
import urllib.parse
import json

def search_openverse(query, page_size=10):
    url = f"https://api.openverse.org/v1/images/?q={urllib.parse.quote(query)}&license_type=commercial&page_size={page_size}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 MorphStudio/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        results = []
        for r in data.get('results', []):
            w = r.get('width', 0)
            h = r.get('height', 0)
            if max(w, h) >= 1200: # high resolution
                results.append({
                    'title': r.get('title'),
                    'url': r.get('url'),
                    'provider': r.get('provider'),
                    'license': r.get('license'),
                    'license_url': r.get('license_url'),
                    'foreign_landing_url': r.get('foreign_landing_url'),
                    'width': w,
                    'height': h
                })
        return results
    except Exception as e:
        print(f"Error searching Openverse '{query}': {e}")
        return []

if __name__ == '__main__':
    for term in ['trench coat fashion', 'cardigan wool', 'denim shirt', 'linen trousers', 'pleated skirt fashion']:
        res = search_openverse(term, 5)
        print(f"=== {term}: {len(res)} high-res matches ===")
        for r in res[:2]:
            print(f"  {r['title']} | {r['width']}x{r['height']} | {r['license']} | {r['url'][:60]}...")
