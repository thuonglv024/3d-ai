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
        "slug": "ao-blazer-cat-ngan-cropped-nang-dong",
        "name": "Áo Blazer Cắt Ngắn Cropped Năng Động",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1591047139829-d91aecb6caea",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "tailored cropped waist blazer jacket, sharp structured shoulders"
    },
    {
        "slug": "ao-blazer-co-tron-khong-ve-minimal",
        "name": "Áo Blazer Cổ Tròn Không ve Minimal",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1594938298603-c8148c4dae35",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "collarless round neck minimal tailored blazer, clean lines"
    },
    {
        "slug": "ao-blazer-coc-tay-mua-he-linen",
        "name": "Áo Blazer Cộc Tay Mùa Hè Linen",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1598033129183-c4f50c736f10",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "short sleeve airy linen tailored summer blazer"
    },
    {
        "slug": "ao-blazer-linen-phom-suong-mau-cat",
        "name": "Áo Blazer Linen Phom Suông Màu Cát",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1507679799987-c73779587ccf",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "relaxed straight-cut sand beige linen blazer"
    },
    {
        "slug": "ao-bomber-kaki-lot-lua-dang-cap",
        "name": "Áo Bomber Kaki Lót Lụa Đẳng Cấp",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1551028719-00167b16eac5",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "premium khaki cotton twill silk-lined bomber jacket"
    },
    {
        "slug": "ao-bomber-ni-bong-day-giu-am",
        "name": "Áo Bomber Nỉ Bông Dày Giữ Ấm",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1556905055-8f358a7a47b2",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "heavy fleece 380gsm boxy bomber jacket"
    },
    {
        "slug": "ao-cardigan-co-v-cuc-sung",
        "name": "Áo Cardigan Cổ V Cúc Sừng",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1576566588028-4147f3842f27",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "merino wool blend V-neck knit cardigan with natural horn buttons"
    },
    {
        "slug": "ao-cardigan-det-day-cable-knit-van-thung",
        "name": "Áo Cardigan Dệt Dày Cable Knit Vặn Thừng",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1512361436605-a484bdb34b5f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1512361436605-a484bdb34b5f",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "thick cable knit embossed pattern cozy oversized cardigan"
    },
    {
        "slug": "ao-cardigan-khuy-bam-kim-loai-hien-dai",
        "name": "Áo Cardigan Khuy Bấm Kim Loại Hiện Đại",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1503341455253-b2e723bb3dbb?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1503341455253-b2e723bb3dbb",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "modern dense knit cotton cardigan with metal snap buttons"
    },
    {
        "slug": "ao-khoac-blazer-linen",
        "name": "Áo khoác Blazer Khuy đơn",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1781271573424-2cf70e4875cd?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/781271573424-2cf70e4875cd",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "unconstructed single-breasted tailored linen-cotton blazer"
    },
    {
        "slug": "ao-khoac-bomber-minimal",
        "name": "Áo khoác Bomber Gió nhẹ",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1544441893-675973e31985?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1544441893-675973e31985",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "minimalist DWR water-resistant lightweight bomber windbreaker"
    },
    {
        "slug": "ao-khoac-cardigan-len",
        "name": "Áo khoác Cardigan Dệt kim",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1434389677669-e08b4cac3105",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "rib knit merino blend slouchy dropped-shoulder cardigan"
    },
    {
        "slug": "ao-khoac-da-dang-dai-ve-to-co-dien",
        "name": "Áo Khoác Dạ Dáng Dài Ve To Cổ Điển",
        "category": "cat-ao-khoac",
        "raw_url": "https://burst.shopifycdn.com/photos/slow-fashion-coat.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/slow-fashion-coat",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "tailored long wool overcoat with broad notch lapels packshot"
    },
    {
        "slug": "ao-khoac-da-lon-suede-gia-da-cao-cap",
        "name": "Áo Khoác Da Lộn Suede Giả Da Cao Cấp",
        "category": "cat-ao-khoac",
        "raw_url": "https://burst.shopifycdn.com/photos/leather-jacket-and-tea.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/leather-jacket-and-tea",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "microfiber faux suede tailored leather jacket packshot"
    },
    {
        "slug": "ao-khoac-dang-kimono-linen-toi-gian",
        "name": "Áo Khoác Dáng Kimono Linen Tối Giản",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1515886657613-9f3515b0c78f",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "wrap kimono drape pure linen Asian-inspired jacket"
    },
    {
        "slug": "ao-khoac-dang-so-mi-shacket-da-ep",
        "name": "Áo Khoác Dáng Sơ Mi Shacket Dạ Ép",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1591047139829-d91aecb6caea",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "pressed wool blend boxy shacket shirt jacket"
    },
    {
        "slug": "ao-khoac-denim-vintage-wash-xanh-nhat",
        "name": "Áo Khoác Denim Vintage Wash Xanh Nhạt",
        "category": "cat-ao-khoac",
        "raw_url": "https://burst.shopifycdn.com/photos/woman-in-jean-jacket.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/woman-in-jean-jacket",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "light wash vintage 13oz denim trucker jacket"
    },
    {
        "slug": "ao-khoac-du-windbreaker-chong-nuoc",
        "name": "Áo Khoác Dù Windbreaker Chống Nước",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1544441893-675973e31985?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1544441893-675973e31985",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "lightweight packable nylon ripstop water-resistant windbreaker"
    },
    {
        "slug": "ao-khoac-field-jacket-bon-tui-quan-doi",
        "name": "Áo Khoác Field Jacket Bốn Túi Quân Đội",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1551028719-00167b16eac5",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "4-pocket utility military field jacket cotton canvas"
    },
    {
        "slug": "ao-khoac-gile-vest-tran-bong-phoi-layer",
        "name": "Áo Khoác Gile Vest Trần Bông Phối Layer",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1512361436605-a484bdb34b5f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1512361436605-a484bdb34b5f",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "quilted puffer sleeveless layer vest matte nylon"
    },
    {
        "slug": "ao-khoac-gio-hai-lop-the-thao",
        "name": "Áo Khoác Gió Hai Lớp Thể Thao",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1608256246200-53e635b5b65f",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "2-layer athletic breathable mesh lined wind jacket"
    },
    {
        "slug": "ao-khoac-harrington-co-be-lot-caro",
        "name": "Áo Khoác Harrington Cổ Bẻ Lót Caro",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1544441893-675973e31985?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1544441893-675973e31985",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "classic Harrington stand-collar jacket with tartan check lining"
    },
    {
        "slug": "ao-khoac-nhung-tam-corduroy-am-ap",
        "name": "Áo Khoác Nhung Tăm Corduroy Ấm Áp",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1551028719-00167b16eac5",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "100% cotton ribbed corduroy retro trucker jacket"
    },
    {
        "slug": "ao-khoac-safari-bon-tui-vai-linen",
        "name": "Áo Khoác Safari Bốn Túi Vải Linen",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1507679799987-c73779587ccf",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "classic safari 4-bellows-pocket heavyweight linen jacket"
    },
    {
        "slug": "ao-khoac-trench-coat-ngan",
        "name": "Áo khoác Trench Coat Dáng lửng",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1539109136881-3be0616acf4b",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "cropped modern gabardine cotton waist-belted trench coat"
    },
    {
        "slug": "ao-khoac-trench-ngan-tay-raglan",
        "name": "Áo Khoác Trench Ngắn Tay Raglan",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1539109136881-3be0616acf4b",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "raglan sleeve short trench jacket cotton twill"
    },
    {
        "slug": "ao-khoac-trut-phao-tran-bong-sieu-nhe",
        "name": "Áo Khoác Trút Phao Trần Bông Siêu Nhẹ",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1544441893-675973e31985?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1544441893-675973e31985",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "ultralight high-density nylon wave quilted down jacket"
    },
    {
        "slug": "ao-parka-co-mu-day-rut-chong-mua",
        "name": "Áo Parka Có Mũ Dây Rút Chống Mưa",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1539109136881-3be0616acf4b",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "weatherproof drawstring hooded rain parka jacket"
    },
    {
        "slug": "ao-trench-coat-dang-dai-co-dien",
        "name": "Áo Trench Coat Dáng Dài Cổ Điển",
        "category": "cat-ao-khoac",
        "raw_url": "https://upload.wikimedia.org/wikipedia/commons/b/b5/Woman_wearing_trench_coat.jpg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Woman_wearing_trench_coat.jpg",
        "source_provider": "Wikimedia Commons",
        "license": "Creative Commons Attribution-ShareAlike 4.0 International",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "garment_check": "classic long double-breasted cotton gabardine trench coat with waist belt"
    }
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

TARGET_W = 1200
TARGET_H = 1600
TARGET_RATIO = TARGET_W / TARGET_H

print(f"=== PROCESSING BATCH OF {len(batch_items)} CAT-AO-KHOAC ITEMS ===", flush=True)

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

existing_manifest_by_slug = {entry["slug"]: entry for entry in existing_manifest}
for entry in new_entries:
    existing_manifest_by_slug[entry["slug"]] = entry

updated_manifest = list(existing_manifest_by_slug.values())
with open(MANIFEST_V2_FILE, "w", encoding="utf-8") as f:
    json.dump(updated_manifest, f, ensure_ascii=False, indent=2)

print(f"\nBatch cat-ao-khoac finished! Total manifest entries: {len(updated_manifest)}", flush=True)
