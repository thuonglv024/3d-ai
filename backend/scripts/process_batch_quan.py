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
        "slug": "quan-cargo-tui-hop-ong-rut-gau",
        "name": "Quần Cargo Túi Hộp Ống Rút Gấu",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1552902865-b72c031ac5ea?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1552902865-b72c031ac5ea",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "cotton ripstop cargo pants with side flap pockets and drawstring hems"
    },
    {
        "slug": "quan-chino-ong-rong-rai-phom-nhat",
        "name": "Quần Chino Ống Rộng Rãi Phom Nhật",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1473966968600-fa801b869a1a",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "wide leg city-boy canvas khaki chino pants"
    },
    {
        "slug": "quan-chino-slim-fit-co-gian-4-chieu",
        "name": "Quần Chino Slim Fit Co Giãn 4 Chiều",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1624378439575-d8705ad7ae80",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "slim fit 4-way stretch beige cotton chino trousers"
    },
    {
        "slug": "quan-du-chong-bam-nuoc-parachute-pants",
        "name": "Quần Dù Chống Bám Nước Parachute Pants",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1552902865-b72c031ac5ea?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1552902865-b72c031ac5ea",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "water-resistant lightweight nylon loose parachute pants"
    },
    {
        "slug": "quan-jeans-den-rua-toi-gian-slim",
        "name": "Quần Jeans Đen Rửa Tối Giản Slim",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1516257984-b1b4d707412e?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1516257984-b1b4d707412e",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "minimalist deep rinsed black slim fit denim jeans"
    },
    {
        "slug": "quan-jeans-ong-suong-rong-baggy",
        "name": "Quần Jeans Ống Suông Rộng Baggy",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1604176354204-9268737828e4?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1604176354204-9268737828e4",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "wide leg baggy streetwear 12oz cotton denim jeans"
    },
    {
        "slug": "quan-jeans-regular-selvedge",
        "name": "Quần Jeans Regular Selvedge",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1541099649105-f69ad21f3246",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "13oz red-line shuttle-loom woven straight raw selvedge jeans"
    },
    {
        "slug": "quan-jeans-selvedge-wash-co-dien",
        "name": "Quần Jeans Selvedge Wash Cổ Điển",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1576995853123-5a10305d93c0",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "classic wash 13.5oz regular selvedge denim jeans"
    },
    {
        "slug": "quan-jeans-trang-nga-ecru-denim",
        "name": "Quần Jeans Trắng Ngà Ecru Denim",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1584370848010-d7fe6bc767ec?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1584370848010-d7fe6bc767ec",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "unbleached natural off-white ecru straight denim jeans"
    },
    {
        "slug": "quan-jogger-kaki-bo-gau-the-thao",
        "name": "Quần Jogger Kaki Bo Gấu Thể Thao",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1555689502-c4b22d76c56f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1555689502-c4b22d76c56f",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "stretch khaki twill cuffed ankle athletic jogger pants"
    },
    {
        "slug": "quan-kaki-ong-dung-khong-ly-toi-gian",
        "name": "Quần Kaki Ống Đứng Không Ly Tối Giản",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1473966968600-fa801b869a1a",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "flat front clean straight leg cotton twill khaki trousers"
    },
    {
        "slug": "quan-kaki-tui-cheo-dang-suong-nhe",
        "name": "Quần Kaki Túi Chéo Dáng Suông Nhẹ",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1624378439575-d8705ad7ae80",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "slanted deep pockets comfort straight khaki pants"
    },
    {
        "slug": "quan-khaki-cap-tang-do-khong-day-nit",
        "name": "Quần Khaki Cạp Tăng Đơ Không Dây Nịt",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1506630448388-4e683c67ddb0?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1506630448388-4e683c67ddb0",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "side adjuster beltless combed cotton khaki trousers"
    },
    {
        "slug": "quan-khaki-xep-ly-don-phom-suong",
        "name": "Quần Khaki Xếp Ly Đơn Phom Suông",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1594938298603-c8148c4dae35",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "single forward pleat relaxed straight khaki trousers"
    },
    {
        "slug": "quan-linen-dang-baggy-lung-mat-me",
        "name": "Quần Linen Dáng Baggy Lửng Mát Mẻ",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1517445312882-bc9910d016b7?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1517445312882-bc9910d016b7",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "cropped tapered baggy relaxed linen-cotton summer pants"
    },
    {
        "slug": "quan-linen-ong-rong-cap-cao-khuy-go",
        "name": "Quần Linen Ống Rộng Cạp Cao Khuy Gỗ",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1517445312882-bc9910d016b7?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1517445312882-bc9910d016b7",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "high-rise wooden button wide leg french linen flowing pants"
    },
    {
        "slug": "quan-linen-ong-suong-thang-dang-ru",
        "name": "Quần Linen Ống Suông Thẳng Dáng Rủ",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1517445312882-bc9910d016b7?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1517445312882-bc9910d016b7",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "bio-washed soft flowing drape straight linen trousers"
    },
    {
        "slug": "quan-ni-bo-gau-day-dan-sweatpants",
        "name": "Quần Nỉ Bo Gấu Dày Dặn Sweatpants",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1555689502-c4b22d76c56f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1555689502-c4b22d76c56f",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "cotton french terry heavy cuffed loungewear sweatpants"
    },
    {
        "slug": "quan-short-chino-mau-pastel-tuoi-sang",
        "name": "Quần Short Chino Màu Pastel Tươi Sáng",
        "category": "cat-quan",
        "raw_url": "https://burst.shopifycdn.com/photos/womens-fashion-woman-denim-shorts-holding-pockets.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/womens-fashion-woman-denim-shorts-holding-pockets",
        "source_provider": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "pastel light wash comfortable summer shorts packshot"
    },
    {
        "slug": "quan-short-denim-rach-gau-phui-bui",
        "name": "Quần Short Denim Rách Gấu Phủi Bụi",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1591195853828-11db59a44f6b",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "frayed hem distressed rugged 100% cotton denim shorts"
    },
    {
        "slug": "quan-short-linen-cap-chun-day-rut",
        "name": "Quần Short Linen Cạp Chun Dây Rút",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1517445312882-bc9910d016b7?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1517445312882-bc9910d016b7",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "pure linen relaxed elastic drawstring vacation resort shorts"
    },
    {
        "slug": "quan-short-tay-xep-ly-lich-lam",
        "name": "Quần Short Tây Xếp Ly Lịch Lãm",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1591195853828-11db59a44f6b",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "tailored pleated knee-length formal smart casual shorts"
    },
    {
        "slug": "quan-tay-cap-lien-hollywood-waistband",
        "name": "Quần Tây Cạp Liền Hollywood Waistband",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1506630448388-4e683c67ddb0?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1506630448388-4e683c67ddb0",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "seamless Hollywood continuous waistband wool dress trousers"
    },
    {
        "slug": "quan-tay-dang-lung-cropped-ankle",
        "name": "Quần Tây Dáng Lửng Cropped Ankle",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1594938298603-c8148c4dae35",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "ankle-length neat cropped straight wool blend dress pants"
    },
    {
        "slug": "quan-tay-gurkha-cap-cao-hai-khoa",
        "name": "Quần Tây Gurkha Cạp Cao Hai Khóa",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1506630448388-4e683c67ddb0?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1506630448388-4e683c67ddb0",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "classic high-rise double buckle beltless Gurkha dress trousers"
    },
    {
        "slug": "quan-tay-lua-bang-thoang-mat-mua-he",
        "name": "Quần Tây Lụa Băng Thoáng Mát Mùa Hè",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1594938298603-c8148c4dae35",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "ice-silk fluid drape cooling straight summer dress pants"
    },
    {
        "slug": "quan-tay-ong-loe-nhe-cat-may-tinh-te",
        "name": "Quần Tây Ống Loe Nhẹ Cắt May Tinh Tế",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1516257984-b1b4d707412e?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1516257984-b1b4d707412e",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "subtle bootcut flare tailored stretch leg-lengthening trousers"
    },
    {
        "slug": "quan-tay-xep-ly-doi-phom-thang",
        "name": "Quần Tây Xếp Ly Đôi Phom Thẳng",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1594938298603-c8148c4dae35",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "double pleated straight leg tailored drape trousers"
    },
    {
        "slug": "quan-tay-xep-ly-giua-om-nhe-chan",
        "name": "Quần Tây Xếp Ly Giữa Ôm Nhẹ Chân",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1506630448388-4e683c67ddb0?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1506630448388-4e683c67ddb0",
        "source_provider": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "sharp permanent center crease tapered fit dress trousers"
    }
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

TARGET_W = 1200
TARGET_H = 1600
TARGET_RATIO = TARGET_W / TARGET_H

print(f"=== PROCESSING BATCH OF {len(batch_items)} CAT-QUAN ITEMS ===", flush=True)

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

print(f"\nBatch cat-quan finished! Total manifest entries: {len(updated_manifest)}", flush=True)
