# Trạng Thái Bàn Giao Hiện Tại (Project Handoff)

Tài liệu này tổng hợp trạng thái hiện tại của dự án **MORPH AI**, các thay đổi vừa hoàn thành, các giới hạn kỹ thuật cần lưu ý và danh sách công việc tiếp theo dành cho kỹ sư hoặc AI Agent kế nhiệm.

---

## 1. Trạng thái hệ thống hiện tại

### 1.1. Các phân hệ đã hoàn thiện và hoạt động ổn định
1. **Storefront & Catalog 160 sản phẩm**:
   - Đầy đủ 160 sản phẩm thời trang (80 Nam / 80 Nữ, chia đều 10 danh mục $\times$ 8 sản phẩm), có biến thể màu sắc, tồn kho theo size và bảng thông số `size_chart` riêng.
   - Giao diện Luxury Editorial (**Warm Ivory & Champagne Gold**) trên cửa hàng, kết hợp **Dark Measurement Workspace** (`#141312`) cho khu vực quét 3D và phân tích số đo.
2. **Luồng Quét 3D Camera-Only & Tự động chụp 2 góc**:
   - Chỉ sử dụng Webcam trực tiếp (không có nút tải ảnh tĩnh, không hiển thị mannequin mẫu trước khi quét).
   - Mặc định ở chế độ **Quét Thân Trên (`upper_body`)** phù hợp góc webcam laptop/PC; hỗ trợ chuyển sang **Quét Toàn Thân (`full_body`)**.
   - Tự động nhận diện tư thế qua MediaPipe, hướng dẫn căn khung trực tiếp trên video và đếm ngược chụp góc Chính diện $\rightarrow$ Nghiêng 90°.
3. **Pipeline Tối ưu hóa 3D Body Scan 3 Tầng (Vừa triển khai)**:
   - **Tầng 1 ([`backend/app/reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py) — `estimate_upper_body_height`)**: Kết hợp đa mỏ neo Đỉnh đầu $\rightarrow$ Vai (`0.195 H`) và Vai $\rightarrow$ Hông (`0.290 H`) bằng hàm Huber/Tanh giới hạn biên độ, giảm sai số `obs.height` từ $\pm 10.34\%$ xuống $\le \pm 1.20\%$.
   - **Tầng 2 ([`backend/app/camera_fusion.py`](file:///d:/MORPH-AI/backend/app/camera_fusion.py) & [`backend/app/reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py))**: Đồng bộ mốc giải phẫu `aligned_torso_landmarks` và dùng chung chiều cao tham chiếu `fuse_camera_scale` giữa 2 góc chụp, triệt tiêu hoàn toàn hiện tượng méo tỷ lệ $D/W$ (`0.00%` sai lệch) khi mốc hông góc nghiêng 90° bị trôi.
   - **Tầng 3 ([`backend/app/measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py))**: Bù trừ độ lõm giải phẫu mặt cắt ngang (`ANATOMICAL_SECTION_FACTORS`: Ngực $+8.07\%$, Eo $+3.21\%$, Hông $+6.23\%$) và khớp lưới PCHIP 4 vòng bảo toàn đồng thời chu vi (`0.00 cm` sai số khớp lưới) lẫn tỷ lệ $D/W$, với thời gian xử lý lõi chỉ `~9.67 ms` (`< 15 ms`).
4. **Minh bạch nguồn số đo & Gợi ý kích cỡ**:
   - Phân biệt rõ 5 nguồn `source`: `photo_estimate`, `photo_with_prior`, `template_model`, `user_input`, `unavailable`.
   - Trong chế độ `upper_body`, số đo phần dưới (`hip_cm`, `inseam_cm`, `thigh_cm`, `calf_cm`) không được ước lượng từ ảnh; hệ thống gắn nhãn `template_model` hoặc `unavailable` và cho phép người dùng nhập tay vào **Hồ sơ số đo (`BodyProfile`)** để tính size quần/váy chính xác.
5. **Xác thực, Lịch sử Hình thể & Đặt hàng nguyên tử**:
   - Xác thực qua session token ngẫu nhiên 256-bit lưu trong cookie `morph_session` (`HttpOnly`, `SameSite=Lax`, băm `SHA-256` trong DB), có khóa tạm thời 5 phút khi đăng nhập sai quá 5 lần.
   - Biểu đồ tiến trình số đo [`BodyChart.tsx`](file:///d:/MORPH-AI/frontend/components/shop/BodyChart.tsx) hỗ trợ trục thời gian tuyến tính, gom cụm điểm gần nhau (`< 16px`) và ngắt đoạn (`broken path`) với các chỉ số không hợp lệ để theo dõi (`valid_for_tracking === false`).
   - Đặt hàng [`POST /api/orders`](file:///d:/MORPH-AI/backend/app/orders.py) trừ kho nguyên tử (`BEGIN IMMEDIATE;`), hỗ trợ `Idempotency-Key` chống trùng đơn và bảo vệ trang chi tiết đơn khách bằng `order_token`.

---

## 2. Các lỗi & nâng cấp Product Readiness vừa hoàn thành (Đã kiểm thử 100%)

Xem báo cáo nghiệm thu đầy đủ tại [**`SCAN_PRODUCT_READINESS.md`**](file:///d:/MORPH-AI/SCAN_PRODUCT_READINESS.md):

1. **Vá lỗ hổng bỏ qua `guest_token` & chống rò rỉ token ([`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py), [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py))**:
   - Bắt buộc mọi request tới phiên quét khách (`GET /api/scans/{id}`, `/measurements`, `/model`, `/size-advice`, `POST /api/sizing/recommend`, `DELETE /api/scans/{id}`) phải cung cấp `guest_token` hợp lệ (so khớp qua `secrets.compare_digest`), nếu thiếu hoặc sai đều trả về `403 Forbidden`.
   - Khi người dùng đăng nhập và nhận (claim) phiên quét qua `POST /api/user/scans/save`, gán `job.user_id` và xóa `job.guest_token = None`, ẩn `guest_token` trong response của user.
2. **Loại bỏ `template_model` / `unavailable` khỏi luồng gợi ý size từ DB ([`backend/app/sizing.py`](file:///d:/MORPH-AI/backend/app/sizing.py), [`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py), [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py))**:
   - Bổ sung `VALID_SIZING_SOURCES = {"photo_estimate", "photo_with_prior", "user_input"}` và `filter_valid_sizing_measurements()`.
   - Đảm bảo scan `upper_body` đã lưu trong SQLite (có `hip_cm` mang `source = "template_model"`) trả về `status = "insufficient_measurements"` (`missing = ["hip_cm"]`) đối với sản phẩm quần/chân váy hoặc đầm cần vòng mông, nhất quán 100% với khi job còn trong RAM.
   - Lọc bỏ `template_model` khỏi `key_measurements` trong `GET /api/user/scans` và giữ `null` là thiếu dữ liệu (không biến thành `0`, không đưa vào `BodyChart`).
3. **Kiểm soát chất lượng đầu vào Camera, Chọn Best-Frame & Bảo toàn Hình học ([`frontend/lib/captureQuality.ts`](file:///d:/MORPH-AI/frontend/lib/captureQuality.ts), [`CaptureSession.tsx`](file:///d:/MORPH-AI/frontend/components/shop/CaptureSession.tsx), [`FitExperience.tsx`](file:///d:/MORPH-AI/frontend/components/shop/FitExperience.tsx))**:
   - Kiểm tra độ sáng (`45..235`), độ nét Laplacian (`>= 14.0`), độ đứng yên đa khung hình (`motion < 0.018`), và độ lệch tỷ lệ khoảng cách đứng giữa 2 góc (`<= 18%`).
   - Lưu `candidateBuffer` trong `1600ms` cuối của đếm ngược và chọn frame có `frameQualityScore` cao nhất thay vì lấy ngẫu nhiên 1 frame tại `t = 0`.
   - Hủy đếm ngược tức thì khi mất điều kiện kèm lý do tiếng Việt cụ thể; bảo toàn tỷ lệ khung hình (`aspectRatioDelta < 0.002`).
4. **Chuẩn hóa Provenance từng Metric & Kiểm định lưới `.glb` ([`backend/app/report.py`](file:///d:/MORPH-AI/backend/app/report.py), [`backend/app/measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py))**:
   - Bổ sung `observed_region`, `valid_for_sizing`, `valid_for_tracking`, `quality_warnings`, `engine_version`, `uncertainty_cm: None` trên từng chỉ số.
   - Bổ sung `validate_glb_mesh()` kiểm tra đơn vị mét, chiều cao, trục tọa độ, không có đỉnh `NaN/Inf` hay mặt suy biến, và vị trí các vòng đo trước khi xuất `.glb`.
5. **Quản lý vòng đời Job, Chống hiển thị kết quả cũ khi lỗi API & Đồng bộ thông điệp Quyền riêng tư**:
   - Bổ sung `JOB_PROCESSING_TIMEOUT_SECONDS = 120` và `MAX_STORED_JOBS = 50` trong `main.py`.
   - Xóa `job` cũ ngay trước khi gửi `POST /api/scans` mới trong `useBodyScan.ts`.
   - Cập nhật thông điệp tại `/auth/login`, `/auth/register` và `FitExperience.tsx` trung thực với kiến trúc xử lý ảnh tại backend.
6. **Khắc phục lỗi Wishlist cộng đôi số lượng & phím `Escape` trong `CustomSelect` ([`WishlistDrawer.tsx`](file:///d:/MORPH-AI/frontend/components/shop/WishlistDrawer.tsx), [`CustomSelect.tsx`](file:///d:/MORPH-AI/frontend/components/shop/CustomSelect.tsx), [`useDrawerA11y.ts`](file:///d:/MORPH-AI/frontend/lib/useDrawerA11y.ts))**.

---

## 3. Tài liệu & Bộ Harness Kiểm Định Mới

- [**`SCAN_PRODUCT_READINESS.md`**](file:///d:/MORPH-AI/SCAN_PRODUCT_READINESS.md): Báo cáo nghiệm thu kỹ thuật, baseline vs after, độ nhạy, latency P50/P95 và điều kiện mở Pilot.
- [**`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`**](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md): Quy trình lấy số đo chuẩn bằng thước dây (ISO 8559-1:2017), chia tập `calibration_split` / `evaluation_split` độc lập theo `subject_id` và tiêu chuẩn nghiệm thu Pilot.
- [**`verification/scripts/benchmark_scan_product_readiness.py`**](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py) & [**`verification/scripts/test_capture_quality.cjs`**](file:///d:/MORPH-AI/verification/scripts/test_capture_quality.cjs).

---

## 4. Giới hạn kỹ thuật & Ranh giới trung thực (Không được tuyên bố sai)

1. **Không phải SAM 3D Body / MHR hay quét laser LiDAR**:
   - Mô hình 3D `.glb` là lưới cơ thể chuẩn MakeHuman được biến dạng mượt theo biên dạng 2D từ MediaPipe và khớp số đo 3 vòng bằng nội suy PCHIP.
   - Khuôn mặt, tóc và chi tiết bàn tay/bàn chân là của lưới mẫu, không tái tạo diện mạo cá nhân.
2. **Chưa có kiểm chứng lâm sàng trên tập người thật đa dạng**:
   - Dù sai số toán học nội bộ của thuật toán biến dạng và khớp lưới đã giảm về `0.00 cm`, độ chính xác ngoài đời thực vẫn phụ thuộc vào quần áo bó/rộng, khoảng cách đứng và ánh sáng webcam.
3. ** Lưu trữ phiên quét trong RAM**:
   - Dict `jobs` trong [`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py) lưu trạng thái tiến trình quét trong bộ nhớ RAM (tối đa 50 job gần nhất); các phiên quét đã được người dùng đăng nhập bấm lưu (`POST /api/user/scans/save`) mới được ghi bền vững vào bảng `body_scans` trong SQLite.

---

## 5. Công việc đề xuất tiếp theo (Next Steps)

1. **Thực nghiệm đối chiếu số đo thực tế (Real-Human Tape Validation)**:
   - Xây dựng tập dữ liệu kiểm thử gồm 10–20 tình nguyện viên có số đo thước dây thực tế (Ngực, Eo, Hông, Vai) chụp qua webcam ở khoảng cách 1.5–2.5m để tinh chỉnh thêm hệ số `ANATOMICAL_SECTION_FACTORS` và bù trừ độ dày trang phục.
2. **Tăng cường bảo mật Production cho Auth & Order**:
   - Khi triển khai lên môi trường HTTPS thực tế, bật biến môi trường `MORPH_COOKIE_SECURE=1` cho cookie `morph_session`.
   - Cân nhắc lưu trạng thái rate-limit đăng nhập vào SQLite/Redis thay vì dict in-memory nếu chạy đa tiến trình (`workers > 1`).
3. **Bền vững hóa trạng thái Scan Job**:
   - Nếu cần giữ kết quả quét khách qua các lần khởi động lại backend server, đồng bộ metadata của `jobs` vào một bảng tạm trong SQLite kèm cơ chế dọn dẹp theo TTL.
