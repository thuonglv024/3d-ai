import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'http://127.0.0.1:8000/api/products?page=1&limit=24'
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

items = data.get('items', [])
print('Page 1 items count:', len(items))
v2_items = [item['slug'] for item in items if '/products/v2/' in item.get('image', '')]
print('Page 1 v2 items count:', len(v2_items))
print('Page 1 v2 items:', v2_items)
for i, item in enumerate(items[:10]):
    print(f"{i+1}. {item['slug']}: {item['image']}")
