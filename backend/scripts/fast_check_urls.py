import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

test_urls = [
    "https://burst.shopifycdn.com/photos/blue-t-shirt.jpg",
    "https://burst.shopifycdn.com/photos/red-t-shirt.jpg",
    "https://burst.shopifycdn.com/photos/green-t-shirt.jpg",
    "https://burst.shopifycdn.com/photos/cobalt-blue-t-shirt.jpg",
    "https://burst.shopifycdn.com/photos/purple-t-shirt.jpg",
    "https://burst.shopifycdn.com/photos/teal-t-shirt.jpg",
    "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=1600&q=85",
    "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=1600&q=85",
    "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=1600&q=85",
    "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=1600&q=85",
]

headers = {'User-Agent': 'Mozilla/5.0'}
for u in test_urls:
    req = urllib.request.Request(u, headers=headers, method='HEAD')
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"OK ({resp.status}, {resp.headers.get('Content-Length')} bytes): {u.split('?')[0].split('/')[-1]}", flush=True)
    except Exception as e:
        print(f"ERR: {u.split('?')[0].split('/')[-1]} -> {e}", flush=True)
