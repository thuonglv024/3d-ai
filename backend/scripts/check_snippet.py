import re
from pathlib import Path

content_file = Path(r'C:\Users\Phan Trinh Tien Dat\.gemini\antigravity\brain\8eb7826c-d1b9-40cb-9702-656e36d73828\.system_generated\steps\837\content.md')
text = content_file.read_text(encoding='utf-8')

# Find all occurrences of burst.shopifycdn.com/photos/...
matches = re.finditer(r'https://burst\.shopifycdn\.com/photos/([a-zA-Z0-9\-_]+)\.jpg', text)
found = set()
for m in matches:
    slug = m.group(1)
    if slug not in found:
        found.add(slug)
        # find some context
        start = max(0, m.start() - 100)
        end = min(len(text), m.end() + 100)
        print(f"Slug: {slug}")
        # print snippet
        # print(text[start:end])
print(f"Total unique slugs: {len(found)}")
