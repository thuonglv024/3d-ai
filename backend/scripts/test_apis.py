import urllib.request
import json

def test_openverse(query):
    url = f"https://api.openverse.org/v1/images/?q={urllib.parse.quote(query)}&license_type=commercial&page_size=5"
    req = urllib.request.Request(url, headers={'User-Agent': 'MorphFashionBot/1.0 (https://morph.local)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        print(f"Openverse {query}: {data.get('result_count')} results")
        for r in data.get('results', [])[:3]:
            print(f"  {r.get('title')} | {r.get('url')} | {r.get('license')} | {r.get('width')}x{r.get('height')}")
    except Exception as e:
        print(f"Openverse error {query}:", e)

def test_commons(query):
    url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(query)}+filetype:bitmap&gsrnamespace=6&prop=imageinfo&iiprop=url|size&format=json&gsrlimit=5"
    req = urllib.request.Request(url, headers={'User-Agent': 'MorphFashionBot/1.0 (contact@morph.local)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        pages = data.get('query', {}).get('pages', {})
        print(f"Commons {query}: {len(pages)} pages")
        for pid, p in list(pages.items())[:3]:
            ii = p.get('imageinfo', [{}])[0]
            print(f"  {p.get('title')} | {ii.get('url')} | {ii.get('width')}x{ii.get('height')}")
    except Exception as e:
        print(f"Commons error {query}:", e)

if __name__ == '__main__':
    import urllib.parse
    test_openverse('blazer jacket')
    test_commons('tailored blazer')
