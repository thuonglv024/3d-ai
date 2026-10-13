import urllib.request
import re
import json

slugs = ['back-of-mens-white-shirt', 'blue-t-shirt', 'mens-tshirts', 'casual-shirts']
for slug in slugs:
    url = f"https://www.shopify.com/stock-photos/photos/{slug}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        title = re.search(r'<title>(.*?)</title>', html)
        title_str = title.group(1) if title else 'None'
        cdn_matches = re.findall(r'https://burst\.shopifycdn\.com/photos/[a-zA-Z0-9\-_]+\.jpg', html)
        print(f"Slug: {slug}")
        print(f"  Title: {title_str}")
        print(f"  CDNs: {list(dict.fromkeys(cdn_matches))[:2]}")
    except Exception as e:
        print(f"Error {slug}: {e}")
