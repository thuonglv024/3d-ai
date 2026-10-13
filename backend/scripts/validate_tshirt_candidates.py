import urllib.request
import io
import sys
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

candidates = [
    ("burst", "blue-t-shirt", "https://burst.shopifycdn.com/photos/blue-t-shirt.jpg"),
    ("burst", "red-t-shirt", "https://burst.shopifycdn.com/photos/red-t-shirt.jpg"),
    ("burst", "green-t-shirt", "https://burst.shopifycdn.com/photos/green-t-shirt.jpg"),
    ("burst", "cobalt-blue-t-shirt", "https://burst.shopifycdn.com/photos/cobalt-blue-t-shirt.jpg"),
    ("burst", "purple-t-shirt", "https://burst.shopifycdn.com/photos/purple-t-shirt.jpg"),
    ("burst", "teal-t-shirt", "https://burst.shopifycdn.com/photos/teal-t-shirt.jpg"),
    ("burst", "light-green-t-shirt", "https://burst.shopifycdn.com/photos/light-green-t-shirt.jpg"),
    ("burst", "bright-purple-t-shirt", "https://burst.shopifycdn.com/photos/bright-purple-t-shirt.jpg"),
    ("burst", "ladies-white-t-shirt", "https://burst.shopifycdn.com/photos/ladies-white-t-shirt.jpg"),
    ("burst", "womens-red-t-shirt", "https://burst.shopifycdn.com/photos/womens-red-t-shirt.jpg"),
    ("burst", "striped-fashion-shirt", "https://burst.shopifycdn.com/photos/striped-fashion-shirt.jpg"),
    ("burst", "dropship-tshirts", "https://burst.shopifycdn.com/photos/dropship-tshirts.jpg"),
    ("burst", "blank-tees", "https://burst.shopifycdn.com/photos/blank-tees.jpg"),
    ("burst", "plain-tshirts", "https://burst.shopifycdn.com/photos/plain-tshirts.jpg"),
    ("unsplash", "photo-1581655353564-df123a1eb820", "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=1600&q=85"),
    ("unsplash", "photo-1521572267360-ee0c2909d518", "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=1600&q=85"),
    ("unsplash", "photo-1503342217505-b0a15ec3261c", "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=1600&q=85"),
    ("unsplash", "photo-1576566588028-4147f3842f27", "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=1600&q=85"),
    ("unsplash", "photo-1503342394128-c104d54dba01", "https://images.unsplash.com/photo-1503342394128-c104d54dba01?w=1600&q=85"),
    ("unsplash", "photo-1583743814966-8936f5b7be1a", "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=1600&q=85"),
    ("unsplash", "photo-1503341455253-b2e723bb3dbb", "https://images.unsplash.com/photo-1503341455253-b2e723bb3dbb?w=1600&q=85"),
    ("unsplash", "photo-1618354691438-25bc04584c23", "https://images.unsplash.com/photo-1618354691438-25bc04584c23?w=1600&q=85"),
    ("unsplash", "photo-1608256246200-53e635b5b65f", "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=1600&q=85"),
    ("unsplash", "photo-1527719327859-c6ce80353573", "https://images.unsplash.com/photo-1527719327859-c6ce80353573?w=1600&q=85"),
    ("unsplash", "photo-1584370848010-d7fe6bc767ec", "https://images.unsplash.com/photo-1584370848010-d7fe6bc767ec?w=1600&q=85"),
    ("unsplash", "photo-1578932750294-f5075e85f44a", "https://images.unsplash.com/photo-1578932750294-f5075e85f44a?w=1600&q=85"),
    ("unsplash", "photo-1618354691229-88d47f285158", "https://images.unsplash.com/photo-1618354691229-88d47f285158?w=1600&q=85"),
    ("unsplash", "photo-1586363104862-3a5e2ab60d99", "https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=1600&q=85"),
    ("unsplash", "photo-1625910513413-568b209e9f65", "https://images.unsplash.com/photo-1625910513413-568b209e9f65?w=1600&q=85"),
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print(f"Testing {len(candidates)} photo candidates for t-shirts...")
verified = []
for src_type, pid, url in candidates:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
        im = Image.open(io.BytesIO(data))
        w, h = im.size
        print(f"  [OK] {pid} ({src_type}): {w}x{h}, {len(data)/1024:.1f} KB")
        verified.append((src_type, pid, url, w, h, len(data)))
    except Exception as e:
        print(f"  [ERR] {pid}: {e}")

print(f"\nTotal verified candidates: {len(verified)} / {len(candidates)}")
