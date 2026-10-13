import urllib.request

test_ids = [
    '1515886657613-9f3515b0c78f',
    '1539109136881-3be0616acf4b',
    '1434389677669-e08b4cac3105',
    '1525507119028-ed4c629a60a3',
    '1489987707025-afc232f7ea0f',
    '1576995853123-5a10305d93c0',
    '1542272604-780c96859503',
]

for pid in test_ids:
    url = f"https://images.unsplash.com/photo-{pid}?w=1600&q=85"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_len = resp.headers.get('Content-Length')
            print(f"{pid}: status {resp.status}, size {content_len}")
    except Exception as e:
        print(f"{pid}: error {e}")
