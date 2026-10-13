import urllib.request
import re

def search_unsplash(query):
    url = f"https://unsplash.com/s/photos/{query.replace(' ', '-')}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        photo_ids = list(dict.fromkeys(re.findall(r'images\.unsplash\.com/photo-([0-9a-zA-Z\-]+)', html)))
        # Filter out thumbnail parameters or very short hashes
        clean_ids = [pid.split('?')[0] for pid in photo_ids if len(pid.split('?')[0]) > 8]
        clean_ids = list(dict.fromkeys(clean_ids))
        print(f'Unsplash "{query}": {len(clean_ids)} photos found. Samples: {clean_ids[:3]}')
        return clean_ids
    except Exception as e:
        print(f"Error fetching Unsplash '{query}':", e)
        return []

def search_burst(collection):
    url = f"https://www.shopify.com/stock-photos/{collection}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        burst_photos = list(dict.fromkeys(re.findall(r'burst\.shopifycdn\.com/photos/([0-9a-zA-Z\-_]+)\.jpg', html)))
        print(f'Burst "{collection}": {len(burst_photos)} photos found. Samples: {burst_photos[:3]}')
        return burst_photos
    except Exception as e:
        print(f"Error fetching Burst '{collection}':", e)
        return []

if __name__ == '__main__':
    search_unsplash('blazer-jacket')
    search_unsplash('denim-jacket')
    search_burst('t-shirts')
    search_burst('fashion')
    search_burst('shirt')
    search_burst('dress')
    search_burst('pants')
