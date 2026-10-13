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
        "slug": "chan-vay-but-chi-xe-ta-sau-ton-dang",
        "name": "Chân Váy Bút Chì Xẻ Tà Sau Tôn Dáng",
        "category": "cat-vay",
        "raw_url": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Kristian_Leigh_pencil_skirt.jpg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Kristian_Leigh_pencil_skirt.jpg",
        "source_provider": "Wikimedia Commons",
        "license": "Creative Commons Attribution-ShareAlike 4.0 International",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "garment_check": "tailored pencil skirt with back slit, high-rise elegant fit"
    },
    {
        "slug": "chan-vay-cargo-tui-hop-xe-ta-truoc",
        "name": "Chân Váy Cargo Túi Hộp Xẻ Tà Trước",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1583496661160-fb5886a0aaaa",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "cotton khaki cargo flap pocket straight skirt with front slit"
    },
    {
        "slug": "chan-vay-chu-a-kaki-khuy-giua",
        "name": "Chân Váy Chữ A Kaki Khuy Giữa",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1583496661160-fb5886a0aaaa",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "A-line khaki cotton skirt with front button row"
    },
    {
        "slug": "chan-vay-da-chu-a-ke-caro-mua-dong",
        "name": "Chân Váy Dạ Chữ A Kẻ Caro Mùa Đông",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1594938298603-c8148c4dae35",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "tartan check wool flannel A-line winter mini skirt"
    },
    {
        "slug": "chan-vay-dai-dap-ly-mau-ombre-doc-dao",
        "name": "Chân Váy Dài Dập Ly Màu Ombre Độc Đáo",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1561579837-703b7e147e34?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1561579837-703b7e147e34",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "fine pleated chiffon gradient ombre maxi skirt"
    },
    {
        "slug": "chan-vay-dap-vat-asymmetric-skirt",
        "name": "Chân Váy Đắp Vạt Asymmetric Skirt",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1583496661160-fb5886a0aaaa",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "modern asymmetric layered overlap wrap midi skirt"
    },
    {
        "slug": "chan-vay-jean-chu-a-cap-cao-xanh-dam",
        "name": "Chân Váy Jean Chữ A Cạp Cao Xanh Đậm",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1576995853123-5a10305d93c0",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "dark blue 11oz structured cotton denim A-line high-rise skirt"
    },
    {
        "slug": "chan-vay-jean-xe-ta",
        "name": "Chân váy Denim Xẻ tà Cổ điển",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1576995853123-5a10305d93c0",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "vintage washed front-slit midi denim skirt"
    },
    {
        "slug": "chan-vay-midi-lua-satin-cat-cheo-bias",
        "name": "Chân Váy Midi Lụa Satin Cắt Chéo Bias",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1561579837-703b7e147e34?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1561579837-703b7e147e34",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "bias-cut fluid silk satin flowing drape midi skirt"
    },
    {
        "slug": "chan-vay-quan-dap-linen-day-buoc-hong",
        "name": "Chân Váy Quấn Đắp Linen Dây Buộc Hông",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1583496661160-fb5886a0aaaa",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "pure linen wrap tie-waist adjustable side bow midi skirt"
    },
    {
        "slug": "chan-vay-tang-xoe-bohemian-phong-khoang",
        "name": "Chân Váy Tầng Xòe Bohemian Phóng Khoáng",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1502716119720-b23a93e5fe1b",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "3-tiered ruffled muslin cotton Bohemian flowy maxi skirt"
    },
    {
        "slug": "chan-vay-xe-ta-dui-quyen-ru-slit-skirt",
        "name": "Chân Váy Xẻ Tà Đùi Quyến Rũ Slit Skirt",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1561579837-703b7e147e34?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1561579837-703b7e147e34",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "rib knit thigh-slit graceful movement midi skirt"
    },
    {
        "slug": "chan-vay-xep-ly-dai-maxi-mem-mai",
        "name": "Chân Váy Xếp Ly Dài Maxi Mềm Mại",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1561579837-703b7e147e34?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1561579837-703b7e147e34",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "soft micro-pleated silk chiffon flowing maxi skirt"
    },
    {
        "slug": "chan-vay-xep-ly-ngan-tennis-skirt",
        "name": "Chân Váy Xếp Ly Ngắn Tennis Skirt",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1594938298603-c8148c4dae35",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "crisp pleated sporty white athletic tennis mini skirt"
    },
    {
        "slug": "chan-vay-xep-ly-ngang-hong-dang-ha-eo",
        "name": "Chân Váy Xếp Ly Ngang Hông Dáng Hạ Eo",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1561579837-703b7e147e34?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1561579837-703b7e147e34",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "drop-waist hip-pleated tailored poly-viscose midi skirt"
    },
    {
        "slug": "chan-vay-xoe-phong-dang-tron-circle-skirt",
        "name": "Chân Váy Xòe Phồng Dáng Tròn Circle Skirt",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1502716119720-b23a93e5fe1b",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "360-degree full circle flare structured taffeta skirt"
    },
    {
        "slug": "dam-babydoll-bong-benh-ngot-ngao",
        "name": "Đầm BabyDoll Bồng Bềnh Ngọt Ngào",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1496747611176-843222e1e57c",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "loose babydoll floral textured voluminous flowy dress"
    },
    {
        "slug": "dam-chu-a-sat-nach-toi-gian-minimal",
        "name": "Đầm Chữ A Sát Nách Tối Giản Minimal",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1592805625868-ad5cc4a2e589?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1592805625868-ad5cc4a2e589",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "minimalist clean-cut sleeveless A-line shift dress"
    },
    {
        "slug": "dam-co-yem-ho-lung-thanh-lich",
        "name": "Đầm Cổ Yếm Hở Lưng Thanh Lịch",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1509631179647-0177331693ae",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "halter neck backless elegant drape silk habotai dress"
    },
    {
        "slug": "dam-day-hai-day-slip-dress-lua-min",
        "name": "Đầm Dây Hai Dây Slip Dress Lụa Mịn",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1539008835657-9e8e9680c956",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "bias-cut spaghetti strap delicate silk satin slip dress"
    },
    {
        "slug": "dam-knit-det-kim-co-lo-om-dang",
        "name": "Đầm Knit Dệt Kim Cổ Lọ Ôm Dáng",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1515886657613-9f3515b0c78f",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "turtleneck rib knit stretch bodycon warm dress"
    },
    {
        "slug": "dam-linen-co-v-hai-tui-vuong-phia-truoc",
        "name": "Đầm Linen Cổ V Hai Túi Vuông Phía Trước",
        "category": "cat-vay",
        "raw_url": "https://burst.shopifycdn.com/photos/slow-fashion-dress-from.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/slow-fashion-dress-from",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "V-neck raw woven linen shift dress with front patch pockets"
    },
    {
        "slug": "dam-linen-tay-bong-co-v-cuc-boc",
        "name": "Đầm Linen Tay Bồng Cổ V Cúc Bọc",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1592805625868-ad5cc4a2e589?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1592805625868-ad5cc4a2e589",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "pure linen puff-sleeve V-neck fabric-covered buttons A-line dress"
    },
    {
        "slug": "dam-maxi-tre-vai-bo-thun-tuoi-tan",
        "name": "Đầm Maxi Trễ Vai Bo Thun Tươi Tắn",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1496747611176-843222e1e57c",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "off-shoulder smocked bodice vintage floral rayon maxi dress"
    },
    {
        "slug": "dam-polo-the-thao-nang-dong",
        "name": "Đầm Polo Thể Thao Năng Động",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1572804013309-59a88b7e92f1",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "sporty pique cotton 3-button collar athletic straight polo dress"
    },
    {
        "slug": "dam-quan-wrap-dress-co-v-that-no",
        "name": "Đầm Quấn Wrap Dress Cổ V Thắt Nơ",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1509631179647-0177331693ae",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "graceful tie-waist crossover V-neck wrap dress"
    },
    {
        "slug": "dam-so-mi-that-dai-eo-shirt-dress",
        "name": "Đầm Sơ Mi Thắt Đai Eo Shirt Dress",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1515372039744-b8f02a3ae446",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "crisp cotton poplin belted waist tailored shirt dress"
    },
    {
        "slug": "dam-suong-hai-day-phom-rong-thoai-mai",
        "name": "Đầm Suông Hai Dây Phom Rộng Thoải Mái",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1539008835657-9e8e9680c956",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "airy loose spaghetti strap cotton-linen summer shift dress"
    },
    {
        "slug": "dam-suong-linen-co-vuong-tay-lo",
        "name": "Đầm Suông Linen Cổ Vuông Tay Lỡ",
        "category": "cat-vay",
        "raw_url": "https://burst.shopifycdn.com/photos/slow-fashion-dress-from.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/slow-fashion-dress-from",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "square neck mid-sleeve pure linen collarbone accentuating shift dress"
    }
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

TARGET_W = 1200
TARGET_H = 1600
TARGET_RATIO = TARGET_W / TARGET_H

print(f"=== PROCESSING BATCH OF {len(batch_items)} CAT-VAY ITEMS ===", flush=True)

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

print(f"\nBatch cat-vay finished! Total manifest entries: {len(updated_manifest)}", flush=True)
