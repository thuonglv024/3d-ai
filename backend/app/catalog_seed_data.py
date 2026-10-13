"""MORPH Studio Catalog Seed Data.
Contains categories, size charts, and >= 150 fashion products with variants and images.
Preserves the original 22 catalog products verbatim.
"""
import json
from pathlib import Path

DATA_JSON = Path(__file__).resolve().parent / "catalog_data.json"
MANIFEST_V2 = Path(__file__).resolve().parent.parent / "scripts" / "catalog_asset_manifest_v2.json"
V2_MAP = {}
if MANIFEST_V2.exists():
    try:
        with open(MANIFEST_V2, "r", encoding="utf-8") as _f:
            for _item in json.load(_f):
                V2_MAP[_item["slug"]] = (_item["primary_url"], _item["detail_url"])
    except Exception:
        pass

CATEGORIES = [
    {
        "id": "cat-ao-thun",
        "slug": "ao-thun",
        "name": "Áo thun",
        "description": "Áo thun phom suông, chất liệu cotton chải kỹ cao cấp",
        "display_order": 1,
    },
    {
        "id": "cat-so-mi",
        "slug": "so-mi",
        "name": "Sơ mi",
        "description": "Sơ mi dáng suông hiện đại từ linen và oxford thoáng khí",
        "display_order": 2,
    },
    {
        "id": "cat-ao-khoac",
        "slug": "ao-khoac",
        "name": "Áo khoác",
        "description": "Áo blazer, bomber và cardigan tinh tế cho mọi thời tiết",
        "display_order": 3,
    },
    {
        "id": "cat-quan",
        "slug": "quan",
        "name": "Quần",
        "description": "Quần tây xếp ly, chino và linen cạp chun tối giản",
        "display_order": 4,
    },
    {
        "id": "cat-vay",
        "slug": "vay",
        "name": "Váy",
        "description": "Chân váy xếp ly, váy chữ A và đầm suông thanh lịch",
        "display_order": 5,
    },
]

TOP_CHART_ROWS = [
    {"size": "XS", "chest_cm": {"min": 72, "max": 82}, "waist_cm": {"min": 60, "max": 74}},
    {"size": "S", "chest_cm": {"min": 82, "max": 90}, "waist_cm": {"min": 66, "max": 74}},
    {"size": "M", "chest_cm": {"min": 90, "max": 98}, "waist_cm": {"min": 74, "max": 82}},
    {"size": "L", "chest_cm": {"min": 98, "max": 106}, "waist_cm": {"min": 82, "max": 90}},
    {"size": "XL", "chest_cm": {"min": 106, "max": 114}, "waist_cm": {"min": 90, "max": 98}},
    {"size": "XXL", "chest_cm": {"min": 114, "max": 122}, "waist_cm": {"min": 98, "max": 106}},
]

BOTTOM_CHART_ROWS = [
    {"size": "28", "waist_cm": {"min": 68, "max": 72}, "hip_cm": {"min": 86, "max": 92}},
    {"size": "29", "waist_cm": {"min": 70, "max": 76}, "hip_cm": {"min": 90, "max": 96}},
    {"size": "30", "waist_cm": {"min": 74, "max": 80}, "hip_cm": {"min": 94, "max": 100}},
    {"size": "31", "waist_cm": {"min": 78, "max": 84}, "hip_cm": {"min": 98, "max": 104}},
    {"size": "32", "waist_cm": {"min": 82, "max": 88}, "hip_cm": {"min": 102, "max": 108}},
    {"size": "33", "waist_cm": {"min": 86, "max": 92}, "hip_cm": {"min": 106, "max": 112}},
    {"size": "34", "waist_cm": {"min": 90, "max": 96}, "hip_cm": {"min": 110, "max": 116}},
]

SKIRT_CHART_ROWS = [
    {"size": "XS", "waist_cm": {"min": 60, "max": 65}, "hip_cm": {"min": 84, "max": 89}},
    {"size": "S", "waist_cm": {"min": 64, "max": 69}, "hip_cm": {"min": 88, "max": 93}},
    {"size": "M", "waist_cm": {"min": 68, "max": 73}, "hip_cm": {"min": 92, "max": 97}},
    {"size": "L", "waist_cm": {"min": 72, "max": 77}, "hip_cm": {"min": 96, "max": 101}},
    {"size": "XL", "waist_cm": {"min": 76, "max": 82}, "hip_cm": {"min": 100, "max": 106}},
]

SIZE_CHARTS = [
    {
        "id": "chart-ao-thun",
        "name": "Bảng size Áo thun Tiêu chuẩn",
        "garment": "top",
        "source": "illustrative",
        "measurement_basis": "body_cm",
        "table_json": json.dumps({"rows": TOP_CHART_ROWS}, ensure_ascii=False),
    },
    {
        "id": "chart-so-mi",
        "name": "Bảng size Sơ mi Tiêu chuẩn",
        "garment": "top",
        "source": "illustrative",
        "measurement_basis": "body_cm",
        "table_json": json.dumps({"rows": TOP_CHART_ROWS}, ensure_ascii=False),
    },
    {
        "id": "chart-ao-khoac",
        "name": "Bảng size Áo khoác Tiêu chuẩn",
        "garment": "top",
        "source": "illustrative",
        "measurement_basis": "body_cm",
        "table_json": json.dumps({"rows": TOP_CHART_ROWS}, ensure_ascii=False),
    },
    {
        "id": "chart-quan",
        "name": "Bảng size Quần Tiêu chuẩn",
        "garment": "bottom",
        "source": "illustrative",
        "measurement_basis": "body_cm",
        "table_json": json.dumps({"rows": BOTTOM_CHART_ROWS}, ensure_ascii=False),
    },
    {
        "id": "chart-vay",
        "name": "Bảng size Váy Tiêu chuẩn",
        "garment": "bottom",
        "source": "illustrative",
        "measurement_basis": "body_cm",
        "table_json": json.dumps({"rows": SKIRT_CHART_ROWS}, ensure_ascii=False),
    },
]

# Additional curated product templates for expansion
EXPANSION_TEMPLATES = {
    "ao-thun": [
        ("Áo thun Pima Cotton Cổ V", "ao-thun-pima-co-v", 420000, 480000, "Dệt từ sợi Pima siêu dài mềm mại", "100% Pima Cotton 210gsm", "Slim fit tôn dáng"),
        ("Áo thun Raglan Vintage", "ao-thun-raglan-vintage", 360000, 420000, "Thiết kế tay phối màu thể thao cổ điển", "100% Combed Cotton 230gsm", "Relaxed fit thoải mái"),
        ("Áo thun Dệt Kim Knit Tee", "ao-thun-det-kim-knit-tee", 520000, 590000, "Dệt kim mỏng nhẹ mang vẻ thanh lịch", "Cotton pha Silk dệt kim", "Regular fit mềm mại"),
        ("Áo thun Henley Cổ Cài Nút", "ao-thun-henley-co-cai-nut", 450000, 520000, "Cổ trụ cài nút đặc trưng phong trần", "100% Cotton chải kỹ 250gsm", "Regular fit"),
        ("Áo thun Mock Neck Cổ Cao", "ao-thun-mock-neck-co-cao", 440000, 490000, "Cổ đứng 3cm hiện đại giữ ấm cổ", "Cotton dệt đặc 260gsm", "Boxy fit trẻ trung"),
        ("Áo thun Graphic Studio Edition", "ao-thun-graphic-studio-edition", 480000, 550000, "Họa tiết typographic in lụa thủ công", "100% Cotton 240gsm", "Oversized fit"),
        ("Áo thun Polo Dệt Dày Premium", "ao-thun-polo-det-day-premium", 590000, 680000, "Cổ polo dệt bo dày dặn chỉn chu", "Cotton cá sấu 4 chiều", "Regular fit"),
        ("Áo thun Ba Lỗ Tank Top Cotton", "ao-thun-ba-lo-tank-top-cotton", 290000, 350000, "Phom suông nách khoét vừa phải", "100% Cotton 200gsm", "Suông mát mẻ"),
        ("Áo thun Striped Breton Cổ Thuyền", "ao-thun-striped-breton-co-thuyen", 430000, 490000, "Kẻ ngang phong cách thủy thủ Pháp", "100% Cotton dệt jacquard", "Regular fit"),
        ("Áo thun Heavyweight Boxy Cut", "ao-thun-heavyweight-boxy-cut", 470000, 540000, "Vải dày 300gsm giữ form áo vuông vắn", "100% Organic Cotton 300gsm", "Boxy cut ngắn thân"),
        ("Áo thun Polo Dệt Kim Cổ Cuba", "ao-thun-polo-det-kim-co-cuba", 620000, 720000, "Cổ mở chữ V không nút mềm mại", "Cotton len mỏng thoáng khí", "Relaxed fit"),
        ("Áo thun Dài Tay Cổ Lọ Nhẹ", "ao-thun-dai-tay-co-lo-nhe", 460000, 520000, "Tay dài cổ lọ mềm dễ phối layer", "Modal pha Cotton co giãn", "Slim-regular fit"),
        ("Áo thun Sợi Tự Nhiên Không Nhuộm", "ao-thun-soi-tu-nhien-khong-nhuom", 490000, 560000, "Màu sắc mộc từ bông tự nhiên", "100% Bông mộc không tẩy", "Regular fit"),
        ("Áo thun Cotton Lanh Thoáng Hè", "ao-thun-cotton-lanh-thoang-he", 410000, 470000, "Pha lanh tăng độ khô ráo thoáng khí", "70% Cotton 30% Linen", "Relaxed fit suông"),
        ("Áo thun Cổ Tròn Xếp Ly Vai", "ao-thun-co-tron-xep-ly-vai", 450000, 510000, "Chi tiết xếp ly nhỏ tinh tế ở vai", "100% Supima Cotton", "Regular fit"),
        ("Áo thun Rộng Tay Lỡ Drop Shoulder", "ao-thun-rong-tay-lo-drop-shoulder", 420000, 480000, "Vai trễ tay lỡ phủ khuỷu tay", "100% Cotton 230gsm", "Oversized fit"),
        ("Áo thun Dệt Gân Cổ Tròn Ribbed", "ao-thun-det-gan-co-tron-ribbed", 380000, 440000, "Vải dệt gân co giãn ôm nhẹ cơ thể", "Cotton Ribbed dệt co giãn", "Slim fit"),
        ("Áo thun Trơn Tối Giản Basic Tee", "ao-thun-tron-toi-gian-basic-tee", 320000, 380000, "Chiếc áo thun thường nhật không thể thiếu", "100% Cotton 200gsm", "Regular fit"),
        ("Áo thun Tay Bo Cổ Bẻ Cổ Điển", "ao-thun-tay-bo-co-be-co-dien", 480000, 550000, "Tay bo gọn gàng phong cách retro", "100% Cotton chải kỹ", "Classic fit"),
        ("Áo thun Washed Vintage Hiệu Ứng Sờn", "ao-thun-washed-vintage-hieu-ung-son", 510000, 590000, "Nhuộm wash acid tạo vết phai tự nhiên", "Cotton 260gsm giặt đá", "Relaxed boxy"),
        ("Áo thun Henley Tay Dài Khuy Gỗ", "ao-thun-henley-tay-dai-khuy-go", 490000, 560000, "Khuy gỗ phong cách mộc mạc", "100% Waffle Cotton", "Regular fit"),
        ("Áo thun Thể Thao Quick-Dry", "ao-thun-the-thao-quick-dry", 390000, 450000, "Thấm hút mồ hôi và khô cực nhanh", "Poly-spandex sợi mát", "Athletic fit"),
        ("Áo thun Cổ V Sâu Thời Trang", "ao-thun-co-v-sau-thoi-trang", 370000, 430000, "Cổ chữ V tôn đường nét cổ và ngực", "100% Cotton chải kỹ", "Slim fit"),
        ("Áo thun Túi Ngực Minimal Pocket", "ao-thun-tui-nguc-minimal-pocket", 395000, 450000, "Túi đắp vuông tối giản góc ngực trái", "100% Cotton 240gsm", "Regular fit"),
        ("Áo thun Mercerized Bóng Mịn", "ao-thun-mercerized-bong-min", 560000, 650000, "Sợi xử lý mercerized ánh bóng sang trọng", "100% Mercerized Cotton", "Tailored fit"),
        ("Áo thun In Chữ Tối Giản Studio", "ao-thun-in-chu-toi-gian-studio", 430000, 490000, "Chi tiết slogan in nổi vi mô trước ngực", "100% Combed Cotton", "Relaxed fit"),
        ("Áo thun Cổ Thuyền Bateaux Dáng Rộng", "ao-thun-co-thuyen-bateaux-dang-rong", 460000, 520000, "Thiết kế cổ thuyền thanh thoát bay bổng", "Cotton lụa mềm mát", "Oversized fit"),
    ],
    "so-mi": [
        ("Sơ mi Lụa Pha Cotton Mịn Mượt", "so-mi-lua-pha-cotton-min-muot", 690000, 790000, "Ánh bóng nhẹ từ sợi tơ tằm thượng hạng", "80% Cotton 20% Silk", "Relaxed fit thanh lịch"),
        ("Sơ mi Denim Selvedge Rửa Nhẹ", "so-mi-denim-selvedge-rua-nhe", 650000, 750000, "Vải denim dệt biên bền chắc cá tính", "100% Selvedge Denim 6.5oz", "Regular fit"),
        ("Sơ mi Flanel Kẻ Caro Ấm Áp", "so-mi-flanel-ke-caro-am-ap", 580000, 670000, "Chất nỉ bông mềm ấm áp mùa thu đông", "100% Cotton Flanel chải lông", "Relaxed fit"),
        ("Sơ mi Chambray Xanh Indigo", "so-mi-chambray-xanh-indigo", 590000, 680000, "Sợi dệt thô mộc phong cách Workwear", "100% Cotton Chambray", "Regular fit"),
        ("Sơ mi Poplin Dáng Suông Công Sở", "so-mi-poplin-dang-suong-cong-so", 540000, 620000, "Mặt vải poplin đanh mịn chống nhăn", "100% Poplin Cotton 120s", "Classic suông"),
        ("Sơ mi Cổ Tàu Khuy Ẩn Tối Giản", "so-mi-co-tau-khuy-an-toi-gian", 610000, 700000, "Nẹp áo che hàng cúc thanh lịch hiện đại", "Cotton pha Tencel thoáng mát", "Modern fit"),
        ("Sơ mi Linen Tay Ngắn Mùa Hè", "so-mi-linen-tay-ngan-mua-he", 530000, 610000, "Tay ngắn mát mẻ cho những ngày hè oi ả", "100% Pure French Linen", "Relaxed fit"),
        ("Sơ mi Kẻ Sọc Bengal Stripe", "so-mi-ke-soc-bengal-stripe", 570000, 650000, "Kẻ sọc lam thanh lịch chuẩn phong cách Anh", "100% Giza Cotton dệt sọc", "Regular fit"),
        ("Sơ mi Overshirt Dày Dặn Hai Túi", "so-mi-overshirt-day-dan-hai-tui", 750000, 860000, "Khoác ngoài như áo jacket nhẹ thời thượng", "Cotton Canvas dày dặn", "Boxy overshirt"),
        ("Sơ mi Cổ Cuba Họa Tiết Lá Nhiệt Đới", "so-mi-co-cuba-hoa-tiet-la-nhiet-doi", 560000, 640000, "Họa tiết in chìm tinh tế phong cách Resort", "100% Viscose Rayon rũ mát", "Cuban relaxed"),
        ("Sơ mi Trắng Cổ Nhọn Formal", "so-mi-trang-co-nhon-formal", 620000, 720000, "Phù hợp phối suit và thắt cà vạt cao cấp", "100% Cotton 2 ply 100s", "Tailored fit"),
        ("Sơ mi Dệt Gân Seersucker Sủi Bọt", "so-mi-det-gan-seersucker-sui-bot", 590000, 680000, "Vải dệt sủi tạo khe thoáng không dính da", "100% Cotton Seersucker", "Relaxed fit"),
        ("Sơ mi Cổ Lãnh Tụ Linen Thô", "so-mi-co-lanh-tu-linen-tho", 580000, 660000, "Chất vải linen dệt thưa phong trần tự tại", "100% Linen tự nhiên", "Suông thoải mái"),
        ("Sơ mi Kẻ Windowpane Ô Vuông Nhỏ", "so-mi-ke-windowpane-o-vuong-nho", 560000, 640000, "Họa tiết kẻ ô mảnh nhẹ nhàng thanh nhã", "100% Cotton chải kỹ", "Regular fit"),
        ("Sơ mi Cổ Tròn Dáng Dài Tunic", "so-mi-co-tron-dang-dai-tunic", 630000, 730000, "Vạt dài xẻ tà nghệ thuật và cá tính", "Linen pha Rayon mềm rũ", "Long tunic fit"),
        ("Sơ mi Dáng Rộng Thụng Oversize", "so-mi-dang-rong-thung-oversize", 590000, 690000, "Phom áo rộng phóng khoáng theo xu hướng Seoul", "100% Cotton Oxford wash", "Oversized"),
        ("Sơ mi Lụa Satin Bóng Sang Trọng", "so-mi-lua-satin-bong-sang-trong", 790000, 920000, "Bề mặt satin bóng mềm rủ quý phái", "Satin lụa pha tencel", "Fluid fit"),
        ("Sơ mi Cổ Bẻ Cuban Kẻ Sọc Dọc", "so-mi-co-be-cuban-ke-soc-doc", 550000, 630000, "Kẻ sọc dọc phối màu trung tính nhã nhặn", "Cotton linen mỏng nhẹ", "Relaxed fit"),
        ("Sơ mi Denim Rách Nhẹ Đậm Chất Bụi", "so-mi-denim-rach-nhe-dam-chat-bui", 670000, 770000, "Chi tiết mài sờn nhẹ tự nhiên", "100% Cotton Denim 7oz", "Regular fit"),
        ("Sơ mi Oxford Tay Ngắn Gấp Gấu", "so-mi-oxford-tay-ngan-gap-gau", 510000, 590000, "Tay áo gấp gấu phong cách hè trẻ trung", "100% Oxford Cotton", "Classic regular"),
        ("Sơ mi Dệt Jacquard Họa Tiết Chìm", "so-mi-det-jacquard-hoa-tiet-chim", 680000, 790000, "Họa tiết dệt chìm tạo chiều sâu tinh xảo", "100% Cotton Jacquard", "Modern fit"),
        ("Sơ mi Tay Bồng Nữ Tính Nhẹ Nhàng", "so-mi-tay-bong-nu-tinh-nhe-nhang", 540000, 630000, "Cổ áo lá sen tay bo nhún nhẹ duyên dáng", "Cotton tơ tằm dệt mỏng", "Flattering fit"),
        ("Sơ mi Linen Nhuộm Tràm Tự Nhiên", "so-mi-linen-nhuom-tram-tu-nhien", 720000, 830000, "Màu xanh tràm truyền thống nhuộm thủ công", "100% Indigo Dyed Linen", "Regular fit"),
        ("Sơ mi Khuy Xà Cừ Cắt May Thủ Công", "so-mi-khuy-xa-cu-cat-may-thu-cong", 750000, 870000, "Khuy khảm ốc xà cừ tự nhiên sang trọng", "Cotton dệt 140s cao cấp", "Tailored fit"),
        ("Sơ mi Vạt Lệch Asymmetric Hem", "so-mi-vat-lech-asymmetric-hem", 610000, 710000, "Vạt trước lệch tà mang hơi thở avant-garde", "100% Poplin Cotton", "Loose fit"),
        ("Sơ mi Cổ Choker Nơ Buộc", "so-mi-co-choker-no-buoc", 570000, 660000, "Dải nơ cổ thanh thoát có thể thắt hoặc buông lơi", "Chiffon tơ nhân tạo", "Soft elegant"),
        ("Sơ mi Kẻ Gingham Nhỏ Năng Động", "so-mi-ke-gingham-nho-nang-dong", 520000, 600000, "Họa tiết kẻ ca-rô nhỏ tươi trẻ dễ phối đồ", "100% Cotton chải kỹ", "Regular fit"),
    ],
    "ao-khoac": [
        ("Áo Blazer Cổ Tròn Không ve Minimal", "ao-blazer-co-tron-khong-ve-minimal", 1250000, 1450000, "Thiết kế loại bỏ ve cổ truyền thống hiện đại", "Wool blend pha sợi tơ", "Clean boxy"),
        ("Áo Bomber Kaki Lót Lụa Đẳng Cấp", "ao-bomber-kaki-lot-lua-dang-cap", 980000, 1150000, "Lớp lót lụa habotai êm ái trượt trên da", "Cotton Twill chống nước nhẹ", "Relaxed bomber"),
        ("Áo Trench Coat Dáng Dài Cổ Điển", "ao-trench-coat-dang-dai-co-dien", 1590000, 1850000, "Áo khoác dáng dài qua gối với đai thắt eo", "Gabardine Cotton chống thấm", "Overcoat fit"),
        ("Áo Khoác Denim Vintage Wash Xanh Nhạt", "ao-khoac-denim-vintage-wash-xanh-nhat", 890000, 1050000, "Nhuộm wash cổ điển phối chỉ vàng vintage", "100% Cotton Denim 13oz", "Regular trucker"),
        ("Áo Cardigan Cổ V Cúc Sừng", "ao-cardigan-co-v-cuc-sung", 750000, 880000, "Cúc làm từ sừng tự nhiên dệt len mềm mại", "Len Merino pha Cotton", "Relaxed fit"),
        ("Áo Blazer Dáng Rộng 2 Hàng Khuy", "ao-blazer-dang-rong-2-hang-khuy", 1350000, 1550000, "Blazer double-breasted quyền lực và cá tính", "Wool twill đứng phom", "Oversized tailoring"),
        ("Áo Khoác Dù Windbreaker Chống Nước", "ao-khoac-du-windbreaker-chong-nuoc", 690000, 790000, "Gọn nhẹ dễ gấp gọn mang theo mọi nơi", "Nylon ripstop phủ nano", "Sporty regular"),
        ("Áo Khoác Dáng Sơ Mi Shacket Dạ Ép", "ao-khoac-dang-so-mi-shacket-da-ep", 920000, 1080000, "Chất dạ ép mịn giữ ấm tốt ngày se lạnh", "Dạ ép sợi len tổng hợp", "Boxy shacket"),
        ("Áo Khoác Dáng Kimono Linen Tối Giản", "ao-khoac-dang-kimono-linen-toi-gian", 780000, 900000, "Áo khoác buộc vạt cảm hứng Á Đông", "100% Pure Linen 280gsm", "Loose drape"),
        ("Áo Khoác Field Jacket Bốn Túi Quân Đội", "ao-khoac-field-jacket-bon-tui-quan-doi", 1120000, 1290000, "Thiết kế túi hộp utility đa năng tiện dụng", "Cotton Canvas chống sờn", "Relaxed utilitarian"),
        ("Áo Khoác Da Lộn Suede Giả Da Cao Cấp", "ao-khoac-da-lon-suede-gia-da-cao-cap", 1290000, 1490000, "Bề mặt mềm như nhung không bong tróc", "Microfiber Faux Suede", "Tailored fit"),
        ("Áo Cardigan Dệt Dày Cable Knit Vặn Thừng", "ao-cardigan-det-day-cable-knit-van-thung", 860000, 990000, "Họa tiết vặn thừng dày dặn ấm cúng", "Wool blend dệt kim nổi", "Cozy oversized"),
        ("Áo Blazer Cắt Ngắn Cropped Năng Động", "ao-blazer-cat-ngan-cropped-nang-dong", 950000, 1100000, "Thân áo cắt ngang eo tôn chiều dài chân", "Polyester twill cao cấp", "Cropped modern"),
        ("Áo Khoác Trút Phao Trần Bông Siêu Nhẹ", "ao-khoac-trut-phao-tran-bong-sieu-nhe", 890000, 1020000, "Chần bông hình sóng nhẹ tênh giữ ấm", "Nylon dệt mật độ cao", "Regular fit"),
        ("Áo Khoác Harrington Cổ Bẻ Lót Caro", "ao-khoac-harrington-co-be-lot-caro", 980000, 1150000, "Phong cách Mod kinh điển vượt thời gian", "Cotton pha Poly chống gió", "Classic Harrington"),
        ("Áo Khoác Varsity Bóng Chày Phối Da", "ao-khoac-varsity-bong-chay-phoi-da", 1190000, 1380000, "Tay áo phối da PU thân dạ dày ấm", "Len dạ pha da tổng hợp", "Varsity boxy"),
        ("Áo Parka Có Mũ Dây Rút Chống Mưa", "ao-parka-co-mu-day-rut-chong-mua", 1250000, 1450000, "Mũ trùm đầu sâu có dây rút bảo vệ tối ưu", "Polyester pha Cotton wax", "Parka oversized"),
        ("Áo Khoác Gile Vest Trần Bông Phối Layer", "ao-khoac-gile-vest-tran-bong-phoi-layer", 650000, 750000, "Áo sát nách giữ ấm ngực dễ kết hợp đồ", "Nylon mờ lót bông sinh học", "Regular gile"),
        ("Áo Blazer Cộc Tay Mùa Hè Linen", "ao-blazer-coc-tay-mua-he-linen", 890000, 1020000, "Tay cộc thoáng mát thanh lịch nơi công sở", "100% Linen tự nhiên", "Relaxed fit"),
        ("Áo Khoác Trench Ngắn Tay Raglan", "ao-khoac-trench-ngan-tay-raglan", 1150000, 1320000, "Dáng áo ngắn hiện đại cho người năng động", "Cotton Twill chống nhăn", "Raglan regular"),
        ("Áo Cardigan Khuy Bấm Kim Loại Hiện Đại", "ao-cardigan-khuy-bam-kim-loai-hien-dai", 780000, 890000, "Khuy bấm kim loại mạ bạc sáng bóng", "Cotton dệt đặc mịn", "Slim relaxed"),
        ("Áo Khoác Dạ Dáng Dài Ve To Cổ Điển", "ao-khoac-da-dang-dai-ve-to-co-dien", 1680000, 1950000, "Ve cổ bẻ to bản phong cách quý tộc châu Âu", "60% Wool 40% Viscose", "Tailored long"),
        ("Áo Blazer Linen Phom Suông Màu Cát", "ao-blazer-linen-phom-suong-mau-cat", 1090000, 1280000, "Màu be cát tự nhiên phóng khoáng", "100% Linen Ý", "Relaxed suông"),
        ("Áo Khoác Gió Hai Lớp Thể Thao", "ao-khoac-gio-hai-lop-the-thao", 620000, 720000, "Lớp lưới bên trong thoáng khí chống bí", "Nylon dù siêu nhẹ", "Sporty fit"),
        ("Áo Khoác Nhung Tăm Corduroy Ấm Áp", "ao-khoac-nhung-tam-corduroy-am-ap", 890000, 1050000, "Vải nhung tăm sợi nổi retro hoài niệm", "100% Cotton Corduroy", "Regular trucker"),
        ("Áo Choàng Len Dệt Poncho Phóng Khoáng", "ao-choang-len-det-poncho-phong-khoang", 850000, 980000, "Dáng cánh dơi phủ vai tự do bay bổng", "Len dệt pha acrylic mềm", "One size loose"),
        ("Áo Khoác Safari Bốn Túi Vải Linen", "ao-khoac-safari-bon-tui-vai-linen", 990000, 1150000, "Phong cách viễn thám cổ điển đầy cuốn hút", "100% Linen dệt dày", "Safari regular"),
        ("Áo Bomber Nỉ Bông Dày Giữ Ấm", "ao-bomber-ni-bong-day-giu-am", 730000, 840000, "Chất nỉ bông cào ấm áp trong tiết trời lạnh", "Cotton nỉ 380gsm", "Bomber boxy"),
    ],
    "quan": [
        ("Quần Tây Xếp Ly Đôi Phom Thẳng", "quan-tay-xep-ly-doi-phom-thang", 620000, 720000, "Xếp 2 ly trước tạo độ phồng nhẹ tinh tế", "Polyester pha Viscose co giãn", "Straight pleated"),
        ("Quần Chino Slim Fit Co Giãn 4 Chiều", "quan-chino-slim-fit-co-gian-4-chieu", 560000, 650000, "Vận động linh hoạt không lo gò bó", "97% Cotton 3% Spandex", "Slim fit tôn chân"),
        ("Quần Jeans Ống Suông Rộng Baggy", "quan-jeans-ong-suong-rong-baggy", 690000, 790000, "Phom baggy rộng rãi theo phong cách streetwear", "100% Cotton Denim 12oz", "Baggy loose"),
        ("Quần Linen Ống Rộng Cạp Cao Khuy Gỗ", "quan-linen-ong-rong-cap-cao-khuy-go", 590000, 680000, "Cạp cao kéo dài chân tự nhiên", "100% Linen Pháp", "Wide leg suông"),
        ("Quần Cargo Túi Hộp Ống Rút Gấu", "quan-cargo-tui-hop-ong-rut-gau", 640000, 740000, "Túi hộp hai bên kèm dây rút túm gấu", "Cotton Ripstop chống rách", "Relaxed cargo"),
        ("Quần Tây Dáng Lửng Cropped Ankle", "quan-tay-dang-lung-cropped-ankle", 580000, 670000, "Độ dài chạm mắt cá chân gọn gàng", "Wool blend đứng dáng", "Cropped straight"),
        ("Quần Jogger Kaki Bo Gấu Thể Thao", "quan-jogger-kaki-bo-gau-the-thao", 490000, 570000, "Cạp chun dây rút và gấu bo năng động", "Cotton Twill co giãn", "Jogger fit"),
        ("Quần Short Tây Xếp Ly Lịch Lãm", "quan-short-tay-xep-ly-lich-lam", 450000, 520000, "Độ dài trên gối phối cùng sơ mi và polo", "Poly-viscose chống nhăn", "Tailored shorts"),
        ("Quần Khaki Cạp Tăng Đơ Không Dây Nịt", "quan-khaki-cap-tang-do-khong-day-nit", 630000, 730000, "Khóa tăng đơ bên hông điều chỉnh eo", "100% Combed Cotton Khaki", "Classic straight"),
        ("Quần Jeans Selvedge Wash Cổ Điển", "quan-jeans-selvedge-wash-co-dien", 850000, 990000, "Đường may biên đỏ cuộn gấu đặc trưng", "100% Selvedge Denim 13.5oz", "Regular fit"),
        ("Quần Linen Dáng Baggy Lửng Mát Mẻ", "quan-linen-dang-baggy-lung-mat-me", 530000, 610000, "Đũng thụng nhẹ và ống ôm dần xuống gấu", "Linen pha Cotton mộc", "Baggy cropped"),
        ("Quần Tây Gurkha Cạp Cao Hai Khóa", "quan-tay-gurkha-cap-cao-hai-khoa", 720000, 830000, "Đai Gurkha huyền thoại không cần dây lưng", "Viscose pha Wool cao cấp", "Gurkha high-rise"),
        ("Quần Kaki Ống Đứng Không Ly Tối Giản", "quan-kaki-ong-dung-khong-ly-toi-gian", 540000, 620000, "Thiết kế phẳng phiu cho vẻ ngoài hiện đại", "100% Cotton Twill", "Straight leg"),
        ("Quần Nỉ Bo Gấu Dày Dặn Sweatpants", "quan-ni-bo-gau-day-dan-sweatpants", 480000, 550000, "Mặt trong nỉ bông êm ái cho ngày nghỉ", "100% Cotton French Terry", "Relaxed fit"),
        ("Quần Short Linen Cạp Chun Dây Rút", "quan-short-linen-cap-chun-day-rut", 390000, 460000, "Chiếc quần ngắn hoàn hảo cho kỳ nghỉ biển", "100% Pure Linen", "Relaxed short"),
        ("Quần Jeans Đen Rửa Tối Giản Slim", "quan-jeans-den-rua-toi-gian-slim", 620000, 710000, "Màu đen sâu giữ màu bền sau nhiều lần giặt", "98% Cotton 2% Elastane", "Slim fit"),
        ("Quần Tây Ống Loe Nhẹ Cắt May Tinh Tế", "quan-tay-ong-loe-nhe-cat-may-tinh-te", 680000, 780000, "Ống loe nhẹ phần gấu giúp đôi chân thon dài", "Poly-spandex co giãn 2 chiều", "Flared tailored"),
        ("Quần Dù Chống Bám Nước Parachute Pants", "quan-du-chong-bam-nuoc-parachute-pants", 570000, 660000, "Phom phồng bồng bềnh phong cách Y2K", "Nylon dệt mỏng", "Parachute loose"),
        ("Quần Tây Cạp Liền Hollywood Waistband", "quan-tay-cap-lien-hollywood-waistband", 740000, 850000, "Cạp liền không đường may cắt ngang eo", "Wool touch twill", "Classic regular"),
        ("Quần Kaki Túi Chéo Dáng Suông Nhẹ", "quan-kaki-tui-cheo-dang-suong-nhe", 520000, 600000, "Túi chéo sâu tiện lợi đựng điện thoại", "Cotton Twill 280gsm", "Comfort straight"),
        ("Quần Short Denim Rách Gấu Phủi Bụi", "quan-short-denim-rach-gau-phui-bui", 440000, 510000, "Gấu cắt sờn tự nhiên khỏe khoắn", "100% Cotton Denim", "Regular shorts"),
        ("Quần Tây Lụa Băng Thoáng Mát Mùa Hè", "quan-tay-lua-bang-thoang-mat-mua-he", 610000, 700000, "Chất liệu sợi làm mát hạ nhiệt cơ thể", "Ice-silk pha Polyester", "Straight drape"),
        ("Quần Jeans Trắng Ngà Ecru Denim", "quan-jeans-trang-nga-ecru-denim", 670000, 770000, "Sợi denim màu mộc tự nhiên không tẩy", "100% Unbleached Cotton", "Straight regular"),
        ("Quần Chino Ống Rộng Rãi Phom Nhật", "quan-chino-ong-rong-rai-phom-nhat", 640000, 730000, "Phom dáng rộng rãi phong cách City Boy Nhật Bản", "100% Cotton Canvas", "Japanese wide-leg"),
        ("Quần Tây Xếp Ly Giữa Ôm Nhẹ Chân", "quan-tay-xep-ly-giua-om-nhe-chan", 590000, 680000, "Ly ủi nhiệt giữ nếp vĩnh viễn", "Terylene pha Rayon", "Tapered fit"),
        ("Quần Short Chino Màu Pastel Tươi Sáng", "quan-short-chino-mau-pastel-tuoi-sang", 420000, 490000, "Tone màu pastel dịu mát cho mùa nắng", "Cotton Khaki mềm", "Regular short"),
        ("Quần Linen Ống Suông Thẳng Dáng Rủ", "quan-linen-ong-suong-thang-dang-ru", 580000, 670000, "Độ rủ tự nhiên mềm mại mỗi bước đi", "100% Linen wash sinh học", "Straight loose"),
        ("Quần Khaki Xếp Ly Đơn Phom Suông", "quan-khaki-xep-ly-don-phom-suong", 550000, 630000, "Một ly trước thanh lịch dễ ứng dụng", "100% Cotton Khaki", "Relaxed fit"),
    ],
    "vay": [
        ("Chân Váy Xếp Ly Dài Maxi Mềm Mại", "chan-vay-xep-ly-dai-maxi-mem-mai", 590000, 690000, "Nếp gấp ly dập nhỏ bay bổng khi chuyển động", "Chiffon lụa xếp nếp", "Maxi thướt tha"),
        ("Chân Váy Chữ A Kaki Khuy Giữa", "chan-vay-chu-a-kaki-khuy-giua", 480000, 560000, "Hàng khuy gỗ chạy dọc thân trước", "Cotton Kaki dày dặn", "Chữ A cổ điển"),
        ("Đầm Suông Linen Cổ Vuông Tay Lỡ", "dam-suong-linen-co-vuong-tay-lo", 720000, 830000, "Cổ vuông khoe xương quai xanh thanh mảnh", "100% Linen cao cấp", "Suông thoải mái"),
        ("Chân Váy Bút Chì Xẻ Tà Sau Tôn Dáng", "chan-vay-but-chi-xe-ta-sau-ton-dang", 540000, 620000, "Ôm nhẹ vòng 3 xẻ tà sau dễ di chuyển", "Cotton pha Spandex đứng phom", "Pencil ôm vừa"),
        ("Đầm Quấn Wrap Dress Cổ V Thắt Nơ", "dam-quan-wrap-dress-co-v-that-no", 780000, 890000, "Vạt quấn đắp chéo che khuyết điểm vòng 2", "Lụa nhân tạo pha Tencel", "Wrap fit duyên dáng"),
        ("Chân Váy Tầng Xòe Bohemian Phóng Khoáng", "chan-vay-tang-xoe-bohemian-phong-khoang", 630000, 730000, "Ba tầng bèo nhún nhẹ nhàng thướt tha", "Cotton xô Muslin 2 lớp", "Boho tiered"),
        ("Đầm Sơ Mi Thắt Đai Eo Shirt Dress", "dam-so-mi-that-dai-eo-shirt-dress", 750000, 860000, "Sự giao thoa giữa sơ mi chỉn chu và đầm duyên dáng", "Cotton Poplin 100s", "Shirt dress fit"),
        ("Chân Váy Jean Chữ A Cạp Cao Xanh Đậm", "chan-vay-jean-chu-a-cap-cao-xanh-dam", 520000, 600000, "Chất denim dày dặn giữ phom chữ A chuẩn", "100% Cotton Denim 11oz", "Chữ A cạp cao"),
        ("Đầm Dây Hai Dây Slip Dress Lụa Mịn", "dam-day-hai-day-slip-dress-lua-min", 690000, 790000, "Dây vai mảnh lưng trần quyến rũ", "Satin lụa dệt mịn rủ", "Bias cut ôm nhẹ"),
        ("Chân Váy Xếp Ly Ngắn Tennis Skirt", "chan-vay-xep-ly-ngan-tennis-skirt", 420000, 490000, "Phong cách thể thao năng động trẻ trung", "Polyester twill đứng nếp", "Tennis mini"),
        ("Đầm Knit Dệt Kim Cổ Lọ Ôm Dáng", "dam-knit-det-kim-co-lo-om-dang", 790000, 920000, "Len dệt gân co giãn giữ ấm ngày thu", "Cotton len dệt kim gân", "Slim bodycon nhẹ"),
        ("Chân Váy Midi Lụa Satin Cắt Chéo Bias", "chan-vay-midi-lua-satin-cat-cheo-bias", 650000, 760000, "Cắt xéo canh sợi tạo độ lượn sóng tự nhiên", "Satin tơ lụa mềm mướt", "Bias drape"),
        ("Đầm Linen Tay Bồng Cổ V Cúc Bọc", "dam-linen-tay-bong-co-v-cuc-boc", 820000, 950000, "Chi tiết cúc bọc vải cùng màu tinh xảo", "100% Linen tự nhiên", "A-line fit"),
        ("Chân Váy Đắp Vạt Asymmetric Skirt", "chan-vay-dap-vat-asymmetric-skirt", 580000, 670000, "Vạt trước lệch tầng hiện đại và cá tính", "Poly-viscose chống nhăn", "Modern asymmetric"),
        ("Đầm Suông Hai Dây Phom Rộng Thoải Mái", "dam-suong-hai-day-phom-rong-thoai-mai", 610000, 700000, "Phom đầm suông rộng bay bổng cho ngày hè", "Cotton lanh thoáng mát", "Loose airy"),
        ("Chân Váy Dạ Chữ A Kẻ Caro Mùa Đông", "chan-vay-da-chu-a-ke-caro-mua-dong", 560000, 650000, "Chất vải dạ ấm áp họa tiết kẻ Tartan", "Dạ len chải mịn", "A-line mini"),
        ("Đầm Cổ Yếm Hở Lưng Thanh Lịch", "dam-co-yem-ho-lung-thanh-lich", 850000, 980000, "Cổ yếm mềm buộc nơ sau gáy quý phái", "Lụa Habotai 2 lớp", "Flattering flow"),
        ("Chân Váy Cargo Túi Hộp Xẻ Tà Trước", "chan-vay-cargo-tui-hop-xe-ta-truoc", 530000, 620000, "Phong cách streetwear tiện dụng khỏe khoắn", "Cotton Kaki ripstop", "Straight cargo"),
        ("Đầm Maxi Trễ Vai Bo Thun Tươi Tắn", "dam-maxi-tre-vai-bo-thun-tuoi-tan", 760000, 880000, "Thân áo bo thun smocking co giãn ôm ngực", "Rayon hoa nhí vintage", "Maxi off-shoulder"),
        ("Chân Váy Xòe Phồng Dáng Tròn Circle Skirt", "chan-vay-xoe-phong-dang-tron-circle-skirt", 590000, 690000, "Xòe tròn 360 độ điệu đà thanh lịch", "Taffeta bóng nhẹ đứng dáng", "Full circle"),
        ("Đầm Polo Thể Thao Năng Động", "dam-polo-the-thao-nang-dong", 580000, 670000, "Cổ bẻ cài 3 khuy phong cách sporty chic", "Cotton cá sấu 4 chiều", "Straight sporty"),
        ("Chân Váy Xếp Ly Ngang Hông Dáng Hạ Eo", "chan-vay-xep-ly-ngang-hong-dang-ha-eo", 570000, 660000, "Thân trên ôm nhẹ thân dưới dập ly", "Poly-viscose cao cấp", "Drop-waist midi"),
        ("Đầm Chữ A Sát Nách Tối Giản Minimal", "dam-chu-a-sat-nach-toi-gian-minimal", 670000, 770000, "Đường cắt tối giản không chi tiết thừa", "Cotton Twill đanh mịn", "Shift A-line"),
        ("Chân Váy Quấn Đắp Linen Dây Buộc Hông", "chan-vay-quan-dap-linen-day-buoc-hong", 540000, 630000, "Buộc nơ lệch hông tự điều chỉnh độ vừa", "100% Pure Linen", "Wrap midi"),
        ("Đầm BabyDoll Bồng Bềnh Ngọt Ngào", "dam-babydoll-bong-benh-ngot-ngao", 640000, 740000, "Dáng babydoll xòe rộng giấu khuyết điểm", "Cotton xốp dệt nổi hoa", "Babydoll loose"),
        ("Chân Váy Xẻ Tà Đùi Quyến Rũ Slit Skirt", "chan-vay-xe-ta-dui-quyen-ru-slit-skirt", 560000, 650000, "Xẻ tà đùi trước vừa phải bước đi uyển chuyển", "Thun Ribbed dệt kim", "Midi slit"),
        ("Đầm Linen Cổ V Hai Túi Vuông Phía Trước", "dam-linen-co-v-hai-tui-vuong-phia-truoc", 710000, 820000, "Hai túi vuông nổi tiện lợi phong cách mộc", "100% Linen dệt thô", "Relaxed shift"),
        ("Chân Váy Dài Dập Ly Màu Ombre Độc Đáo", "chan-vay-dai-dap-ly-mau-ombre-doc-dao", 680000, 790000, "Hiệu ứng chuyển màu ombre huyền ảo tinh tế", "Chiffon dập ly nhỏ", "Maxi pleated"),
    ],
}

DEFAULT_PALETTES = {
    "ao-thun": [
        {"name": "Trắng ngà", "hex": "#f4f1ea"},
        {"name": "Đen tuyền", "hex": "#1f2220"},
        {"name": "Xám tiêu", "hex": "#8a8d8f"},
        {"name": "Xanh navy", "hex": "#1b2a4a"},
        {"name": "Nâu be", "hex": "#c4a482"},
    ],
    "so-mi": [
        {"name": "Trắng tinh", "hex": "#ffffff"},
        {"name": "Xanh baby", "hex": "#a3c1ad"},
        {"name": "Xanh sọc lam", "hex": "#4a76a8"},
        {"name": "Be nhạt", "hex": "#dcd0c0"},
        {"name": "Hồng pastel", "hex": "#e8c5c8"},
    ],
    "ao-khoac": [
        {"name": "Đen than", "hex": "#1a1a1a"},
        {"name": "Be sáng", "hex": "#e2d7c5"},
        {"name": "Nâu camel", "hex": "#9c6b3e"},
        {"name": "Xanh rêu", "hex": "#354a21"},
        {"name": "Xám ghi", "hex": "#5e6572"},
    ],
    "quan": [
        {"name": "Đen tuyền", "hex": "#1f2220"},
        {"name": "Xám chì", "hex": "#3a3d40"},
        {"name": "Be kaki", "hex": "#c2b280"},
        {"name": "Nâu cà phê", "hex": "#4b382a"},
        {"name": "Xanh indigo", "hex": "#2e4482"},
    ],
    "vay": [
        {"name": "Đen tuyền", "hex": "#1f2220"},
        {"name": "Trắng kem", "hex": "#f7f5f0"},
        {"name": "Nâu caramel", "hex": "#8b5a2b"},
        {"name": "Hồng phấn", "hex": "#f4c2c2"},
        {"name": "Xanh olive", "hex": "#556b2f"},
    ],
}

DEFAULT_SIZES = {
    "ao-thun": ["XS", "S", "M", "L", "XL"],
    "so-mi": ["S", "M", "L", "XL"],
    "ao-khoac": ["S", "M", "L", "XL"],
    "quan": ["29", "30", "31", "32", "33"],
    "vay": ["XS", "S", "M", "L"],
}


def _load_base_products() -> list[dict]:
    """Loads the original 22 products from catalog_data.json."""
    if not DATA_JSON.is_file():
        return []
    with open(DATA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("products", [])


def _build_seed_products() -> tuple[list[dict], list[dict]]:
    """Builds complete list of products and size charts (original 22 + generated >= 150 total)."""
    base_products = _load_base_products()
    products_out = []
    charts_out = list(SIZE_CHARTS)
    known_chart_ids = {c["id"] for c in charts_out}

    # 1. Add base products
    for bp in base_products:
        p = dict(bp)
        cat_key = p.get("category", "ao-thun")
        p["category_id"] = f"cat-{cat_key}"
        p["is_new"] = 1 if p.get("isNew") else 0
        p["is_featured"] = 1 if p.get("isFeatured") else 0
        p["is_active"] = 1
        p["created_at"] = "2026-10-01T00:00:00Z"
        p["updated_at"] = "2026-10-12T00:00:00Z"
        p["details_json"] = json.dumps(p.get("details", []), ensure_ascii=False)

        # Handle size chart
        chart_data = p.get("chart")
        if chart_data and isinstance(chart_data, dict):
            chart_id = f"chart-{p['slug']}"
            p["size_chart_id"] = chart_id
            if chart_id not in known_chart_ids:
                known_chart_ids.add(chart_id)
                charts_out.append({
                    "id": chart_id,
                    "name": chart_data.get("name", f"Bảng size {p['name']}"),
                    "garment": chart_data.get("garment", "bottom" if cat_key in ("quan", "vay") else "top"),
                    "source": chart_data.get("source", "illustrative"),
                    "measurement_basis": chart_data.get("measurement_basis", "body_cm"),
                    "table_json": json.dumps({"rows": chart_data.get("rows", [])}, ensure_ascii=False),
                })
        else:
            p["size_chart_id"] = f"chart-{cat_key}"

        # Generate variants if missing
        if "variants" not in p:
            variants = []
            colors = p.get("colors") or [{"name": p.get("color", "Mặc định"), "hex": "#000000"}]
            sizes = p.get("sizes") or ["M"]
            for c_idx, c in enumerate(colors):
                c_name = c["name"] if isinstance(c, dict) else str(c)
                c_hex = c["hex"] if isinstance(c, dict) else "#000000"
                for s in sizes:
                    var_id = f"var-{p['slug']}-{c_idx}-{s.lower()}"
                    sku = f"SKU-{p['slug'].upper()}-{c_idx}-{s}"
                    variants.append({
                        "id": var_id,
                        "product_id": p["id"],
                        "sku": sku,
                        "color_name": c_name,
                        "color_hex": c_hex,
                        "size": s,
                        "stock": 15,
                        "is_active": 1,
                    })
            p["variants"] = variants

        # Ensure gallery and images: [main_photo, detail_photo]
        image_url = f"/products/{p['slug']}.jpg"
        gallery = [image_url, f"/products/{p['slug']}-detail.jpg"]
        p["image"] = image_url
        p["gallery"] = gallery
        p["images"] = [
            {
                "id": f"img-{p['slug']}-0",
                "product_id": p["id"],
                "url": gallery[0],
                "alt": f"{p['name']} - Mặt trước",
                "color_name": p.get("color"),
                "display_order": 0,
                "is_primary": 1,
            },
            {
                "id": f"img-{p['slug']}-1",
                "product_id": p["id"],
                "url": gallery[1],
                "alt": f"{p['name']} - Chi tiết chất liệu",
                "color_name": p.get("color"),
                "display_order": 1,
                "is_primary": 0,
            },
        ]

        products_out.append(p)

    # 2. Add expansion products
    for cat_slug, templates in EXPANSION_TEMPLATES.items():
        palettes = DEFAULT_PALETTES.get(cat_slug, DEFAULT_PALETTES["ao-thun"])
        sizes = DEFAULT_SIZES.get(cat_slug, DEFAULT_SIZES["ao-thun"])
        default_chart_id = f"chart-{cat_slug}"

        for idx, (name, slug, price, orig_price, subtitle, material, fit) in enumerate(templates):
            pid = slug
            # 2 to 3 colors per product
            prod_colors = [palettes[idx % len(palettes)], palettes[(idx + 1) % len(palettes)]]
            if idx % 3 == 0:
                prod_colors.append(palettes[(idx + 2) % len(palettes)])

            if slug in V2_MAP:
                image_url, detail_url = V2_MAP[slug]
                gallery = [image_url, detail_url]
            else:
                image_url = f"/products/{slug}.jpg"
                gallery = [image_url, f"/products/{slug}-detail.jpg"]

            details = [
                f"Chất liệu {material} cao cấp chuẩn xuất khẩu",
                f"Phom dáng {fit} tạo sự thoải mái tối ưu",
                "Đường may hoàn thiện thủ công tỉ mỉ chống bai dão",
                "Sản phẩm thiết kế độc quyền từ MORPH Studio",
            ]

            variants = []
            for c_idx, c in enumerate(prod_colors):
                for s in sizes:
                    var_id = f"var-{slug}-{c_idx}-{s.lower()}"
                    sku = f"SKU-{slug.upper()}-{c_idx}-{s}"
                    variants.append({
                        "id": var_id,
                        "product_id": pid,
                        "sku": sku,
                        "color_name": c["name"],
                        "color_hex": c["hex"],
                        "size": s,
                        "stock": 12,
                        "is_active": 1,
                    })

            images = [
                {
                    "id": f"img-{slug}-0",
                    "product_id": pid,
                    "url": gallery[0],
                    "alt": f"{name} - Mặt trước",
                    "color_name": prod_colors[0]["name"],
                    "display_order": 0,
                    "is_primary": 1,
                },
                {
                    "id": f"img-{slug}-1",
                    "product_id": pid,
                    "url": gallery[1],
                    "alt": f"{name} - Chi tiết chất liệu (phóng to)" if slug in V2_MAP else f"{name} - Chi tiết chất liệu",
                    "color_name": prod_colors[0]["name"],
                    "display_order": 1,
                    "is_primary": 0,
                },
            ]

            p = {
                "id": pid,
                "slug": slug,
                "name": name,
                "subtitle": subtitle,
                "category": cat_slug,
                "category_id": f"cat-{cat_slug}",
                "categoryName": next((c["name"] for c in CATEGORIES if c["slug"] == cat_slug), cat_slug),
                "price": price,
                "originalPrice": orig_price,
                "original_price": orig_price,
                "color": prod_colors[0]["name"],
                "colors": prod_colors,
                "sizes": sizes,
                "image": image_url,
                "gallery": gallery,
                "description": f"{name} với {subtitle.lower()}. Sản phẩm được MORPH tuyển chọn từ chất liệu {material.lower()}, hoàn thiện tỉ mỉ từng chi tiết cho tủ đồ hiện đại.",
                "material": material,
                "fit": fit,
                "details": details,
                "details_json": json.dumps(details, ensure_ascii=False),
                "size_chart_id": default_chart_id,
                "is_new": 1 if idx % 4 == 0 else 0,
                "is_featured": 1 if idx % 5 == 0 else 0,
                "isNew": True if idx % 4 == 0 else False,
                "isFeatured": True if idx % 5 == 0 else False,
                "is_active": 1,
                "created_at": f"2026-10-{(idx % 10) + 1:02d}T10:00:00Z",
                "updated_at": "2026-10-12T12:00:00Z",
                "variants": variants,
                "images": images,
            }
            products_out.append(p)

    return products_out, charts_out


PRODUCTS, SIZE_CHARTS = _build_seed_products()
