import urllib.request, json, sys

sys.stdout.reconfigure(encoding='utf-8')

targets = [
    'ao-blazer-dang-rong-2-hang-khuy',
    'ao-choang-len-det-poncho-phong-khoang',
    'ao-khoac-varsity-bong-chay-phoi-da',
    'so-mi-oxford-classic',
    'ao-thun-essential'
]

print("=== TESTING BACKEND API ENDPOINTS ===")
for slug in targets:
    url = f'http://127.0.0.1:8000/api/products/{slug}'
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            img_urls = [img.get("url") for img in data.get("images", [])]
            print(f"\nAPI {slug}:")
            print(f"  Name: {data.get('name')}")
            print(f"  Image: {data.get('image')}")
            print(f"  Images in list: {img_urls}")
            print(f"  Gallery: {data.get('gallery')}")
    except Exception as e:
        print(f"\nAPI {slug} Error: {e}")
