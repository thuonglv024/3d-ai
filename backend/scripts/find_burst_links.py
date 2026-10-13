import re, sys
from pathlib import Path

content_file = Path(r'C:\Users\Phan Trinh Tien Dat\.gemini\antigravity\brain\8eb7826c-d1b9-40cb-9702-656e36d73828\.system_generated\steps\837\content.md')
text = content_file.read_text(encoding='utf-8')

# Find all links starting with /stock-photos/
links = sorted(list(set(re.findall(r'href="(/stock-photos/[a-zA-Z0-9\-_]+)"', text))))
print(f"Total {len(links)} Burst category/tag links:")
for l in links:
    if not l.startswith("/stock-photos/photos/"):
        print(f"  {l}")
