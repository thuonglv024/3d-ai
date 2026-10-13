# MORPH — Bàn giao nâng cấp Camera Layout, Popup & Dropdown Toàn diện

Ngày hoàn thành: 13/10/2026.
Phạm vi: Cải tiến cấu trúc layout camera, chuẩn hóa toàn bộ hệ thống popup/modal/drawer sang dạng modal cân giữa (desktop) và bottom sheet (mobile), nâng cấp dropdown thông minh chống tràn mép, sửa lỗi cleanup và focus thrashing accessibility.

---

## 1. Tóm tắt các vấn đề đã khắc phục triệt để

1. **Sửa lỗi dọn dẹp (cleanup) và khoá cuộn trong `Modal.tsx`**:
   - *Nguyên nhân cũ*: Nhánh `open === true` trả về hàm cleanup sớm `() => clearTimeout(focusTimer)`, làm mất logic giải phóng `document.body.style.overflow`, giảm biến đếm `globalActiveModalCount` và khôi phục focus về nút kích hoạt.
   - *Khắc phục*: Chuẩn hóa toàn bộ cleanup vào một return duy nhất cuối `useEffect`. Khi modal đóng hoặc unmount, body scroll unlock lập tức và focus được trả về đúng trigger ref.

2. **Khắc phục focus thrashing trong `useDrawerA11y.ts`**:
   - *Nguyên nhân cũ*: `onClose` callback được truyền vào mảng phụ thuộc `[isOpen, panelRef, onClose]`. Mỗi render cha tạo function mới khiến effect chạy lại liên tục, tranh chấp khôi phục và giật focus.
   - *Khắc phục*: Lưu `onClose` qua `useRef` (`onCloseRef.current = onClose`) và lược bỏ khỏi dependencies `[isOpen, panelRef]`, loại bỏ hoàn toàn render thrashing.

3. **Loại bỏ drawer ép sát mép phải (`right: 0; height: 100%`)**:
   - *Hiện trạng cũ*: Wishlist và Bộ lọc trên desktop mở dưới dạng thanh dài áp sát lề phải, mất cân đối với bố cục storefront.
   - *Khắc phục*:
     - **Desktop (>= 768px)**: Chuyển thành modal cân giữa màn hình (`position: fixed; inset: 0; margin: auto; display: flex; align-items: center; justify-content: center`). Wishlist và Filter Panel có độ cao tự nhiên (`height: auto; max-height: 85vh`), bo góc 24px, đổ bóng mềm sang trọng.
     - **Mobile (< 768px)**: Tự động chuyển thành **Bottom Sheet** hiện đại (`position: fixed; bottom: 0; left: 0; right: 0; width: 100%`), bo góc trên `24px 24px 0 0`, trang bị thanh cầm tay `.sheet-handle-bar` hỗ trợ cảm ứng và hỗ trợ `padding-bottom: env(safe-area-inset-bottom)`.

4. **Dropdown thông minh chống tràn mép & Điều hướng phím**:
   - *Hiện trạng cũ*: Dropdown chỉ neo `top: 100%; left: 0`, khi ở sát mép dưới hoặc mép phải màn hình sẽ bị che khuất hoặc tạo thanh cuộn ngang trang.
   - *Khắc phục*:
     - Bổ sung logic đo tọa độ viewport thực tế (`getBoundingClientRect()`) trong `ProductFilter.tsx` và `ProductPickerPopover.tsx`.
     - Tự động lật lên trên (`.is-flipped-up`) khi không gian bên dưới < 260px.
     - Tự động căn lề phải (`.is-align-right`) khi dropdown vượt quá lề phải viewport.
     - Giới hạn chiều cao an toàn `max-height: min(280px, calc(100vh - ...))` với thanh cuộn mượt.
     - Tích hợp đầy đủ điều hướng phím: `ArrowDown`, `ArrowUp`, `Home`, `End`, `Enter`, `Escape`.

5. **Giải phóng không gian Camera Scan (`/scan` & FitExperience)**:
   - *Hiện trạng cũ*: Bị giới hạn cứng bởi `max-height: 52dvh` (tablet) và `48dvh` (mobile), cùng khoảng đệm quá lớn khiến khung nhìn người bị cắt xén phần eo và cạp quần.
   - *Khắc phục*:
     - Chuyển sang tính toán động theo viewport khả dụng:
       - Desktop: `min-height: 380px; max-height: calc(100dvh - 140px);`
       - Tablet: `min-height: 360px; max-height: min(68dvh, calc(100dvh - 180px));`
       - Mobile: `min-height: 280px; max-height: min(64dvh, calc(100dvh - 160px));`
     - Khi mở rộng (`.capture-session-expanded`): `max-height: calc(100dvh - 64px) !important; height: 100% !important;` trên mọi màn hình.
     - Tinh chỉnh padding container mobile thành `10px 8px 14px`, nâng độ rộng vùng hiển thị video lên >350px.
     - Tách biệt hoàn toàn sidebar hướng dẫn và video camera; không để bất kỳ banner hay controls nào che khuất trục thân người từ đầu đến cạp quần. Giữ nguyên stream webcam khi chuyển đổi giữa chế độ chuẩn và toàn màn hình.

---

## 2. Danh mục Source Code Đã Nâng Cấp

- `frontend/components/shop/Modal.tsx`: Sửa cleanup effect, lock/unlock body scroll tin cậy, autofocus phần tử đầu tiên và phục hồi focus về trigger ban đầu.
- `frontend/lib/useDrawerA11y.ts`: Ổn định callback qua `useRef`, ngăn focus thrashing khi render.
- `frontend/components/shop/WishlistDrawer.tsx`: Chuyển đổi markup sang `wishlist-modal-backdrop` & `wishlist-modal-panel`, thêm `.sheet-handle-bar`.
- `frontend/components/shop/ProductFilter.tsx`: Đo tọa độ bounding box, tự động gán `.is-flipped-up`, `.is-align-right`, hỗ trợ ARIA listbox và bàn phím.
- `frontend/components/shop/ProductPickerPopover.tsx`: Định vị an toàn cho popover chọn sản phẩm thử đồ.
- `frontend/app/commerce.css`: Định nghĩa hệ thống class modal cân giữa, bottom sheet mobile, animation `@keyframes sheetSlideUp`, `@keyframes dropdownFadeUp` và thanh touch handle `.sheet-handle-bar`.
- `frontend/app/capture-flow.css` & `scan-result.css`: Bỏ dvh cứng, áp dụng dynamic viewport bounds, tối ưu hóa kích thước video và stage.
- `verification/scripts/overlay-camera-verification.cjs`: Kịch bản kiểm thử tự động toàn diện với Playwright Headless Chrome trên 5 độ phân giải.

---

## 3. Kết Quả Kiểm Thử & Đo Lường Thực Tế (Playwright)

Tất cả **25/25 kịch bản kiểm thử tự động (100%)** đều vượt qua trên 5 kích thước màn hình chuẩn:
- **1920×1080 (Desktop lớn)**
- **1366×768 (Laptop phổ thông)**
- **768×1024 (Tablet / iPad)**
- **390×844 (Mobile chuẩn - iPhone 12/13/14)**
- **360×800 (Mobile nhỏ - Android gọn)**

Chi tiết trích xuất từ `output/playwright/overlay-camera/results.json`:

| STT | Kịch Bản Kiểm Thử | Kết Quả | Chi Tiết Đo Lường |
|:---:|:---|:---:|:---|
| 1 | Desktop Modal Cân Giữa Chiều Ngang | **PASSED** | Lệch biên độ: `0.0px` (Tuyệt đối chính giữa) |
| 2 | Desktop Modal Cân Giữa Chiều Dọc | **PASSED** | Vị trí Y: `186.3px`, Chiều cao: `707.3px` (Cân đối) |
| 3 | Khóa Cuộn Trang Khi Mở Modal | **PASSED** | `document.body.style.overflow = "hidden"` |
| 4 | Mở Khóa Cuộn Trang Khi Đóng Modal | **PASSED** | `document.body.style.overflow = ""` (Khôi phục hoàn toàn) |
| 5 | Khôi Phục Focus Về Nút Kích Hoạt | **PASSED** | Nút bấm kích hoạt nhận lại focus chính xác |
| 6 | Desktop Wishlist Hiển Thị Dạng Cân Giữa | **PASSED** | Không còn `right: 0`, Lệch biên: `0.0px`, Rộng: `548.8px` |
| 7 | Desktop Wishlist Chiều Cao Tự Nhiên | **PASSED** | Chiều cao: `478.8px` (< 100% màn hình) |
| 8 | Dropdown Neo Ngay Dưới Nút Bấm | **PASSED** | X: `750.9px`, Bám sát nút kích hoạt |
| 9 | Điều Hướng Phím Trong Dropdown | **PASSED** | Hỗ trợ ArrowDown/Up, Enter chọn option và tự đóng |
| 10 | Dropdown Sắp Xếp Nằm Trọn Viewport | **PASSED** | Mép phải: `1345.3px < 1920px` (Không tràn lề) |
| 11 | Popover Chọn Sản Phẩm Nằm Trọn Viewport | **PASSED** | Mép phải: `1202.8px < 1920px` (An toàn) |
| 12 | Chiều Cao Camera Desktop Rộng Rãi | **PASSED** | Đạt `689.4px` (Vượt xa mốc tối thiểu 380px) |
| 13 | Vùng Camera Không Bị Che Khuất | **PASSED** | Sidebar điều khiển tách riêng biệt |
| 14 | Bật Chế Độ Mở Rộng Camera | **PASSED** | Chuyển chế độ mượt mà, giữ nguyên MediaStream |
| 15 | Thu Nhỏ Camera Về Chuẩn | **PASSED** | Thu gọn về bố cục gốc an toàn |
| 16 | Camera Laptop 1366×768 Không Bị Cắt Xén | **PASSED** | Chiều cao đạt `542.4px`, nút CTA nằm trọn trong viewport |
| 17 | Camera Tablet 768×1024 Đủ Độ Cao | **PASSED** | Chiều cao đạt `397.2px` (Đã gỡ bỏ giới hạn 52dvh cũ) |
| 18 | Camera Tablet Chiếm Trọn Độ Rộng | **PASSED** | Độ rộng đạt `704.6px` |
| 19 | Mobile Bảng Size Dạng Bottom Sheet | **PASSED** | Chiếm trọn độ rộng `390px`, bám đáy `bottom: 0` |
| 20 | Mobile Wishlist Dạng Bottom Sheet | **PASSED** | Chiếm trọn độ rộng `390px`, bo góc trên `24px` |
| 21 | Mobile Wishlist Có Thanh Cầm Tay Cảm Ứng | **PASSED** | Hiển thị `.sheet-handle-bar` chuẩn UX di động |
| 22 | Mobile Bộ Lọc Dạng Bottom Sheet | **PASSED** | Chiếm trọn độ rộng `390px`, bám đáy màn hình |
| 23 | Chiều Cao Camera Mobile Đầy Đủ | **PASSED** | Chiều cao đạt `282.0px` (Đã gỡ bỏ giới hạn 48dvh cũ) |
| 24 | Độ Rộng Camera Mobile Tối Ưu | **PASSED** | Tăng độ rộng lên `350.2px` (Giảm padding thừa) |
| 25 | Camera Mobile Nhỏ (360×800) Đạt Chuẩn | **PASSED** | Chiều cao đạt `282.0px`, không tràn ngang |

Toàn bộ ảnh chụp kiểm thử đã được xuất lưu trữ tại:
`output/playwright/overlay-camera/`:
- `01-desktop-sizechart-centered.png`
- `02-desktop-wishlist-centered.png`
- `04-desktop-dropdowns.png`
- `05-desktop-scan-camera.png`
- `05-desktop-scan-camera-expanded.png`
- `06-laptop-scan-camera.png`
- `07-tablet-scan-camera.png`
- `08-mobile-sizechart-bottomsheet.png`
- `09-mobile-wishlist-bottomsheet.png`
- `10-mobile-filter-bottomsheet.png`
- `11-mobile-scan-camera.png`
- `12-mobile-compact-scan.png`

---

## 4. Xác Minh Toàn Hệ Thống

- **Frontend Next.js Build**: Chạy lệnh `npm --prefix frontend run build` đạt kết quả **0 lỗi** trên toàn bộ 8 routes.
- **Backend Tests**: Chạy lệnh `backend/.venv/Scripts/python.exe -m pytest backend/tests` đạt **59/59 tests PASSED**.
- **Quy tắc bảo toàn**:
  - Route `/cart` được giữ nguyên là trang độc lập đầy đủ, không bị biến thành popup hay drawer.
  - Không có bất kỳ thành phần upload file ảnh hoặc hình nộm nào được đưa lại vào quy trình scan.
  - Catalog SQLite với 160 sản phẩm, cơ chế chống giả mạo giá tiền và luồng checkout tiếp tục hoạt động ổn định.
