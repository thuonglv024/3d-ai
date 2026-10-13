import urllib.request
import io
from PIL import Image

test_slugs = [
    'blue-t-shirt',
    'red-t-shirt',
    'green-t-shirt',
    'casual-shirts',
    'slow-fashion-coat',
]

for s in test_slugs:
    url = f"https://burst.shopifycdn.com/photos/{s}.jpg"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        im = Image.open(io.BytesIO(data))
        print(f"{s}: format={im.format}, size={im.size} ({len(data)/1024:.1f} KB)")
    except Exception as e:
        print(f"Error {s}: {e}")
