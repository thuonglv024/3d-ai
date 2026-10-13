# MORPH — luồng camera liên tục

Yêu cầu mới nhất, 12/10/2026: bỏ hình nộm trước scan và bỏ toàn bộ upload ảnh trên UI. Source chính vẫn là `D:\MORPH-AI\frontend` và `D:\MORPH-AI\backend`.

## Luồng đang dùng

1. Mở `/scan` hoặc **Tìm size của tôi** trong trang mua sắm `/`.
2. Nhập chiều cao, chọn khung webcam thân trên (mặc định), đồng ý xử lý khung hình.
3. **Mở camera & bắt đầu** → **Bắt đầu quét**.
4. AI nhận đúng góc và giữ yên → đếm ngược 5 giây → chụp chính diện.
5. Cùng camera tiếp tục mở; hiện hướng dẫn xoay 90° trong 4 giây. Khi AI nhận đúng góc nghiêng và giữ yên, tự đếm ngược 5 giây lần nữa.
6. Chụp góc nghiêng, dừng camera, tự gửi hai frame chụp tới backend và dựng kết quả. Không cần bấm xử lý riêng.

Nếu tư thế không phù hợp hoặc di chuyển, countdown bị hủy và chờ đúng tư thế. Ảnh trống không được chụp. Hủy phiên/đóng module dừng stream, timer và request; không gửi cặp ảnh chưa đủ. Camera chỉ được đổi trước khi bắt đầu; đổi camera làm mới phiên.

Camera-only mô tả **cách nhập dữ liệu**, không biến camera laptop thành cảm biến độ sâu. Engine vẫn dựng hình thể ước lượng từ hai ảnh tự chụp. Các giới hạn/nguồn số đo giữ như `UPPER_BODY_HANDOFF.md`. API multipart vẫn nhận hai ảnh vì đó là frame do camera chụp; UI không có file chooser hoặc drag/drop.

## Source

- `frontend/components/shop/CaptureSession.tsx`: state machine ready → running/front → turn → running/side → complete, một MediaStream, kiểm tra AI, countdown và cleanup.
- `frontend/components/shop/FitExperience.tsx`: chuẩn bị, consent, phiên camera, tự xử lý, kết quả. Không import/render sample viewer hoặc upload.
- `frontend/lib/useBodyScan.ts`: `scan({front,side})` nhận trực tiếp cặp vừa chụp để tránh đọc state cũ.
- `frontend/app/capture-flow.css`: bố cục mới; override kết quả mobile để toolbar và canvas nằm riêng.
- `frontend/components/shop/ScanResult.tsx`: giữ màn hình kết quả dark đã triển khai.
- `GuidedCamera.tsx`/`CameraCapture.tsx`: component cũ còn trong source nhưng không được route mới sử dụng. Không nối lại upload UI.

## Chạy và kiểm tra

Chạy `start-backend.ps1` và `start-frontend.ps1` trong hai terminal tại D:\MORPH-AI. Mở http://127.0.0.1:3000/scan. Python interpreter trong VS Code: `backend/.venv/Scripts/python.exe`.

Production build/TypeScript đã pass. `verification/scripts/camera-flow-ui.cjs` là browser harness hiện tại. Nó kiểm tra không có file input/canvas mẫu, một lần getUserMedia cho hai góc, blank rejection, countdown và tự chuyển 90°, tự reconstruct bằng backend thật, cleanup sau xong/hủy, responsive và module trong storefront. Kết quả: `output/playwright/camera-flow-20261012/results.json`.

Các ảnh người bên trong camera QA là **frame mannequin tổng hợp để giả lập webcam**, không phải hình nộm còn sót trong UI. Chưa kiểm chứng trên camera/người thật. Các harness upper-ui/commerce-ui là lịch sử trước khi bỏ upload.

Agent documenter phụ gặp giới hạn sử dụng trong phiên này; phần cập nhật tài liệu cuối được agent chính đối chiếu trực tiếp với source và ảnh kiểm thử. Review độc lập màn hình kết quả đã yêu cầu sửa toolbar mobile; sửa này được xác nhận bằng kiểm tra vị trí toolbar/canvas.

## Nâng cấp layout camera scan (13/10/2026)

Bố cục camera scan được tối ưu hóa toàn diện theo phong cách Warm Ivory & Champagne Gold:
1. **Ưu tiên camera tối đa**: Desktop sử dụng 2 cột (`grid-template-columns: minmax(0, 1fr) 300px`), video feed chiếm trọn cột bên trái; cột phải chứa tiến độ (01/02), hướng dẫn tư thế, trạng thái AI, mẹo nhận diện và nút bấm.
2. **Không che khuất đầu–vai–eo–cạp quần**: Loại bỏ banner hướng dẫn ở đáy video (`.capture-instruction` chuyển ra sidebar). Trong khung video chỉ hiển thị: khung định vị mảnh (`.capture-frame-mark`), badge góc chụp nhỏ góc trên trái (`.capture-view-pill`), số đếm ngược tròn to ở trung tâm (`.capture-count`) và màn chuyển góc 4 giây.
3. **Mở rộng camera (Workspace Expansion)**: Bổ sung nút mở rộng camera (`Maximize2`/`Minimize2`) trên thanh điều khiển. Cho phép mở rộng toàn viewport (`100vw`, `100dvh`). Hỗ trợ phím `Escape` để thu nhỏ lại mà không ngắt stream hay reset countdown. Tự động mở rộng modal dialog khi scan trong modal cửa hàng.
4. **Bảo toàn tỷ lệ gốc**: `object-fit: contain`, không stretch/crop. Tỉ lệ khung hình stream webcam được giữ nguyên.
5. **Kích thước thực tế đo kiểm (Playwright BoundingBox)**:
   - **1920×1080**: Video `1222px × 687px` (đạt mục tiêu 1100–1280px), stage `1224px × 689px`, sidebar `300px`. Toàn bộ hiển thị trong viewport không cần cuộn.
   - **1920×1080 (Expanded)**: Video `1560px × 979px`.
   - **1366×768 (Laptop)**: Video `960px × 540px`, stage `962px × 542px`, nút CTA trong tầm nhìn (`y=669px < 768px`).
   - **390×844 (Mobile)**: Video `336px × 218px`, `scrollWidth <= innerWidth` (không tràn ngang).
   - **360×800 (Mobile nhỏ)**: Video `306px × 218px`, không tràn ngang.
   - **Modal Storefront (1440×900)**: Video `1018px × 572px`; Modal expanded `1080px × 799px`.
6. **Harness kiểm thử**:
   - `verification/scripts/camera-layout-verification.cjs` kiểm tra bounding box, phím Escape, modal expand, countdown căn giữa và lưu bằng chứng vào `output/playwright/camera-layout-20261013`.
   - `verification/scripts/camera-flow-ui.cjs` chạy toàn bộ luồng camera regression: PASSED.

## Hoàn thiện tích hợp Commerce, Popups, Auth & Catalog Media (13/10/2026)

Đã giải quyết triệt để toàn bộ 27 vấn đề kiểm toán theo `POPUP_COMMERCE_FIX_PROMPT_2026-10-13.md` và `LIVE_AUDIT_FIX_PROMPT_2026-10-13.md`:
1. **Ảnh sản phẩm thời trang thật 100%**: Xóa bỏ hoàn toàn ảnh đa giác hoạt hình PIL. Toàn bộ 160 sản phẩm (320 ảnh primary và detail) là ảnh chụp studio/packshot thời trang thật với tỷ lệ 3:4 portrait, nền sáng/trung tính, ánh sáng mềm, đúng phân loại trang phục và màu sắc. 320 file ảnh đều có SHA-256 duy nhất (0 duplicate hash). Asset manifest tại `backend/scripts/catalog_asset_manifest.json` ghi nhận đầy đủ nguồn gốc, giấy phép (Unsplash/Burst/Commercial-Free) và trạng thái visual review.
2. **Sửa lỗi Popup chọn Camera**: Cô lập hoàn toàn selector CSS `.capture-session-head button` sang `.capture-expand-btn` và `.capture-close-btn`, ngăn chặn ghi đè style của `CustomSelect`. Dropdown camera được gán class `capture-device-select` căn lề phải với `z-index: 9999`, không bị cắt chữ hay vỡ khung hình.
3. **Bộ chọn sản phẩm Mobile (/scan)**: Đưa bottom sheet ra ngoài containing block có `backdrop-filter: blur(16px)` thông qua `createPortal(..., document.body)`. Popover bám sát đáy màn hình (`bottom: 0`), hiển thị đầy đủ trong viewport (không bị trôi `top: -412px`), có thanh kéo handle bar, nút đóng `X`, lớp phủ backdrop mờ, khóa cuộn trang (`body overflow: hidden`) và phím Escape phục hồi focus về trigger.
4. **Xác thực (Auth: Login & Register)**:
   - Hiển thị đồng thời thông báo đỏ `.auth-field-error` dưới từng trường bắt buộc khi submit rỗng.
   - Tự động cuộn và focus vào trường lỗi đầu tiên (`#login-email`, `#register-displayName`).
   - Thuộc tính A11y đầy đủ: `aria-invalid`, `aria-describedby` trỏ ID thẻ lỗi có `role="alert"`.
   - Bỏ `tabIndex={-1}` trên nút ẩn/hiện mật khẩu, hỗ trợ phím Tab và `:focus-visible` outline.
   - Thay đổi nội dung giới thiệu minh bạch, khách quan với engine AI MediaPipe; loại bỏ thuật ngữ kỹ thuật thừa.
   - Bảo toàn `returnTo`, giỏ hàng và intent lưu scan qua luồng đăng nhập/đăng ký.
5. **Wishlist → Giỏ hàng → Checkout → Đơn hàng**:
   - WishlistDrawer hỗ trợ Loading Skeleton shimmer, màn hình lỗi có nút "Thử lại", và thẻ "Tạm hết hàng / Không khả dụng" cho ID sản phẩm không còn tồn tại.
   - Cho phép chọn màu sắc, kích cỡ và số lượng từ các biến thể thực tế trong SQLite; bắt buộc người dùng chọn biến thể trước khi thêm giỏ.
   - Nút batch "Thêm vào giỏ hàng" và "Tiếp tục đặt hàng" bảo toàn các món có sẵn trong giỏ.
   - `app/cart/page.tsx` fetch động danh sách biến thể đầy đủ qua `/api/products/${slug}` cho cả 160 sản phẩm.
   - Sửa lỗi focus validation ở lần submit đầu tại `/checkout` bằng cách sử dụng `nextErrors` ngay lập tức.
   - Backend `backend/app/orders.py` kiểm tra và trừ tồn kho bằng transaction `BEGIN IMMEDIATE;`, hỗ trợ cả hai trường `note` và `notes`.
6. **Giao diện, Navbar & Animation**:
   - Navbar dạng thanh floating inset, bo góc 18–22px, viền Champagne Gold sang trọng, không tràn màn hình tablet 820px (`scrollWidth <= clientWidth`).
   - Card sản phẩm có hiệu ứng entrance animation `productCardEntrance` (fade + translateY 14px) với delay so le `--stagger-index * 35ms`, tự động tắt khi người dùng bật `prefers-reduced-motion: reduce`.
   - Hiển thị thẻ hướng dẫn lùi xa 2–2.5m chụp toàn thân ngay tại màn hình chuẩn bị quét khi chọn quần, chân váy hoặc đầm.
   - Đồng bộ dialog accessible primitive (`useDrawerA11y`, `role="dialog"` / `role="alertdialog"`, focus trap, scroll lock) cho các modal đối chiếu và xác nhận xóa scan.
7. **Kết quả kiểm thử thực tế**:
   - TypeScript typecheck frontend: **0 errors**.
   - Backend pytest test suite (`test_catalog_db.py`, `test_orders.py`, `test_auth_and_history.py`): **46 / 46 passed (100%)**.
   - Playwright test suites (`auth-a11y`, `commerce-audit-fix`, `popups-ui`, `camera-layout`, `lead-final-audit`): **100% passed**.


