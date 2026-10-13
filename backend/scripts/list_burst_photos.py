import re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
content_file = Path(r'C:\Users\Phan Trinh Tien Dat\.gemini\antigravity\brain\8eb7826c-d1b9-40cb-9702-656e36d73828\.system_generated\steps\837\content.md')
text = content_file.read_text(encoding='utf-8')

# extract all photo slugs
pages = sorted(list(set(re.findall(r'/stock-photos/photos/([a-zA-Z0-9\-]+)', text))))
print(f"Total {len(pages)} photo pages in Burst clothes:")
for p in pages:
    print(f"- {p}")
