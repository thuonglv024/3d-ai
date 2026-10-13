import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

titles = [
    "File:Grey_Double-Buttoned_Suit_Jacket.jpg",
    "File:Letterman_jacket.jpg",
    "File:Poncho.jpg"
]

params = {
    "action": "query",
    "titles": "|".join(titles),
    "prop": "imageinfo",
    "iiprop": "url|size|mime|extmetadata",
    "format": "json"
}

url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
req = urllib.request.Request(url, headers={'User-Agent': 'MorphFashionBot/1.0 (contact@morph.local)'})

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

for page_id, page in data.get('query', {}).get('pages', {}).items():
    title = page.get('title')
    imageinfo = page.get('imageinfo', [])
    if not imageinfo:
        print(f"No imageinfo for {title}")
        continue
    info = imageinfo[0]
    meta = info.get('extmetadata', {})
    artist = meta.get('Artist', {}).get('value', 'Unknown')
    license_name = meta.get('LicenseShortName', {}).get('value', 'Unknown')
    license_url = meta.get('LicenseUrl', {}).get('value', 'https://commons.wikimedia.org')
    desc = meta.get('ImageDescription', {}).get('value', '')
    
    print(f"Title: {title}")
    print(f"  URL: {info.get('url')}")
    print(f"  Dimensions: {info.get('width')} x {info.get('height')}")
    print(f"  License: {license_name} ({license_url})")
    print(f"  Artist: {artist}")
    print(f"  Description: {desc[:100]}...")
    print()
