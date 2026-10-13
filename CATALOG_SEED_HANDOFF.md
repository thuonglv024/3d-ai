# CATALOG SEED HANDOFF — MORPH STUDIO

## 1. Tổng quan nâng cấp

Đã hoàn thành toàn diện việc nâng cấp catalog của MORPH Studio tại `D:\MORPH-AI` từ danh mục tĩnh 22 sản phẩm thành kho hàng thời trang chuyên nghiệp với **160 sản phẩm** lưu trữ trực tiếp trong SQLite (`.runtime/orders.db`). Hệ thống hoạt động đồng bộ xuyên suốt từ **Backend API → SQLite → Frontend Storefront → Giỏ hàng → Checkout → Xác nhận đơn hàng → Gợi ý size 3D**.

### Các chỉ số chính:
- **Tổng số sản phẩm**: 160 sản phẩm (mục tiêu tối thiểu 150).
- **Phân bổ danh mục**:
  - Áo thun (`ao-thun`): 32 sản phẩm
  - Sơ mi (`so-mi`): 32 sản phẩm
  - Áo khoác (`ao-khoac`): 32 sản phẩm
  - Quần (`quan`): 32 sản phẩm
  - Váy/Đầm (`vay`): 32 sản phẩm
- **Tổng số biến thể (Variants)**: 1,671 biến thể (kết hợp màu sắc thực tế × kích thước theo bảng size × tồn kho demo từ 8–35 cái).
- **Tổng số ảnh sản phẩm**: 321 ảnh thời trang chất lượng cao (ảnh nội bộ và Unsplash thời trang chuyên nghiệp với tỉ lệ ~4:5, chi tiết trang phục, không dùng ảnh chân dung cận mặt cho áo).
- **Bảng size (Size Charts)**: 27 bảng size chi tiết bằng số đo cơ thể cm (áo/khoác: ngực/eo; quần: eo/mông; váy/đầm: ngực/eo/mông).
- **Bảo toàn dữ liệu cũ**: Giữ nguyên 22 sản phẩm ban đầu với đầy đủ slug và ID (`ao-thun-essential`, `so-mi-oxford-classic`,...), bảo toàn 100% các đơn hàng đã tạo trước đó trong database mà không xóa/reset bảng.

---

## 2. Kiến trúc cơ sở dữ liệu SQLite (`.runtime/orders.db`)

Cơ sở dữ liệu được quản lý qua migration được đánh phiên bản tại [backend/app/db.py](file:///D:/MORPH-AI/backend/app/db.py):

### Các bảng dữ liệu:
1. `schema_migrations`: Lưu phiên bản migration (`version`, `name`, `applied_at`).
2. `categories`: Quản lý 5 nhóm danh mục (`id`, `slug`, `name`, `description`, `display_order`).
3. `size_charts`: Bảng size chuẩn hóa (`id`, `name`, `garment`, `source`, `measurement_basis`, `table_json`).
4. `products`: Thông tin sản phẩm (`id`, `slug`, `name`, `subtitle`, `category_id`, `price`, `original_price`, `description`, `material`, `fit`, `details_json`, `size_chart_id`, `is_new`, `is_featured`, `is_active`, `created_at`, `updated_at`).
5. `product_variants`: Biến thể SKU (`id`, `product_id`, `sku`, `color_name`, `color_hex`, `size`, `stock`, `is_active`).
6. `product_images`: Hình ảnh sản phẩm (`id`, `product_id`, `url`, `alt`, `color_name`, `display_order`, `is_primary`).
7. `orders` & `order_items`: Lưu đơn hàng checkout với snapshot giá thật từ SQLite.

Các chỉ mục (`INDEX`) tối ưu hóa truy vấn:
- `idx_products_category_id`, `idx_products_slug`, `idx_products_is_active`
- `idx_product_variants_product_id`, `idx_product_variants_sku`
- `idx_product_images_product_id`

---

## 3. Seed dữ liệu Idempotent

Script seeder tại [backend/app/seed.py](file:///D:/MORPH-AI/backend/app/seed.py) nạp dữ liệu từ [backend/app/catalog_seed_data.py](file:///D:/MORPH-AI/backend/app/catalog_seed_data.py).

- Cơ chế `ON CONFLICT DO UPDATE` đảm bảo an toàn tuyệt đối khi chạy lại nhiều lần (idempotent), không gây trùng lặp bản ghi hay vi phạm khóa unique/foreign key.
- Lệnh chạy:
  ```powershell
  $env:PATHEXT = '.COM;.EXE;.BAT;.CMD'; & backend/.venv/Scripts/python.exe backend/app/seed.py
  # Kết quả: Seeded 5 categories, 27 size charts, 160 products, 1671 variants, 321 images.
  ```

---

## 4. Backend API & Chống gian lận giá

Tập tin [backend/app/catalog.py](file:///D:/MORPH-AI/backend/app/catalog.py) và [backend/app/orders.py](file:///D:/MORPH-AI/backend/app/orders.py) đã được chuyển đổi hoàn toàn sang SQLite:

### Endpoints Catalog:
- `GET /api/products`:
  - Tham số: `page`, `limit` (mặc định 24 sp/trang), `category`, `search`, `sort` (`featured`, `price_asc`, `price_desc`, `name_asc`, `newest`), `min_price`, `max_price`, `color`, `size`.
  - Khi có tham số `page` hoặc `limit`: Trả về đối tượng phân trang `{ items, total, page, page_size, total_pages }`.
  - Khi không truyền tham số phân trang: Trả về `list[dict]` để tương thích 100% với các test cũ.
- `GET /api/products/{slug}`: Lấy chi tiết sản phẩm kèm variants, gallery, và size chart.
- `GET /api/products/categories` & `GET /api/categories`: Danh sách danh mục kèm số lượng sản phẩm kích hoạt (`product_count`).

### Bảo mật báo giá và Đơn hàng:
- `POST /api/orders/quote` và `POST /api/orders`:
  - `validate_cart_item()` truy vấn trực tiếp bảng `products` và `product_variants` trong SQLite để lấy giá bán niêm yết chính xác (`unit_price_vnd`).
  - Toàn bộ giá bán hay tổng tiền mà client gửi lên đều bị bỏ qua (overridden), triệt tiêu hoàn toàn nguy cơ can thiệp giá từ client.

---

## 5. Nâng cấp Frontend UI & Trải nghiệm mua sắm

1. **Client API ([frontend/lib/catalogApi.ts](file:///D:/MORPH-AI/frontend/lib/catalogApi.ts))**:
   - `fetchProducts(options)` hỗ trợ phân trang 24 sp/trang, bộ lọc danh mục, tìm kiếm, khoảng giá, màu sắc và kích thước.
   - Cơ chế fallback linh hoạt trong môi trường offline/SSR.
2. **Storefront ([frontend/components/shop/StorefrontHome.tsx](file:///D:/MORPH-AI/frontend/components/shop/StorefrontHome.tsx))**:
   - Hiển thị 24 sản phẩm mỗi trang với bộ điều khiển phân trang chuyên nghiệp (`PaginationControls`): Nút Trước, các số trang (kèm dấu `...` khi nhiều trang), Nút Sau.
   - Dòng thông tin trạng thái: `Hiển thị 1 – 24 trong 160 sản phẩm`.
   - Đồng bộ trạng thái URL query string (`?page=...&category=...&sort=...`).
   - Hiệu ứng chuyển trang mượt mà kèm skeleton loading (`ProductGridSkeleton`) chuẩn tông màu Warm Ivory & Champagne Gold.
3. **Chi tiết sản phẩm ([frontend/components/shop/ProductDetail.tsx](file:///D:/MORPH-AI/frontend/components/shop/ProductDetail.tsx))**:
   - Đọc dữ liệu động theo `slug`, hiển thị trạng thái tồn kho (`Còn hàng · Sẵn sàng đóng gói và giao hàng`), chọn màu, chọn size, mở bảng size chuẩn và phòng scan 3D.
4. **Bộ chọn sản phẩm tìm kiếm tại trang Scan ([frontend/components/shop/ProductPickerPopover.tsx](file:///D:/MORPH-AI/frontend/components/shop/ProductPickerPopover.tsx))**:
   - Thay thế thẻ `<select>` cũ bằng popover tra cứu 160 sản phẩm:
     - Ô tìm kiếm nhanh theo tên và chất liệu.
     - Các tab danh mục (`Tất cả`, `Áo thun`, `Sơ mi`, `Áo khoác`, `Quần`, `Váy`) kèm số lượng.
     - Danh sách cuộn mượt mà có ảnh thumbnail và giá niêm yết.

---

## 6. Kết quả Kiểm thử & Nghiệm thu

### 1. Pytest Backend:
- Đã chạy: `backend/.venv/Scripts/python.exe -m pytest backend/tests`
- **Kết quả**: **59/59 passed (100%)** trong 13.63s:
  - 51 unit/integration test hiện có (scan, images, sizing, upper-body, orders).
  - 8 catalog database test mới tại [backend/tests/test_catalog_db.py](file:///D:/MORPH-AI/backend/tests/test_catalog_db.py) kiểm thử migrations, seed idempotency, phân trang, lọc danh mục, sắp xếp giá, và chống giả mạo giá client.

### 2. TypeScript & Next.js Build:
- Đã chạy: `npm run build` tại `frontend/`
- **Kết quả**: **29/29 routes compiled successfully**, 0 TypeScript error, 0 lint error.

### 3. Playwright End-to-End Verification ([verification/scripts/catalog-e2e-verification.cjs](file:///D:/MORPH-AI/verification/scripts/catalog-e2e-verification.cjs)):
- **Kết quả**: **14/14 bước kiểm thử đạt 100% (PASS)**:
  1. Backend categories count (5/5 categories) — **PASS**
  2. Backend total products >= 150 (160 items) — **PASS**
  3. Backend page size is 24 (24 items/page) — **PASS**
  4. Backend total pages >= 7 (7 pages) — **PASS**
  5. Storefront initial card count (24 cards rendered) — **PASS**
  6. Pagination controls exist — **PASS**
  7. Pagination status text ("Hiển thị 1 – 24 trong 160 sản phẩm") — **PASS**
  8. Navigation to Page 2 & URL sync (`?page=2#catalog`) — **PASS**
  9. Category filter URL sync (`?category=so-mi#catalog`) — **PASS**
  10. Product detail title rendering — **PASS**
  11. In-stock badge displayed ("Còn hàng") — **PASS**
  12. Add to cart & checkout order creation with real SQLite price — **PASS**
  13. Searchable product picker popover opened in `/scan` — **PASS**
  14. Picker search filter functioning with matching results — **PASS**

Ảnh chụp màn hình kiểm thử được lưu trữ tại `output/playwright/catalog-upgrade/`:
- `01_storefront_page1.png`
- `02_storefront_page2.png`
- `03_category_so_mi.png`
- `04_product_detail.png`
- `05_cart_drawer.png`
- `06_checkout_form.png`
- `07_order_success.png`
- `08_scan_product_picker.png`
