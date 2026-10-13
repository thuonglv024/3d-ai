import urllib.request
import re

url = "https://unsplash.com/photos/young-woman-in-bomber-jacket-leans-against-pillar"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    img_matches = re.findall(r'images\.unsplash\.com/photo-([0-9a-zA-Z\-]+)', html)
    print("Found photo IDs:", list(dict.fromkeys(img_matches))[:5])
except Exception as e:
    print("Error:", e)
