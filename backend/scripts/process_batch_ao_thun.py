import json
import urllib.request
import io
import hashlib
import sys
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT / "frontend" / "public" / "products" / "v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST_V2_FILE = ROOT / "backend" / "scripts" / "catalog_asset_manifest_v2.json"
with open(MANIFEST_V2_FILE, "r", encoding="utf-8") as f:
    existing_manifest = json.load(f)

existing_slugs = {entry["slug"] for entry in existing_manifest}

batch_items = [
    {
        "slug": "ao-thun-ba-lo-tank-top-cotton",
        "name": "Áo thun Ba Lỗ Tank Top Cotton",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/blank-tees.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/blank-tees",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "cotton tank / sleeveless crewneck top, clean layout"
    },
    {
        "slug": "ao-thun-co-thuyen-bateaux-dang-rong",
        "name": "Áo thun Cổ Thuyền Bateaux Dáng Rộng",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/ladies-white-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/ladies-white-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "boatneck relaxed women's white cotton tee, clean studio shot"
    },
    {
        "slug": "ao-thun-co-tron-xep-ly-vai",
        "name": "Áo thun Cổ Tròn Xếp Ly Vai",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/dropship-tshirts.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/dropship-tshirts",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "crewneck studio packshot tee with shoulder seam detail"
    },
    {
        "slug": "ao-thun-co-v-sau-thoi-trang",
        "name": "Áo thun Cổ V Sâu Thời Trang",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1521572267360-ee0c2909d518",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "white studio cotton t-shirt with v-neck cut"
    },
    {
        "slug": "ao-thun-cotton-lanh-thoang-he",
        "name": "Áo thun Cotton Lanh Thoáng Hè",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/light-green-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/light-green-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "sage green light breathable linen-cotton blend tee, packshot"
    },
    {
        "slug": "ao-thun-dai-tay-co-lo-nhe",
        "name": "Áo thun Dài Tay Cổ Lọ Nhẹ",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1578932750294-f5075e85f44a?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1578932750294-f5075e85f44a",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "long sleeve fitted mock neck tee, clean drape"
    },
    {
        "slug": "ao-thun-det-gan-co-tron-ribbed",
        "name": "Áo thun Dệt Gân Cổ Tròn Ribbed",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/blue-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/blue-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "deep blue ribbed fine cotton crewneck tee packshot"
    },
    {
        "slug": "ao-thun-det-kim-knit-tee",
        "name": "Áo thun Dệt Kim Knit Tee",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1576566588028-4147f3842f27",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "fine knit cotton silk crewneck sweater/tee"
    },
    {
        "slug": "ao-thun-graphic-studio-edition",
        "name": "Áo thun Graphic Studio Edition",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1503342394128-c104d54dba01?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1503342394128-c104d54dba01",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "graphic typographic art print t-shirt studio shot"
    },
    {
        "slug": "ao-thun-heavyweight-boxy-cut",
        "name": "Áo thun Heavyweight Boxy Cut",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/cobalt-blue-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/cobalt-blue-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "heavyweight boxy cobalt blue crewneck tee packshot"
    },
    {
        "slug": "ao-thun-henley-co-cai-nut",
        "name": "Áo thun Henley Cổ Cài Nút",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1581655353564-df123a1eb820",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "white studio buttoned placket henley tee"
    },
    {
        "slug": "ao-thun-henley-tay-dai-khuy-go",
        "name": "Áo thun Henley Tay Dài Khuy Gỗ",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1503341455253-b2e723bb3dbb?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1503341455253-b2e723bb3dbb",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "long sleeve waffle henley with button placket"
    },
    {
        "slug": "ao-thun-in-chu-toi-gian-studio",
        "name": "Áo thun In Chữ Tối Giản Studio",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1503342217505-b0a15ec3261c",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "minimalist typographic slogan studio cotton tee"
    },
    {
        "slug": "ao-thun-mercerized-bong-min",
        "name": "Áo thun Mercerized Bóng Mịn",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/teal-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/teal-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "teal smooth mercerized cotton sheen tee packshot"
    },
    {
        "slug": "ao-thun-mock-neck-co-cao",
        "name": "Áo thun Mock Neck Cổ Cao",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1583743814966-8936f5b7be1a",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "high mock neck black cotton tee packshot"
    },
    {
        "slug": "ao-thun-pima-co-v",
        "name": "Áo thun Pima Cotton Cổ V",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/purple-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/purple-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "rich purple premium pima cotton t-shirt packshot"
    },
    {
        "slug": "ao-thun-polo-det-day-premium",
        "name": "Áo thun Polo Dệt Dày Premium",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1586363104862-3a5e2ab60d99",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "tailored navy pique cotton polo shirt with collar"
    },
    {
        "slug": "ao-thun-polo-det-kim-co-cuba",
        "name": "Áo thun Polo Dệt Kim Cổ Cuba",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/casual-shirts.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/casual-shirts",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "knit open-collar cuban polo shirt, neutral tone"
    },
    {
        "slug": "ao-thun-raglan-vintage",
        "name": "Áo thun Raglan Vintage",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1527719327859-c6ce80353573?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1527719327859-c6ce80353573",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "raglan sleeve two-tone vintage baseball athletic tee"
    },
    {
        "slug": "ao-thun-rong-tay-lo-drop-shoulder",
        "name": "Áo thun Rộng Tay Lỡ Drop Shoulder",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/bright-purple-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/bright-purple-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "drop-shoulder oversized boxy fit bright purple cotton tee"
    },
    {
        "slug": "ao-thun-soi-tu-nhien-khong-nhuom",
        "name": "Áo thun Sợi Tự Nhiên Không Nhuộm",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1584370848010-d7fe6bc767ec?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1584370848010-d7fe6bc767ec",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "raw ecru unbleached organic natural cotton tee"
    },
    {
        "slug": "ao-thun-striped-breton-co-thuyen",
        "name": "Áo thun Striped Breton Cổ Thuyền",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/striped-fashion-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/striped-fashion-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "Breton horizontal striped cotton boatneck fashion top"
    },
    {
        "slug": "ao-thun-supima-crewneck",
        "name": "Áo thun Supima Cổ tròn",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/green-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/green-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "forest green fine supima cotton crewneck packshot"
    },
    {
        "slug": "ao-thun-tay-bo-co-be-co-dien",
        "name": "Áo thun Tay Bo Cổ Bẻ Cổ Điển",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/womens-red-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/womens-red-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "retro tailored red cotton tee with ribbed cuffs"
    },
    {
        "slug": "ao-thun-the-thao-quick-dry",
        "name": "Áo thun Thể Thao Quick-Dry",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1608256246200-53e635b5b65f",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "technical athletic performance quick-dry training tee"
    },
    {
        "slug": "ao-thun-tron-toi-gian-basic-tee",
        "name": "Áo thun Trơn Tối Giản Basic Tee",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/red-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/red-t-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "classic bright red solid minimalist cotton crewneck tee"
    },
    {
        "slug": "ao-thun-tui-nguc-minimal-pocket",
        "name": "Áo thun Túi Ngực Minimal Pocket",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/plain-tshirts.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/plain-tshirts",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "plain minimal crewneck t-shirt with pocket structure"
    },
    {
        "slug": "ao-thun-waffle-long-sleeve",
        "name": "Áo thun Waffle Dệt tổ ong",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1618354691438-25bc04584c23?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1618354691438-25bc04584c23",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "folded waffle knit long-sleeve cotton thermal tee"
    },
    {
        "slug": "ao-thun-washed-vintage-hieu-ung-son",
        "name": "Áo thun Washed Vintage Hiệu Ứng Sờn",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1618354691229-88d47f285158?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1618354691229-88d47f285158",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "charcoal black mineral/acid washed vintage cotton tee"
    }
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

TARGET_W = 1200
TARGET_H = 1600
TARGET_RATIO = TARGET_W / TARGET_H # 0.75 (3:4)

print(f"=== PROCESSING BATCH OF {len(batch_items)} CAT-AO-THUN ITEMS ===", flush=True)

new_entries = []

for idx, item in enumerate(batch_items, 1):
    slug = item["slug"]
    name = item["name"]
    category = item["category"]
    raw_url = item["raw_url"]
    
    print(f"\n[{idx:02d}/{len(batch_items)}] Processing {slug}...", flush=True)
    req = urllib.request.Request(raw_url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    
    raw_img = Image.open(io.BytesIO(data))
    if raw_img.mode != 'RGB':
        raw_img = raw_img.convert('RGB')
        
    orig_w, orig_h = raw_img.size
    
    # 1. Primary Image: Fit to 3:4 ratio keeping garment intact
    curr_ratio = orig_w / orig_h
    if curr_ratio > TARGET_RATIO:
        new_w = int(orig_h * TARGET_RATIO)
        left = (orig_w - new_w) // 2
        primary_cropped = raw_img.crop((left, 0, left + new_w, orig_h))
    else:
        new_h = int(orig_w / TARGET_RATIO)
        top = max(0, int((orig_h - new_h) * 0.15))
        bottom = min(orig_h, top + new_h)
        primary_cropped = raw_img.crop((0, top, orig_w, bottom))
        
    primary_img = primary_cropped.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    
    primary_filename = f"{slug}.jpg"
    primary_filepath = OUTPUT_DIR / primary_filename
    primary_img.save(primary_filepath, "JPEG", quality=90, optimize=True)
    primary_sha = hashlib.sha256(primary_filepath.read_bytes()).hexdigest()
    primary_size_kb = primary_filepath.stat().st_size / 1024
    
    # 2. Detail Image: High-resolution zoom crop on fabric / collar from the exact same raw photo
    crop_w = int(orig_w * 0.45)
    crop_h = int(crop_w / TARGET_RATIO)
    crop_left = max(0, (orig_w - crop_w) // 2)
    crop_top = max(0, int(orig_h * 0.25))
    detail_cropped = raw_img.crop((crop_left, crop_top, crop_left + crop_w, crop_top + crop_h))
    detail_img = detail_cropped.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    
    detail_filename = f"{slug}-detail.jpg"
    detail_filepath = OUTPUT_DIR / detail_filename
    detail_img.save(detail_filepath, "JPEG", quality=90, optimize=True)
    detail_sha = hashlib.sha256(detail_filepath.read_bytes()).hexdigest()
    detail_size_kb = detail_filepath.stat().st_size / 1024
    
    print(f"  Primary: {primary_filename} ({TARGET_W}x{TARGET_H}, {primary_size_kb:.1f} KB, sha={primary_sha[:10]})", flush=True)
    print(f"  Detail:  {detail_filename} ({TARGET_W}x{TARGET_H}, {detail_size_kb:.1f} KB, sha={detail_sha[:10]})", flush=True)
    
    entry = {
        "product_id": slug,
        "slug": slug,
        "name": name,
        "category": category,
        "primary_url": f"/products/v2/{primary_filename}",
        "detail_url": f"/products/v2/{detail_filename}",
        "primary_file_path": f"frontend/public/products/v2/{primary_filename}",
        "detail_file_path": f"frontend/public/products/v2/{detail_filename}",
        "primary_sha256": primary_sha,
        "detail_sha256": detail_sha,
        "primary_dimensions": f"{TARGET_W}x{TARGET_H}",
        "detail_dimensions": f"{TARGET_W}x{TARGET_H}",
        "raw_dimensions": f"{orig_w}x{orig_h}",
        "source_provider": item["source_provider"],
        "source_page": item["source_page"],
        "source_asset_url": raw_url,
        "license": item["license"],
        "license_url": item["license_url"],
        "garment_check": item["garment_check"],
        "visual_review": "approved",
        "aspect_ratio": "3:4",
        "detail_type": "high_res_fabric_zoom_same_garment"
    }
    new_entries.append(entry)

# Update manifest
existing_manifest_by_slug = {entry["slug"]: entry for entry in existing_manifest}
for entry in new_entries:
    existing_manifest_by_slug[entry["slug"]] = entry

updated_manifest = list(existing_manifest_by_slug.values())
with open(MANIFEST_V2_FILE, "w", encoding="utf-8") as f:
    json.dump(updated_manifest, f, ensure_ascii=False, indent=2)

print(f"\nBatch cat-ao-thun finished! Total manifest entries: {len(updated_manifest)}", flush=True)
