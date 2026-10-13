import urllib.request
import json
import io
import sys
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

test_manifest = [
    {
        "slug": "ao-blazer-dang-rong-2-hang-khuy",
        "name": "Áo Blazer Dáng Rộng 2 Hàng Khuy",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1781271573424-2cf70e4875cd?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/781271573424-2cf70e4875cd",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "double-breasted suit jacket / blazer, sharp tailoring, dark/charcoal"
    },
    {
        "slug": "ao-choang-len-det-poncho-phong-khoang",
        "name": "Áo Choàng Len Dệt Poncho Phóng Khoáng",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1512361436605-a484bdb34b5f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/woman-wearing-gray-shawl-1512361436605-a484bdb34b5f",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "draped knit wool poncho/shawl, batwing shoulder wrap, charcoal/grey"
    },
    {
        "slug": "ao-khoac-varsity-bong-chay-phoi-da",
        "name": "Áo Khoác Varsity Bóng Chày Phối Da",
        "category": "cat-ao-khoac",
        "raw_url": "https://images.unsplash.com/photo-1749534472739-c038cdf0a63f?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1749534472739-c038cdf0a63f",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "baseball varsity letterman jacket with leather contrast sleeves, black/charcoal body"
    },
    {
        "slug": "so-mi-oxford-classic",
        "name": "Sơ mi Oxford Dáng suông",
        "category": "cat-so-mi",
        "raw_url": "https://burst.shopifycdn.com/photos/back-of-mens-white-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/back-of-mens-white-shirt",
        "source_type": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "crisp white oxford button-down shirt, studio packshot, 5120x3840"
    },
    {
        "slug": "so-mi-co-tru-minimal",
        "name": "Sơ mi Cổ trụ Tối giản",
        "category": "cat-so-mi",
        "raw_url": "https://burst.shopifycdn.com/photos/simple-beige-mens-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/simple-beige-mens-shirt",
        "source_type": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "minimalist clean buttoned shirt beige/sand, studio packshot, 7436x4960"
    },
    {
        "slug": "so-mi-cuban-collar",
        "name": "Sơ mi Cổ Cuba Nghỉ dưỡng",
        "category": "cat-so-mi",
        "raw_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1596755094514-f87e34085b2c",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "relaxed collar camp/cuban shirt, buttoned front"
    },
    {
        "slug": "ao-thun-essential",
        "name": "Áo thun Essential Cotton",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/white-tshirt-template.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/white-tshirt-template",
        "source_type": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "crewneck plain white minimalist cotton t-shirt, studio packshot, 5120x3840"
    },
    {
        "slug": "ao-thun-oversized-heavyweight",
        "name": "Áo thun Heavyweight Oversized",
        "category": "cat-ao-thun",
        "raw_url": "https://burst.shopifycdn.com/photos/grey-t-shirt.jpg",
        "source_page": "https://www.shopify.com/stock-photos/photos/grey-t-shirt",
        "source_type": "Shopify Burst",
        "license": "Shopify Some Rights Reserved (Commercial use allowed)",
        "license_url": "https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved",
        "garment_check": "heavyweight grey/earth tone crewneck t-shirt, studio packshot, 7952x5304"
    },
    {
        "slug": "ao-thun-striped-relaxed",
        "name": "Áo thun Kẻ sọc Relaxed",
        "category": "cat-ao-thun",
        "raw_url": "https://images.unsplash.com/photo-1566816652416-fe5daddceeda?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1566816652416-fe5daddceeda",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "horizontal Breton striped cotton tee, white/blue stripes"
    },
    {
        "slug": "quan-tay-pleated-wide-leg",
        "name": "Quần tây Xếp ly Dáng rộng",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1594938298603-c8148c4dae35",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "tailored pleated trousers, clean drape"
    },
    {
        "slug": "quan-khaki-chino-straight",
        "name": "Quần Khaki Chino Ống đứng",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1624378439575-d8705ad7ae80",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "straight leg beige khaki chino trousers"
    },
    {
        "slug": "quan-linen-cap-chun",
        "name": "Quần Linen Cạp chun Thư giãn",
        "category": "cat-quan",
        "raw_url": "https://images.unsplash.com/photo-1517445312882-bc9910d016b7?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1517445312882-bc9910d016b7",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "relaxed drawstring natural fabric trousers"
    },
    {
        "slug": "chan-vay-pleated-midi",
        "name": "Chân váy Xếp ly Dáng dài Midi",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1561579837-703b7e147e34?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1561579837-703b7e147e34",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "fine pleated midi skirt with elegant drape"
    },
    {
        "slug": "chan-vay-chu-a-linen",
        "name": "Chân váy Chữ A Vải Linen",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1583496661160-fb5886a0aaaa",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "A-line flared skirt, natural texture"
    },
    {
        "slug": "dam-suong-linen-minimal",
        "name": "Đầm suông Linen Tối giản",
        "category": "cat-vay",
        "raw_url": "https://images.unsplash.com/photo-1592805625868-ad5cc4a2e589?w=1600&q=85",
        "source_page": "https://unsplash.com/photos/1592805625868-ad5cc4a2e589",
        "source_type": "Unsplash",
        "license": "Unsplash License (Free commercial & non-commercial use)",
        "license_url": "https://unsplash.com/license",
        "garment_check": "minimalist linen shift dress, clean silhouette"
    }
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print(f"=== TESTING DOWNLOAD OF 15 RAW ASSETS ===")
success = 0
for idx, item in enumerate(test_manifest, 1):
    slug = item["slug"]
    url = item["raw_url"]
    print(f"[{idx}/15] Downloading {slug}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data))
        w, h = img.size
        print(f"  OK: {w}x{h}, {len(data)/1024:.1f} KB, format={img.format}")
        item["raw_width"] = w
        item["raw_height"] = h
        item["raw_bytes"] = len(data)
        success += 1
    except Exception as e:
        print(f"  FAILED: {e}")

print(f"\nResult: {success}/15 successfully downloaded and verified.")
with open("backend/scripts/test_manifest_15.json", "w", encoding="utf-8") as f:
    json.dump(test_manifest, f, ensure_ascii=False, indent=2)
print("Saved manifest to backend/scripts/test_manifest_15.json")
