import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
content_file = Path(r'C:\Users\Phan Trinh Tien Dat\.gemini\antigravity\brain\8eb7826c-d1b9-40cb-9702-656e36d73828\.system_generated\steps\837\content.md')
text = content_file.read_text(encoding='utf-8')

imgs = re.findall(r'https://burst\.shopifycdn\.com/photos/[^\s"\'\)]+', text)
print(f"Total burst photo URLs: {len(imgs)}")
unique_imgs = sorted(list(set(imgs)))
print(f"Unique burst photo URLs: {len(unique_imgs)}")
for u in unique_imgs[:20]:
    print("  ", u)

pages = re.findall(r'/stock-photos/photos/[a-zA-Z0-9\-]+', text)
unique_pages = sorted(list(set(pages)))
print(f"\nTotal photo pages: {len(pages)}, Unique: {len(unique_pages)}")
for p in unique_pages[:30]:
    print("  ", p)
