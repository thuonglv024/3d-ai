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

## 2. Trạng thái Nghiệm thu Nâng cấp Scan (`run-20261014-v2`)

Xem báo cáo nghiệm thu chi tiết tại [**`SCAN_PRODUCT_READINESS.md`**](file:///d:/MORPH-AI/SCAN_PRODUCT_READINESS.md) và thư mục bằng chứng [`output/runs/run-20261014-v2/`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/):

- **Phân loại rõ 4 trạng thái nghiệm thu**:
  1. **Implementation & Security Verification**: **PASSED** (`pytest` Backend `N = 107` tests; Unit Quality `N = 16` checks; Browser E2E `CaptureSession` `N = 8` kịch bản DOM/Network trên Chromium; TypeScript `0` lỗi).
  2. **Synthetic / Geometric Validation**: **PASSED (Trong phạm vi Hình học Tổng hợp)** (`N_cal = 12` subjects / `36` scans, `N_eval = 10` held-out subjects / `30` scans, LOSO-CV `N = 13` archetypes, `N = 10` kịch bản nhiễu/từ chối, `N = 160` sản phẩm catalog).
  3. **API Lifecycle & Bounded Concurrent Load Test**: **EXECUTED (Trong phạm vi Local Single-Worker CPU)** (Tách riêng In-Process `reconstruct()` Cold/Warm start với Full HTTP Lifecycle + Browser WebGL Render; chạy tải đồng thời `Concurrency = 1, 2, 4, 10` với `MAX_ACTIVE_JOBS = 8`; đo tách biệt `OS Working Set RSS` `279–309 MB` với `Python Heap tracemalloc` `71–93 MB`).
  4. **Real-Human Anthropometric Accuracy**: **CHƯA XÁC NHẬN / CHƯA NGHIỆM THU (`MISSING_EMPIRICAL_COHORT`, `N_human = 0`)** — Chỉ được kết luận Product-Ready về độ chính xác nhân trắc học sau khi có tập dữ liệu người thật có đồng ý sử dụng vượt qua các cổng mục tiêu tại [`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md).

### Các hạng mục kỹ thuật đã hoàn tất:
1. **Bảo vệ `guest_token` & chống rò rỉ token ([`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py), [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py))**:
   - Bắt buộc đối chiếu `guest_token` qua `secrets.compare_digest` trên 6 endpoints phiên khách (`403 Forbidden` khi thiếu/sai token); xóa `job.guest_token = None` sau khi user claim scan (`POST /api/user/scans/save`).
2. **Lọc nguồn `VALID_SIZING_SOURCES` đồng bộ giữa RAM và SQLite ([`backend/app/sizing.py`](file:///d:/MORPH-AI/backend/app/sizing.py), [`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py), [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py))**:
   - Loại bỏ `template_model` và `unavailable` khi đọc từ `body_measurements`, đảm bảo scan `upper_body` luôn trả về `insufficient_measurements` (`missing = ["hip_cm"]`) cho `78/160` sản phẩm quần/chân váy cần vòng mông.
3. **Kiểm soát chất lượng Camera, Chọn Best-Frame & Kiểm thử Hành vi Trình duyệt ([`frontend/lib/captureQuality.ts`](file:///d:/MORPH-AI/frontend/lib/captureQuality.ts), [`CaptureSession.tsx`](file:///d:/MORPH-AI/frontend/components/shop/CaptureSession.tsx), [`test_capture_session_e2e.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_session_e2e.cjs))**:
   - Kiểm chứng thực tế trên trình duyệt Chromium (`8/8` kịch bản): hủy đếm ngược khi mất điều kiện, chọn đúng frame có `frameQualityScore` cao nhất trong cửa sổ `1600ms` (kiểm tra bằng giải mã pixel JPEG từ `POST /api/scans`), chuyển `front → turn → side`, chặn lệch khoảng cách đứng `> 18%`, đổi thiết bị camera, mất kết nối giữa chừng (`onended`), đóng phiên và retry (`0` track bị rò rỉ).
4. **Chuẩn hóa Provenance từng Metric & Kiểm định lưới `.glb` ([`backend/app/report.py`](file:///d:/MORPH-AI/backend/app/report.py), [`backend/app/measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py))**:
   - Bổ sung `observed_region`, `valid_for_sizing`, `valid_for_tracking`, `quality_warnings`, `engine_version`, `uncertainty_cm: None` và hàm `validate_glb_mesh()`.
5. **Quản lý Hàng đợi (`MAX_ACTIVE_JOBS = 8`), Timeout (`120s`), TTL (`MAX_STORED_JOBS = 50`) & Sửa lỗi Wishlist/Escape**.

---

## 3. Tài liệu & Bộ Harness Kiểm Định Hiện Có

- [**`SCAN_PRODUCT_READINESS.md`**](file:///d:/MORPH-AI/SCAN_PRODUCT_READINESS.md): Báo cáo nghiệm thu tổng hợp, ma trận trạng thái, kết quả E2E/Load/Validation và các cổng gating trước khi mở Pilot.
- [**`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`**](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md): Đối chiếu vị trí đo ISO 7250-1:2017 / ISO 8559-1:2017 với mốc MediaPipe (bao gồm độ chệch mốc vai `11–12` so với *Acromion*), các ngưỡng mục tiêu đề xuất cho Pilot (*Proposed Pilot Target Thresholds*), và phương pháp hiệu chuẩn khoảng dự đoán **Split Conformal Prediction / Empirical Residual Quantiles**.
- **Bộ script kiểm định trong `verification/scripts/`**:
  - [`test_capture_session_e2e.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_session_e2e.cjs) (Browser E2E cho `CaptureSession`)
  - [`test_capture_quality.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_quality.cjs) (Unit test logic chất lượng khung hình & hình học)
  - [`benchmark_scan_api_and_load.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_api_and_load.py) (Benchmark tách biệt `reconstruct()`, toàn trình API, WebGL render, tải đồng thời & bộ nhớ RSS/Heap)
  - [`evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py) & [`benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py) (Harness kiểm định nhân trắc học & khoảng dự đoán Split Conformal).

---

## 4. Giới hạn kỹ thuật còn lại (Không được tuyên bố vượt phạm vi)

1. **Chưa có tập dữ liệu kiểm định trên người thật (`N_human = 0`)**: Độ chính xác nhân trắc học trên cơ thể người thật chưa được xác nhận; `uncertainty_cm` giữ giá trị `None`.
2. **Chưa kiểm chứng tự động trên phần cứng camera vật lý đa thiết bị**: Bài test trình duyệt dùng `canvas.captureStream(30)` xác định; các yếu tố ISP auto-exposure, rolling shutter blur trong phòng tối, méo quang học góc rộng và lỗi driver USB/OS cần kiểm thử thực địa.
3. **Độ chệch mốc vai MediaPipe `11–12` vs *Acromion* (`~2.4–4.4 cm`), độ nhạy trang phục rộng (`+8.7..+9.1 cm` khi phình `+6 px`), và độ nhạy chiều cao tự nhập (`±2.2..±3.0 cm` khi lệch `±5 cm`)**.
4. **Kiến trúc `ThreadPoolExecutor(max_workers=1)` & in-memory `jobs`**: Dưới tải đồng thời `C >= 4`, thời gian chờ hàng đợi `queue_wait_ms P95` tăng lên `12.39s – 20.90s`; vượt quá `MAX_ACTIVE_JOBS = 8` trả về `HTTP 429`.

---

## 5. Công việc đề xuất tiếp theo (Next Steps)

1. **Thu thập & Kiểm định Tập dữ liệu Người thật có Đồng ý (`N >= 35` người)**:
   - Thực hiện đo thước dây (2 người đo $\times$ 2 lần) theo [`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md), nạp vào `verification/datasets/real_human_pilot/` và chạy [`evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py) để hiệu chuẩn khoảng dự đoán Split Conformal thực nghiệm.
2. **Kiểm thử Thực địa Camera Phần cứng**:
   - Đo kiểm trên các dòng webcam laptop (720p/1080p) và điện thoại thực tế dưới nhiều mức ánh sáng (`150–500 lux`).
3. **Tăng cường cấu hình Production**:
   - Bật `MORPH_COOKIE_SECURE=1` khi chạy HTTPS; chuyển lưu trữ trạng thái job/rate-limit sang SQLite/Redis nếu mở rộng nhiều worker process.
