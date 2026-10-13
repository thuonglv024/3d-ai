import hashlib
from pathlib import Path
from PIL import Image

gate_slugs = [
    "ao-blazer-dang-rong-2-hang-khuy",
    "ao-choang-len-det-poncho-phong-khoang",
    "ao-khoac-varsity-bong-chay-phoi-da",
    "so-mi-oxford-classic",
    "so-mi-co-tru-minimal",
    "so-mi-cuban-collar",
    "ao-thun-essential",
    "ao-thun-oversized-heavyweight",
    "ao-thun-striped-relaxed",
    "quan-tay-pleated-wide-leg",
    "quan-khaki-chino-straight",
    "quan-linen-cap-chun",
    "chan-vay-pleated-midi",
    "chan-vay-chu-a-linen",
    "dam-suong-linen-minimal"
]

public_dir = Path("frontend/public/products")

print(f"{'SLUG':<38} | {'FILE':<42} | {'DIMENSIONS':<12} | {'SIZE (KB)':<10} | {'SHA256 (first 12)'}")
print("-" * 120)

for slug in gate_slugs:
    for suffix in ["", "-detail"]:
        fname = f"{slug}{suffix}.jpg"
        fpath = public_dir / fname
        if fpath.exists():
            with Image.open(fpath) as img:
                dims = f"{img.width}x{img.height}"
            size_kb = f"{fpath.stat().st_size / 1024:.1f}"
            sha = hashlib.sha256(fpath.read_bytes()).hexdigest()[:12]
            print(f"{slug:<38} | {fname:<42} | {dims:<12} | {size_kb:<10} | {sha}")
        else:
            print(f"{slug:<38} | {fname:<42} | NOT FOUND")
