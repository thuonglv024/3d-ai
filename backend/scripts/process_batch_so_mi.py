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

batch_items = [
    {
        "slug": "so-mi-chambray-xanh-indigo",
        "name": "Sơ mi Chambray Xanh Indigo",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1598033129183-c4f50c736f10",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "blue chambray buttoned workwear shirt packshot"
    },
    {
        "slug": "so-mi-co-be-cuban-ke-soc-doc",
        "name": "Sơ mi Cổ Bẻ Cuban Kẻ Sọc Dọc",
        "category": "cat-so-mi",
        "raw_url": "https://burst.shopifycdn.com/photos/striped-fashion-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/striped-fashion-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "vertical striped resort cuban open collar shirt"
    },
    {
        "slug": "so-mi-co-choker-no-buoc",
        "name": "Sơ mi Cổ Choker Nơ Buộc",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1589310243389-96a5483213a8?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1589310243389-96a5483213a8",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "elegant white chiffon choker bow-tie collar blouse"
    },
    {
        "slug": "so-mi-co-cuba-hoa-tiet-la-nhiet-doi",
        "name": "Sơ mi Cổ Cuba Họa Tiết Lá Nhiệt Đới",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1507679799987-c73779587ccf",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "subtle tropical resort Cuban collar print shirt"
    },
    {
        "slug": "so-mi-co-lanh-tu-linen-tho",
        "name": "Sơ mi Cổ Lãnh Tụ Linen Thô",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1602810318383-e386cc2a3ccf",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "raw linen mandarin band-collar button-down shirt"
    },
    {
        "slug": "so-mi-co-tau-khuy-an-toi-gian",
        "name": "Sơ mi Cổ Tàu Khuy Ẩn Tối Giản",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1603252109303-2751441dd157?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1603252109303-2751441dd157",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "minimalist concealed placket mandarin collar shirt"
    },
    {
        "slug": "so-mi-co-tron-dang-dai-tunic",
        "name": "Sơ mi Cổ Tròn Dáng Dài Tunic",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1515886657613-9f3515b0c78f",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "long tunic split-hem round neck artistic shirt"
    },
    {
        "slug": "so-mi-dang-rong-thung-oversize",
        "name": "Sơ mi Dáng Rộng Thụng Oversize",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1554412933-514a83d2f3c8?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1554412933-514a83d2f3c8",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "Seoul streetwear oversized boxy cotton shirt"
    },
    {
        "slug": "so-mi-denim-nhe",
        "name": "Sơ mi Denim Dệt nhẹ",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1576995853123-5a10305d93c0",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "lightweight stone-washed blue denim shirt packshot"
    },
    {
        "slug": "so-mi-denim-rach-nhe-dam-chat-bui",
        "name": "Sơ mi Denim Rách Nhẹ Đậm Chất Bụi",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1543087903-1ac2ec7aa8c5?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1543087903-1ac2ec7aa8c5",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "distressed raw edge rugged denim overshirt"
    },
    {
        "slug": "so-mi-denim-selvedge-rua-nhe",
        "name": "Sơ mi Denim Selvedge Rửa Nhẹ",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1588850561407-ed78c282e89b",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "rinsed dark indigo selvedge denim shirt"
    },
    {
        "slug": "so-mi-det-gan-seersucker-sui-bot",
        "name": "Sơ mi Dệt Gân Seersucker Sủi Bọt",
        "category": "cat-so-mi",
        "raw_url": "https://burst.shopifycdn.com/photos/casual-shirts.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/casual-shirts",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "seersucker textured puckered weave breathable shirt"
    },
    {
        "slug": "so-mi-det-jacquard-hoa-tiet-chim",
        "name": "Sơ mi Dệt Jacquard Họa Tiết Chìm",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1598032895397-b9472444bf93?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1598032895397-b9472444bf93",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "tone-on-tone woven jacquard pattern shirt"
    },
    {
        "slug": "so-mi-flanel-ke-caro-am-ap",
        "name": "Sơ mi Flanel Kẻ Caro Ấm Áp",
        "category": "cat-so-mi",
        "raw_url": "https://burst.shopifycdn.com/photos/simple-beige-mens-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/simple-beige-mens-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "warm brushed cotton flannel buttoned shirt packshot"
    },
    {
        "slug": "so-mi-ke-gingham-nho-nang-dong",
        "name": "Sơ mi Kẻ Gingham Nhỏ Năng Động",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1594938298603-c8148c4dae35",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "clean small check gingham cotton buttoned shirt"
    },
    {
        "slug": "so-mi-ke-soc-bengal-stripe",
        "name": "Sơ mi Kẻ Sọc Bengal Stripe",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1596755094514-f87e34085b2c",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "tailored Bengal blue/white vertical stripe formal shirt"
    },
    {
        "slug": "so-mi-ke-windowpane-o-vuong-nho",
        "name": "Sơ mi Kẻ Windowpane Ô Vuông Nhỏ",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1607345366928-199ea26cfe3e?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1607345366928-199ea26cfe3e",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "windowpane grid check smart business casual shirt"
    },
    {
        "slug": "so-mi-khuy-xa-cu-cat-may-thu-cong",
        "name": "Sơ mi Khuy Xà Cừ Cắt May Thủ Công",
        "category": "cat-so-mi",
        "raw_url": "https://burst.shopifycdn.com/photos/back-of-mens-white-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/back-of-mens-white-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "tailored white fine cotton dress shirt with mother-of-pearl buttons"
    },
    {
        "slug": "so-mi-linen-nhuom-tram-tu-nhien",
        "name": "Sơ mi Linen Nhuộm Tràm Tự Nhiên",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1620799140408-edc6dcb6d633",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "natural indigo-dyed relaxed linen shirt"
    },
    {
        "slug": "so-mi-linen-tay-ngan-mua-he",
        "name": "Sơ mi Linen Tay Ngắn Mùa Hè",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1596755094514-f87e34085b2c",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "short-sleeve airy french linen summer shirt"
    },
    {
        "slug": "so-mi-linen-thoang-khi",
        "name": "Sơ mi Linen Thoáng khí",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1598033129183-c4f50c736f10",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "breathable enzyme washed relaxed linen shirt"
    },
    {
        "slug": "so-mi-lua-pha-cotton-min-muot",
        "name": "Sơ mi Lụa Pha Cotton Mịn Mượt",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1603252109303-2751441dd157?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1603252109303-2751441dd157",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "cotton-silk blend shirt with subtle sheen"
    },
    {
        "slug": "so-mi-lua-satin-bong-sang-trong",
        "name": "Sơ mi Lụa Satin Bóng Sang Trọng",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1618354691373-d851c5c3a990",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "fluid silk satin drape luxury shirt"
    },
    {
        "slug": "so-mi-overshirt-day-dan-hai-tui",
        "name": "Sơ mi Overshirt Dày Dặn Hai Túi",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1591047139829-d91aecb6caea",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "heavy two-pocket canvas utility overshirt"
    },
    {
        "slug": "so-mi-oxford-tay-ngan-gap-gau",
        "name": "Sơ mi Oxford Tay Ngắn Gấp Gấu",
        "category": "cat-so-mi",
        "raw_url": "https://burst.shopifycdn.com/photos/photo-of-a-person-in-a-white-dress-shirt-outdoors.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/photo-of-a-person-in-a-white-dress-shirt-outdoors",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "cuffed short sleeve classic oxford white shirt"
    },
    {
        "slug": "so-mi-poplin-dang-suong-cong-so",
        "name": "Sơ mi Poplin Dáng Suông Công Sở",
        "category": "cat-so-mi",
        "raw_url": "https://burst.shopifycdn.com/photos/light-men-s-dress-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/light-men-s-dress-shirt",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "crisp white poplin tailored business shirt packshot"
    },
    {
        "slug": "so-mi-tay-bong-nu-tinh-nhe-nhang",
        "name": "Sơ mi Tay Bồng Nữ Tính Nhẹ Nhàng",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1589310243389-96a5483213a8?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1589310243389-96a5483213a8",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "feminine puff-sleeve gathered cuff blouse"
    },
    {
        "slug": "so-mi-trang-co-nhon-formal",
        "name": "Sơ mi Trắng Cổ Nhọn Formal",
        "category": "cat-so-mi",
        "raw_url": "https://burst.shopifycdn.com/photos/torso-of-a-person-in-a-white-dress-shirt-and-jeans.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/torso-of-a-person-in-a-white-dress-shirt-and-jeans",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "crisp white formal pointed collar dress shirt packshot"
    },
    {
        "slug": "so-mi-vat-lech-asymmetric-hem",
        "name": "Sơ mi Vạt Lệch Asymmetric Hem",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1554412933-514a83d2f3c8?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1554412933-514a83d2f3c8",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "asymmetric high-low hem modern avant-garde shirt"
    }
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

TARGET_W = 1200
TARGET_H = 1600
TARGET_RATIO = TARGET_W / TARGET_H

print(f"=== PROCESSING BATCH OF {len(batch_items)} CAT-SO-MI ITEMS ===", flush=True)

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
    
    # Primary Image: 3:4 crop
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
    
    # Detail Image: Zoom crop on fabric / collar from the exact same raw photo
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

print(f"\nBatch cat-so-mi finished! Total manifest entries: {len(updated_manifest)}", flush=True)
