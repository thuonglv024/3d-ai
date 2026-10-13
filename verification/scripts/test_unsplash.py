import urllib.request
import json

url = 'https://unsplash.com/s/photos/white-t-shirt'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        import re
        # Find images.unsplash.com/photo- IDs
        photo_ids = set(re.findall(r'images\.unsplash\.com/photo-([0-9a-zA-Z\-]+)', html))
        print('Found photo IDs count:', len(photo_ids))
        print('Sample IDs:', list(photo_ids)[:5])
except Exception as e:
    print('Error:', e)
