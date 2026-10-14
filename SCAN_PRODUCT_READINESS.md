# Báo Cáo Nghiệm Thu & Đánh Giá Mức Độ Sẵn Sàng Chức Năng 3D Body Scan (`SCAN_PRODUCT_READINESS.md`)

- **Run ID Nghiệm thu**: `run-20261014-v2`
- **Thư mục lưu trữ bằng chứng (Log, Screenshot, JSON Report)**: [`output/runs/run-20261014-v2/`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/)
- **Phiên bản Engine**: `ENGINE = "mediapipe-two-photo-fit-v4"`

---

## 0. Bảng Phân Loại Trạng Thái Nghiệm Thu Tổng Thể (Readiness Matrix)

> [!IMPORTANT]
> **Kết luận tổng thể về mức độ sẵn sàng (`Overall Product-Readiness Verdict`)**:  
> **CHƯA ĐỦ ĐIỀU KIỆN CÔNG BỐ PRODUCT-READY VỀ ĐỘ CHÍNH XÁC NHÂN TRẮC HỌC (`PRE-PILOT / GATED ON REAL-HUMAN VALIDATION`)**.  
> Hệ thống chỉ được phép kết luận **Product-Ready** sau khi hoàn tất thu thập tập dữ liệu người thật có đồng ý sử dụng (`Informed Consent`) và vượt qua đầy đủ các cổng kiểm định (Acceptance Gates) tại Mục 6.

| Hạng mục Đánh giá | Trạng thái Hiện tại | Bộ Test / Script Kiểm chứng | Tập dữ liệu & Số mẫu (`N`) | Phạm vi Thực tế & Giới hạn |
| :--- | :---: | :--- | :--- | :--- |
| **1. Implementation & Security Verification** (Logic code, bảo mật `guest_token`, lọc nguồn `source`, UI/UX state) | **PASSED** *(Trong phạm vi Unit, API & Browser E2E)* | - [`backend/tests/`](file:///d:/MORPH-AI/backend/tests/)<br>- [`test_capture_quality.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_quality.cjs)<br>- [`test_capture_session_e2e.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_session_e2e.cjs)<br>- `tsc --noEmit` | - Backend: **`N = 107` test cases**<br>- Unit Quality: **`N = 16` checks**<br>- Browser E2E: **`N = 8` kịch bản DOM/Network**<br>- TypeScript: **`0` lỗi biên dịch** | Đã kiểm chứng trên FastAPI TestClient, SQLite cục bộ và Chromium với `canvas.captureStream(30)`. **Chưa kiểm chứng tự động trên phần cứng webcam vật lý đa thiết bị** (ISP auto-exposure, rolling shutter, méo ống kính). |
| **2. Synthetic / Geometric Validation** (Tính nhất quán toán học 3 tầng, khớp mặt cắt `.glb`, bất biến tỷ lệ $D/W$) | **PASSED** *(Chỉ trong phạm vi Hình học Tổng hợp)* | - [`benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py)<br>- [`evaluate_3d_scan_accuracy.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_3d_scan_accuracy.py) | - Calibration: **`N_cal = 12` subjects (`36` scans)**<br>- Held-out Eval: **`N_eval = 10` subjects (`30` scans)**<br>- LOSO-CV: **`N = 13` archetypes**<br>- Perturbation: **`N = 10` kịch bản**<br>- Catalog Sizing: **`N = 160` sản phẩm** | Đánh giá trên silhouette chiếu từ lưới 3D biến dạng MakeHuman có nhiễu pixel/landmark có kiểm soát. **Không đại diện cho sai số mô mềm, quần áo thực tế và hình thái cơ thể người thật.** |
| **3. API Lifecycle & Bounded Concurrent Load Test** (Cold/Warm start, HTTP queue, WebGL render, tải đồng thời, RSS vs Heap) | **EXECUTED** *(Trong phạm vi Local Single-Worker CPU)* | - [`benchmark_scan_api_and_load.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_api_and_load.py)<br>- Báo cáo: [`BENCHMARK_API_AND_LOAD_SUMMARY.md`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/benchmark/BENCHMARK_API_AND_LOAD_SUMMARY.md) | - Cold Start: **`N = 1` subprocess**<br>- Warm In-Process: **`N = 16` scans**<br>- Full HTTP API: **`N = 10` scans**<br>- WebGL Render: **`N = 8` warm + `1` cold**<br>- Load Test: **`4` mức (`C = 1, 2, 4, 10`, tổng `29` requests)**<br>- Memory: **`9` checkpoints** | Đo thực tế trên máy `Core i7-1165G7` (`1` Uvicorn process, `ThreadPoolExecutor(max_workers=1)`, `MAX_ACTIVE_JOBS = 8`). Khi `C >= 4`, thời gian chờ hàng đợi (`queue_wait_ms P95`) tăng lên `12.39s – 20.90s`. Chưa kiểm thử tải phân tán đa máy chủ hoặc qua mạng WAN. |
| **4. Real-Human Anthropometric Accuracy** (Độ chính xác so với thước dây trên người thật & Khoảng dự đoán thực nghiệm) | **NOT CONFIRMED / NOT ACCEPTED** (`MISSING_EMPIRICAL_COHORT`) | - [`evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py)<br>- Quy trình: [`ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md) | - Người thật có đồng ý: **`N_human = 0` subjects** (`verification/datasets/real_human_pilot/` chưa có dữ liệu) | **Chưa thể nghiệm thu độ chính xác trên người thật.** Trường `uncertainty_cm` trong báo cáo số đo bắt buộc giữ giá trị `null` (`None`). |

---

## 1. Tóm Tắt Các Lỗi Đã Tái Hiện, Khắc Phục Và Bằng Chứng Kiểm Thử

Mọi kết luận sửa lỗi dưới đây đều gắn với file mã nguồn, bài kiểm thử cụ thể và số lượng mẫu thực thi:

| STT | Vấn đề đã tái hiện | Giải pháp kỹ thuật đã triển khai | Bài test, Tập dữ liệu & Số mẫu (`N`) chứng minh |
| :---: | :--- | :--- | :--- |
| **1** | **Lỗ hổng bỏ qua `guest_token` khi thiếu header/query & giữ lại token khách sau khi user lưu scan** | - Bắt buộc mọi request tới phiên scan khách (`GET /api/scans/{id}`, `/model`, `/measurements`, `/size-advice`, `POST /api/sizing/recommend`, `DELETE /api/scans/{id}`) phải gửi `guest_token` khớp qua `secrets.compare_digest` (`403 Forbidden` nếu thiếu/sai).<br>- Khi user claim scan qua `POST /api/user/scans/save`, gán `job.user_id` và xóa `job.guest_token = None`. | - [`backend/tests/test_api.py`](file:///d:/MORPH-AI/backend/tests/test_api.py) (`N = 19` tests) & [`backend/tests/test_auth_and_history.py`](file:///d:/MORPH-AI/backend/tests/test_auth_and_history.py) (`N = 26` tests): kiểm tra đủ 4 tổ hợp (valid token `200`, invalid token `403`, missing token `403`, cross-user access `403`) trên 6 endpoints.<br>- [`verification/scripts/repro_reported_issues.py`](file:///d:/MORPH-AI/verification/scripts/repro_reported_issues.py) (`N = 4` kịch bản bảo mật trực tiếp). |
| **2** | **Nhánh gợi ý size từ SQLite (`body_measurements`) bỏ qua cột `source`, dùng `hip_cm` của `template_model` để gợi ý quần/váy cho scan `upper_body`** | - Định nghĩa [`VALID_SIZING_SOURCES`](file:///d:/MORPH-AI/backend/app/sizing.py#L6) `= {"photo_estimate", "photo_with_prior", "user_input"}` và hàm [`filter_valid_sizing_measurements`](file:///d:/MORPH-AI/backend/app/sizing.py#L91-L148).<br>- Lọc bỏ mọi metric có `source in {"template_model", "unavailable"}` hoặc `<= 0` ở cả nhánh RAM (`jobs`) và nhánh SQLite (`body_measurements`). | - [`backend/tests/test_auth_and_history.py`](file:///d:/MORPH-AI/backend/tests/test_auth_and_history.py) & [`backend/tests/test_sizing.py`](file:///d:/MORPH-AI/backend/tests/test_sizing.py) (`N = 25` tests): đối chiếu trực tiếp kết quả `POST /api/sizing/recommend` trước và sau khi `jobs.pop(scan_id)` cho cả `top` và `bottom` ở 2 chế độ `upper_body` / `full_body`.<br>- [`benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py) (Mục 5): kiểm tra trên **`N = 160` sản phẩm thực tế trong SQLite** (`82` sản phẩm thân trên khớp size bình thường; `78` sản phẩm quần/chân váy trả về `insufficient_measurements` với `missing = ["hip_cm"]` khi quét `upper_body`). |
| **3** | **Lịch sử scan (`GET /api/user/scans`) đưa cả số đo `template_model` vào `key_measurements`** | - Trong [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py) (`list_scans` & `/chart`), loại bỏ các dòng có `source in ("template_model", "unavailable")`, giữ `null` là thiếu dữ liệu. | - [`backend/tests/test_auth_and_history.py`](file:///d:/MORPH-AI/backend/tests/test_auth_and_history.py) (`test_upper_body_saved_scan_blocks_template_hip_in_history_and_sizing`) & [`regression_frontend_chart_checkout.cjs`](file:///d:/MORPH-AI/verification/scripts/regression_frontend_chart_checkout.cjs) (`N = 12` assertions trên `BodyChart`). |
| **4** | **Camera lấy mù quáng frame tại `t = 0`, thiếu kiểm tra chất lượng khung hình & độ lệch khoảng cách giữa 2 góc** | - Xây dựng [`frontend/lib/captureQuality.ts`](file:///d:/MORPH-AI/frontend/lib/captureQuality.ts) và tích hợp vào [`CaptureSession.tsx`](file:///d:/MORPH-AI/frontend/components/shop/CaptureSession.tsx): kiểm tra độ sáng (`45..235`), độ nét Laplacian (`>= 14.0`), độ dịch chuyển mốc (`< 0.018`), độ lệch khoảng cách giữa 2 góc (`<= 18%`), chọn frame có `frameQualityScore` cao nhất trong cửa sổ `1600ms` cuối, và hủy countdown tức thì khi mất điều kiện. | - Unit Test: [`test_capture_quality.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_quality.cjs) (**`N = 16/16` checks PASS**).<br>- Browser E2E Test: [`test_capture_session_e2e.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_session_e2e.cjs) (**`N = 8/8` kịch bản hành vi trên trình duyệt Chromium PASS**, lưu ảnh và báo cáo tại [`output/runs/run-20261014-v2/capture-e2e/report.json`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/capture-e2e/report.json)). |
| **5** | **Thiếu metadata nguồn dữ liệu chi tiết trên từng chỉ số & chưa kiểm định lưới `.glb` xuất ra** | - Nâng cấp [`measurement_report()`](file:///d:/MORPH-AI/backend/app/report.py) xuất `source`, `observed_region`, `valid_for_sizing`, `valid_for_tracking`, `quality_warnings`, `engine_version`, `uncertainty_cm: None`.<br>- Bổ sung [`validate_glb_mesh()`](file:///d:/MORPH-AI/backend/app/measurements.py) kiểm tra đơn vị mét, chân tại `y ≈ 0`, không có đỉnh `NaN/Inf` hoặc mặt suy biến. | - [`backend/tests/test_reconstruction.py`](file:///d:/MORPH-AI/backend/tests/test_reconstruction.py) (`N = 11` tests) & [`backend/tests/test_photo_measurements.py`](file:///d:/MORPH-AI/backend/tests/test_photo_measurements.py) (`N = 11` tests). |
| **6** | **Giữ lại state `job` cũ khi API quét mới lỗi; thiếu giới hạn hàng đợi/timeout job treo; câu chữ Auth chưa chính xác** | - Gọi `setJob(null)` trước khi gửi `POST /api/scans` trong [`useBodyScan.ts`](file:///d:/MORPH-AI/frontend/lib/useBodyScan.ts).<br>- Bổ sung `MAX_ACTIVE_JOBS = 8`, `MAX_STORED_JOBS = 50`, `JOB_PROCESSING_TIMEOUT_SECONDS = 120` trong [`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py).<br>- Cập nhật câu chữ quyền riêng tư tại `/auth/login`, `/auth/register`, `FitExperience.tsx`. | - [`backend/tests/test_api.py`](file:///d:/MORPH-AI/backend/tests/test_api.py) (kiểm tra timeout `120s` và `MAX_STORED_JOBS = 50`).<br>- Load Test Mức 4 trong [`benchmark_scan_api_and_load.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_api_and_load.py) (`N = 10` request đồng thời: nhận đúng `8` jobs và trả `HTTP 429` cho `2` request vượt ngưỡng). |
| **7** | **Nhấn phím `Escape` khi mở dropdown màu đóng nhầm Wishlist Drawer & Cộng đôi số lượng giỏ hàng** | - Chặn `Escape` ở capture phase trong [`CustomSelect.tsx`](file:///d:/MORPH-AI/frontend/components/shop/CustomSelect.tsx) và kiểm tra `e.defaultPrevented` trong [`useDrawerA11y.ts`](file:///d:/MORPH-AI/frontend/lib/useDrawerA11y.ts).<br>- Đồng bộ số lượng tuyệt đối (`isAbsolute = true`) trong [`WishlistDrawer.tsx`](file:///d:/MORPH-AI/frontend/components/shop/WishlistDrawer.tsx). | - [`wishlist-escape-cart-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/wishlist-escape-cart-verification.cjs) (**`N = 7/7` checks PASS** trên trình duyệt Chromium). |

---

## 2. Kết Quả Kiểm Thử Hành Vi `CaptureSession` Trên Trình Duyệt (Browser E2E) & Giới Hạn Phần Cứng

- **Script thực thi**: [`verification/scripts/test_capture_session_e2e.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_session_e2e.cjs)
- **Báo cáo & Screenshot lưu theo Run ID**: [`output/runs/run-20261014-v2/capture-e2e/report.json`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/capture-e2e/report.json), [`console.log`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/capture-e2e/console.log)
- **Phương pháp kiểm thử**: Chạy Chromium thực tế mở trang `/scan`, inject luồng video xác định (`canvas.captureStream(30)` với `1280×720`) vào `navigator.mediaDevices.getUserMedia` và `enumerateDevices` (`2` thiết bị camera giả lập `cam-1`, `cam-2`), kiểm chứng trực tiếp trên DOM, sự kiện trình duyệt và gói tin multipart `POST /api/scans` (không dùng tìm kiếm chuỗi mã nguồn).

### 2.1. Kết quả 8 kịch bản hành vi trình duyệt (`8/8 PASS`, `0` lỗi console/page)

| Kịch bản E2E | Hành vi kích hoạt trên Trình duyệt | Kết quả quan sát & Bằng chứng (`output/runs/run-20261014-v2/capture-e2e/`) |
| :--- | :--- | :--- |
| **1. Lỗi quyền truy cập & Retry (`NotAllowedError`)** | Lần đầu gọi `getUserMedia` ném `DOMException("Permission denied", "NotAllowedError")`; sau đó cấp quyền và bấm `Thử lại camera`. | Hiển thị `role="alert"` tiếng Việt hướng dẫn mở quyền camera; sau khi bấm `Thử lại camera`, `<video>` phát ở `1280×720` (`readyState = 4`) và nút `Bắt đầu quét` được bật (`01a-permission-denied.png`, `01b-camera-ready.png`). |
| **2. Hủy đếm ngược tức thì khi mất điều kiện** | Đang đếm ngược ở góc `01 · Chính diện` (`.capture-count` hiển thị `"3"`), bơm frame có chuyển động landmark `motion > 0.05` (`>= 0.018`). | `.capture-count` bị gỡ khỏi DOM ngay lập tức; `.capture-status-message` hiển thị `"Đã tạm dừng đếm ngược: Hình ảnh đang bị nhòe do chuyển động. Hãy đứng yên hơn."` (`02a-countdown-active.png`, `02b-countdown-cancelled.png`). |
| **3. Chọn đúng Frame nét nhất trong cửa sổ `1600ms`** | Trong cửa sổ `1600ms` cuối: tại `t = deadline - 1217ms` phát frame sắc nét cao (`RGB = 180`, `sharpness = 43264`, `score = 0.992`); tại `t = deadline - 201ms..0ms` phát frame kém nét hơn (`RGB = 90`, `sharpness = 22`, `score = 0.636..0.531`). | Giải mã pixel file `front.jpg` (`13,274 bytes`) bắt từ request `POST /api/scans` bằng `createImageBitmap`: **`meanR = 180, meanG = 180, meanB = 180`**, chứng minh hệ thống chọn đúng frame có `score = 0.992` thay vì frame cuối lúc `t = 0` (`scan1-uploaded-front.jpg`). |
| **4. Chuyển pha tự động `front → turn → side`** | Hoàn tất đếm ngược góc `01 · Chính diện`. | Hiển thị màn hình `.capture-turn` (`"Đã chụp chính diện"`, `"Xoay người 90°"`), sau đó tự chuyển sang `Bước 02 / 02` (`02 · Góc nghiêng`) mà không cần bấm nút (`04a-turn-screen.png`, `04b-auto-transitioned-to-side.png`). |
| **5. Chặn sai khoảng cách đứng giữa 2 góc (`Cross-View Drift`)** | Ở góc `02 · Góc nghiêng`, bơm landmark có `hip_y - shoulder_y = 0.405` (lệch `+35% > 18%` so với `0.30` của góc chính diện). | Countdown bị chặn hoàn toàn; pill hiển thị `"Khoảng cách: Lệch vị trí"` (`.is-warn`) và thông báo `"Khoảng cách đứng đã thay đổi so với góc chính diện. Hãy đứng đúng vị trí cũ và xoay 90°."` (`05-cross-view-distance-drift.png`). |
| **6. Đổi thiết bị Camera & Mất kết nối giữa chừng (`onended`)** | Mở dropdown `Chọn camera` chuyển từ `cam-1` sang `cam-2`; sau đó kích hoạt `videoTrack.onended()` khi đang quét, rồi bấm `Thử lại camera` để chụp hoàn tất cả 2 góc. | Khi đổi sang `cam-2`, track của `cam-1` được gọi `.stop()` và phiên reset về `01 · Chính diện`. Khi `onended` nổ, hiện cảnh báo `"Camera đã ngắt kết nối giữa chừng..."`. Sau khi bấm `Thử lại camera`, chụp đủ `front.jpg` + `side.jpg` gửi lên `POST /api/scans` (`06a..06c`). |
| **7. Đóng phiên / Hủy phiên & Thu hồi Track** | Click `Hủy phiên` và nút `X` (`Đóng camera`). | Component `.capture-session` đóng khỏi DOM; toàn bộ `8/8` `MediaStreamTrack` được tạo trong suốt bài test đều ở trạng thái `readyState === "ended"` (`leakedActiveTracks = 0`) (`07-session-cancelled-clean.png`). |
| **8. Ranh giới kiểm chứng phần cứng** | Kiểm tra đối chiếu phạm vi mock vs vật lý. | Ghi nhận tường minh trong `report.json` (`verificationBoundary`). |

### 2.2. Phần Camera phần cứng vật lý CHƯA được kiểm chứng bởi bài test trình duyệt
Bài test E2E trên sử dụng luồng `canvas.captureStream(30)` xác định trên Chromium. Các yếu tố phần cứng vật lý sau **chưa được kiểm chứng tự động** và cần kiểm tra thực địa trên thiết bị thật trước khi mở Pilot:
1. **ISP Auto-Exposure / Auto-White-Balance (AE/AWB)**: Hiện tượng webcam tự động đẩy sáng/giảm sáng thất thường khi người dùng di chuyển trước cửa sổ hoặc đèn trần chiếu ngược.
2. **Rolling Shutter & Sensor Noise**: Độ nhòe chuyển động thực tế của cảm biến CMOS giá rẻ trên laptop trong phòng thiếu sáng (`< 150 lux`) khi tốc độ màn trập giảm xuống `< 1/15s`.
3. **Méo quang học ống kính (Barrel / Perspective Distortion)**: Biến dạng phối cảnh khi người dùng đặt laptop dưới thấp ngửa lên hoặc đứng quá gần ống kính góc rộng điện thoại.
4. **Hành vi Driver USB/UVC & Privacy Shutter vật lý**: Trường hợp cần gạt che camera vật lý đóng (phát khung hình đen hoàn toàn mà không ném lỗi `DOMException`) hoặc xung đột độc quyền thiết bị với Zoom/Teams trên Windows.

---

## 3. Kết Quả Kiểm Định Hình Học, Hiệu Chuẩn Khoảng Dự Đoán & Trạng Thái Dữ Liệu Người Thật

- **Scripts thực thi**:
  - [`verification/scripts/evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py)
  - [`verification/scripts/benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py)
  - [`verification/scripts/evaluate_3d_scan_accuracy.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_3d_scan_accuracy.py)
- **Báo cáo & Log lưu theo Run ID**:
  - [`output/runs/run-20261014-v2/validation/human_validation_cohort_report.json`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/validation/human_validation_cohort_report.json)
  - [`output/runs/run-20261014-v2/validation/scan_product_readiness_benchmark.json`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/validation/scan_product_readiness_benchmark.json)
  - [`output/runs/run-20261014-v2/validation/evaluate_human_validation_cohort.log`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/validation/evaluate_human_validation_cohort.log)

### 3.1. Đối chiếu Vị trí Đo: Tiêu chuẩn Quốc tế (`ISO 7250-1:2017` / `ISO 8559-1:2017`) vs. Thuật toán Hiện tại
Chi tiết đầy đủ được quy định tại [`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md) (Mục 2):
- **`height_cm`**: Theo `ISO 7250-1:2017 Clause 6.1.1` / `ISO 8559-1:2017 Clause 5.1.1` là chiều cao đứng (*Stature*) từ sàn đến *Vertex*. Trong hệ thống: người dùng tự nhập (`source = "user_input"`), dùng làm hệ số quy đổi toàn cục từ pixel sang `cm`.
- **`shoulder_width_cm` (Khác biệt cấu trúc mốc đo cần lưu ý)**:
  - Trong `ISO 7250-1:2017 Clause 6.2.1` (*Biacromial breadth*) là khoảng cách giữa hai mỏm cùng vai xương (*Acromion*); trong `ISO 8559-1:2017 Clause 5.4.1` (*Shoulder width*) đo qua bề mặt lưng/acromion.
  - Trong [`backend/app/measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py#L47): Hệ thống tính `shoulder_width_cm = shoulder_ratio * height_cm` từ khoảng cách ngang Euclidean 2D giữa hai mốc **MediaPipe Pose Landmarks `11` và `12` (tâm khớp vai 2D suy từ ảnh RGB)**, vốn nằm thấp và dịch vào trong (*medial*) khoảng `1.2–2.2 cm` mỗi bên (`~2.4–4.4 cm` tổng cộng) so với mỏm xương *Acromion*. Trên tập hình học (`N_eval = 30`), nếu so trực tiếp với *Biacromial breadth* chưa hiệu chuẩn bù độ chệch mốc, `MAE = 3.33 cm` (`Bias = +3.27 cm`); sau khi hiệu chuẩn bù độ chệch mốc trên tập `calibration_split`, `Bias-Corrected MAE = 0.28 cm` (`90% Conformal Half-Width = ±0.53 cm`).
- **`chest_cm`**: `ISO 8559-1:2017 Clause 5.3.4` (*Chest/Bust girth* ngang qua *Thelion/Mesosternale*). Trong [`measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py#L46-L67): lấy chu vi mặt cắt lớn nhất (`max`) trong dải tỷ lệ thân `fractions ∈ [0.30, 0.44]` (tương ứng độ cao lưới `0.6774 H .. 0.7180 H`), nhân hệ số bù lõm giải phẫu `ANATOMICAL_SECTION_FACTORS["chest_cm"] = 1.08074`.
- **`waist_cm`**: `ISO 8559-1:2017 Clause 5.3.10` (*Natural waist girth* nhỏ nhất giữa bờ sườn 10 và *Iliocristale*). Trong [`measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py#L46-L67): lấy chu vi mặt cắt nhỏ nhất (`min`) trong dải `fractions ∈ [0.52, 0.78]` (tương ứng độ cao lưới `0.5788 H .. 0.6542 H`), nhân hệ số `1.03209`.
- **`hip_cm`**: `ISO 8559-1:2017 Clause 5.3.13` (*Hip/Seat girth* lớn nhất qua *Gluteal prominence*). Trong [`measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py#L46-L67): lấy chu vi mặt cắt lớn nhất (`max`) trong dải `fractions ∈ [0.95, 1.12]` (tương ứng `0.4802 H .. 0.5295 H`), nhân hệ số `1.06234`; bị khóa cứng `None` khi `capture_mode == "upper_body"`.

### 3.2. Khoảng Dự Đoán Được Hiệu Chuẩn (Split Conformal Prediction & Empirical Quantiles — Thay thế `±1.96 × RMSE`)
Thay vì dùng công thức tham số `±1.96 × RMSE` (vốn giả định sai số phân phối chuẩn đối xứng tâm 0 và phương sai đồng nhất), hệ thống áp dụng **Split Conformal Prediction có khử độ chệch (Bias-Corrected Split Conformal)** và **Khoảng Phân Vị Phần Dư Bất Đối Xứng (Asymmetric Empirical Quantile Interval)** hiệu chuẩn trên tập `calibration_split` tách biệt hoàn toàn theo `subject_id` (`verify_subject_disjoint_split`):
- Với tập hiệu chuẩn $D_{\text{cal}}$ ($n$ mẫu), tính độ chệch trung bình $\hat{\mu}_{\text{cal}} = \frac{1}{n}\sum_{i=1}^n (y_i^{\text{GT}} - \hat{y}_i)$ và điểm bất tương hợp $s_i = |y_i^{\text{GT}} - (\hat{y}_i + \hat{\mu}_{\text{cal}})|$.
- Phân vị hữu hạn mẫu mức $1 - \alpha$: $\hat{q}_{1-\alpha} = \text{Quantile}\left(\{s_1, \dots, s_n\}; \min\left(1, \frac{\lceil (n + 1)(1 - \alpha) \rceil}{n}\right)\right)$.
- Khoảng dự đoán cho mẫu mới: $C_{1-\alpha}^{\text{sym}}(x) = [\hat{y}(x) + \hat{\mu}_{\text{cal}} - \hat{q}_{1-\alpha},\; \hat{y}(x) + \hat{\mu}_{\text{cal}} + \hat{q}_{1-\alpha}]$ (độ rộng $W = 2\hat{q}_{1-\alpha}$).

**Kết quả kiểm chứng bộ hiệu chuẩn trên Tập Hình Học Độc Lập** (`D_cal`: `12` subjects $\times$ `3` điều kiện $= 36$ scans; `D_eval`: `10` held-out subjects $\times$ `3` điều kiện $= 30$ scans, bao gồm cả nhiễu trang phục `+0.8 px`/cạnh và jitter mốc):

| Chế độ (`capture_mode`) | Chỉ số (`metric_key`) | Số mẫu Eval (`N_eval`) | Raw MAE (cm) | Bias-Corrected MAE (cm) | Độ chệch $\hat{\mu}_{\text{cal}}$ (cm) | 90% Conformal Half-Width / Width (cm) | 90% Empirical Coverage trên `D_eval` | 95% Conformal Half-Width / Width (cm) | 95% Empirical Coverage trên `D_eval` | 90% Asymmetric Quantile $[\hat{q}_{0.05}, \hat{q}_{0.95}]$ (`Width` / `Cov`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`full_body`** | `chest_cm` | `30` (`10` subj) | `0.56` | `0.46` | `-0.41` | `±0.76` (`1.51 cm`) | **`86.7%`** (`26/30`) | `±0.94` (`1.87 cm`) | **`96.7%`** (`29/30`) | `[-1.21, +0.26]` (`1.47 cm` / `83.3%`) |
| **`full_body`** | `waist_cm` | `30` (`10` subj) | `1.19` | `0.43` | `-1.17` | `±0.77` (`1.54 cm`) | **`86.7%`** (`26/30`) | `±0.85` (`1.71 cm`) | **`90.0%`** (`27/30`) | `[-1.95, -0.45]` (`1.50 cm` / `86.7%`) |
| **`full_body`** | `hip_cm` | `30` (`10` subj) | `0.51` | `0.48` | `+0.16` | `±0.97` (`1.94 cm`) | **`96.7%`** (`29/30`) | `±1.16` (`2.31 cm`) | **`100.0%`** (`30/30`) | `[-0.81, +0.76]` (`1.57 cm` / `93.3%`) |
| **`full_body`** | `shoulder_width_cm` *(đối chiếu mốc khớp)* | `30` (`10` subj) | `0.19` | `0.19` | `+0.05` | `±0.45` (`0.90 cm`) | **`96.7%`** (`29/30`) | `±0.45` (`0.90 cm`) | **`96.7%`** (`29/30`) | `[-0.25, +0.39]` (`0.64 cm` / `96.7%`) |
| **`full_body`** | `shoulder_width_cm` *(đối chiếu Biacromial ISO)* | `30` (`10` subj) | `3.33` | `0.28` | `+3.27` | `±0.53` (`1.06 cm`) | **`86.7%`** (`26/30`) | `±0.58` (`1.16 cm`) | **`90.0%`** (`27/30`) | `[+2.74, +3.72]` (`0.98 cm` / `83.3%`) |
| **`upper_body`** | `chest_cm` | `30` (`10` subj) | `0.81` | `0.73` | `-0.32` | `±1.60` (`3.20 cm`) | **`96.7%`** (`29/30`) | `±1.69` (`3.38 cm`) | **`96.7%`** (`29/30`) | `[-1.84, +1.05]` (`2.89 cm` / `96.7%`) |
| **`upper_body`** | `waist_cm` | `30` (`10` subj) | `1.20` | `0.68` | `-1.09` | `±1.29` (`2.58 cm`) | **`86.7%`** (`26/30`) | `±1.49` (`2.97 cm`) | **`90.0%`** (`27/30`) | `[-2.39, +0.16]` (`2.55 cm` / `86.7%`) |
| **`upper_body`** | `hip_cm` | `30` (`10` subj) | *Locked* | *Locked* | *N/A* | *N/A (`None`)* | **`0.0%`** *(Chặn sizing)* | *N/A (`None`)* | **`0.0%`** *(Chặn sizing)* | *N/A (`None`)* |
| **`upper_body`** | `shoulder_width_cm` *(đối chiếu mốc khớp)* | `30` (`10` subj) | `0.24` | `0.24` | `+0.07` | `±0.67` (`1.34 cm`) | **`93.3%`** (`28/30`) | `±0.83` (`1.66 cm`) | **`100.0%`** (`30/30`) | `[-0.36, +0.62]` (`0.98 cm` / `93.3%`) |

### 3.3. Phân rã Coverage & Độ rộng theo Nhóm Dữ liệu Độc lập (Subgroup Breakdown trên `D_eval`, `N = 30`)
- **Theo nhóm tỷ lệ lưng (`torso_ratio_group`: `short_torso` $r \le 0.28$, `medium_torso` $0.28 < r < 0.30$, `long_torso` $r \ge 0.30$)**:
  - Ở `full_body`: `chest_cm` đạt `BC_MAE = 0.42–0.48 cm` (`Cov90 = 83.3%–88.9%`, `Width = 1.51 cm`); `hip_cm` đạt `BC_MAE = 0.45–0.53 cm` (`Cov90 = 88.9%–100.0%`, `Width = 1.94 cm`).
  - Ở `upper_body`: `chest_cm` có độ rộng khoảng dự đoán lớn hơn (`Width = 3.20 cm`, `Cov90 = 88.9%–100.0%`) do phụ thuộc vào ước lượng chiều cao từ đa mỏ neo sọ–vai–hông.
- **Theo nhóm kích thước hình thể (`body_size_tier`: `petite_slim`, `standard_athletic`, `broad_plus`)**:
  - Nhóm `broad_plus` (`N = 9` scans) có `BC_MAE` vòng eo cao hơn (`0.64 cm` ở `full_body`, `0.78 cm` ở `upper_body`, `Cov90 = 77.8%`) so với nhóm `standard_athletic` (`N = 12` scans, `BC_MAE = 0.36 cm`, `Cov90 = 91.7%`).
- **Theo điều kiện nhiễu/trang phục (`perturbation_condition`: `baseline_tight_fit`, `moderate_pose_jitter`, `everyday_light_attire`)**:
  - Ở `baseline_tight_fit` (`N = 10`) và `moderate_pose_jitter` (`N = 10`), độ phủ `Cov90` đạt **`90.0% – 100.0%`** trên tất cả các chỉ số. Khi có độ dày trang phục (`everyday_light_attire`, `N = 10`), phần dư bị dịch dương làm giảm độ phủ của khoảng chung xuống `70.0% – 90.0%`, khẳng định khi áp dụng trên người thật cần hiệu chuẩn khoảng dự đoán phân tầng theo loại trang phục (`tight_activewear` vs `regular_casual`).

---

## 4. Kết Quả Benchmark Hiệu Năng: Tách Biệt Hàm `reconstruct()` Với Toàn Luồng API, Tải Đồng Thời & Bộ Nhớ

- **Script thực thi**: [`verification/scripts/benchmark_scan_api_and_load.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_api_and_load.py)
- **Báo cáo & Log lưu theo Run ID**:
  - [`output/runs/run-20261014-v2/benchmark/benchmark_api_and_load.json`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/benchmark/benchmark_api_and_load.json)
  - [`output/runs/run-20261014-v2/benchmark/BENCHMARK_API_AND_LOAD_SUMMARY.md`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/benchmark/BENCHMARK_API_AND_LOAD_SUMMARY.md)
  - [`output/runs/run-20261014-v2/benchmark/benchmark_console.log`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/benchmark/benchmark_console.log)
- **Cấu hình phần cứng thực tế đã đo**: `Windows 10 Build 26200 (AMD64)`, CPU `11th Gen Intel Core i7-1165G7 @ 2.80GHz` (`8` luồng logic, thuần CPU TFLite XNNPACK, `0 MB VRAM`), RAM hệ thống `7.73 GB`, `Python 3.11.17`.

### 4.1. Benchmark In-Process Hàm `reconstruct()` (Cold Start vs Warm Start)

| Giai đoạn In-Process (Gọi trực tiếp hàm Python, không qua HTTP) | Số mẫu (`N`) | `P50 (ms)` | `P95 (ms)` | `Mean ± SD (ms)` | `Min / Max (ms)` |
| :--- | :---: | ---: | ---: | ---: | ---: |
| **Cold Start**: `import app.reconstruction` (Subprocess mới) | `1` | `5364.45` | `5364.45` | `5364.45` | `5364.45` |
| **Cold Start**: Nạp `get_detector()` (`pose_landmarker_full.task`, `8.96 MB`) | `1` | `9923.90` | `9923.90` | `9923.90` | `9923.90` |
| **Cold Start**: Nạp `read_template()` (`body-template.obj`, `19,158` verts) | `1` | `1118.14` | `1118.14` | `1118.14` | `1118.14` |
| **Cold Start**: Lần gọi `reconstruct()` đầu tiên (All-in-One chưa preload) | `1` | `9199.41` | `9199.41` | `9199.41` | `9199.41` |
| **Warm Start**: Thuật toán toán học 3 tầng (`Tier 1 + Tier 2 + Tier 3 PCHIP`) | `25` | `8.52` | `11.48` | `8.65 ± 1.75` | `6.34 / 14.38` |
| **Warm Start**: Kiểm tra tư thế 1 frame (`capture_feedback()`) | `10` | `50.43` | `63.80` | `53.09 ± 5.49` | `48.47 / 66.01` |
| **Warm Start**: Biến dạng Trimesh + Khớp 4 vòng (`18` lát cắt 3D) | `10` | `178.89` | `228.22` | `184.34 ± 31.54` | `140.46 / 231.41` |
| **Warm Start**: Hàm `reconstruct()` — `upper_body` (2 ảnh + Mesh + `.glb`) | `8` | `1734.38` | `2061.47` | `1719.60 ± 236.89` | `1345.03 / 2166.14` |
| **Warm Start**: Hàm `reconstruct()` — `full_body` (2 ảnh + Mesh + `.glb`) | `8` | `1734.76` | `2241.75` | `1739.78 ± 323.87` | `1333.23 / 2432.69` |
| **Warm Start**: Tổng hợp hàm `reconstruct()` In-Process | `16` | **`1734.38`** | **`2232.77`** | **`1729.69 ± 283.91`** | `1333.23 / 2432.69` |

*(Ghi chú: Tốc độ phục vụ lý thuyết của hàm `reconstruct()` đơn luồng trong bộ nhớ là `60 / 1.730s = 34.69 scans/phút`; con số này **không phải** là throughput tải thực tế qua API).*

### 4.2. Benchmark Toàn Luồng API (End-to-End HTTP Lifecycle) & Render WebGL Trên Trình Duyệt

Đo trực tiếp trên tiến trình `uvicorn app.main:app` thực tế kết hợp Playwright Chromium (`three@0.180.0` `GLTFLoader` + `WebGLRenderer`):

| Giai đoạn Toàn Luồng API & Browser Render | Số mẫu (`N`) | `P50 (ms)` | `P95 (ms)` | `Mean ± SD (ms)` | `Min / Max (ms)` |
| :--- | :---: | ---: | ---: | ---: | ---: |
| `POST /api/capture-check` (Upload multipart 1 frame + MediaPipe check) | `10` | `83.38` | `101.92` | `84.67 ± 10.55` | `69.39 / 105.63` |
| `POST /api/scans` (`scan_upload_enqueue_ms`: upload 2 ảnh $\rightarrow$ `202 Accepted`) | `10` | `27.08` | `42.22` | `29.10 ± 8.07` | `19.97 / 44.62` |
| `queue_wait_ms` (Thời gian chờ ở trạng thái `queued` khi `Concurrency = 1`) | `10` | `1.00` | `2.00` | `1.30 ± 0.46` | `1.00 / 2.00` |
| `worker_processing_ms` (Thời gian worker chạy `process()` $\rightarrow$ `completed`) | `10` | `2007.63` | `2334.13` | `1944.86 ± 305.44` | `1403.75 / 2459.66` |
| **`end_to_end_poll_completion_ms` (Từ lúc gửi `POST /api/scans` $\rightarrow$ poll `completed`)** | **`10`** | **`2155.72`** | **`2514.12`** | **`2094.87 ± 320.70`** | **`1527.13 / 2632.94`** |
| `GET /api/scans/{id}/model` (`glb_download_ms`, kích thước `680.62 KB`) | `10` | `29.10` | `189.18` | `67.82 ± 65.44` | `22.92 / 215.61` |
| `GET /api/scans/{id}/measurements` (`measurements_download_ms`) | `10` | `51.79` | `98.40` | `55.76 ± 25.14` | `26.35 / 120.49` |
| Trình duyệt Chromium: `fetch()` `.glb` + `GLTFLoader.parseAsync` + Render khung hình WebGL đầu tiên (**Cold Shader Compile**) | `1` | `578.50` | `578.50` | `578.50` | `578.50` |
| Trình duyệt Chromium: `fetch()` (`17.3ms`) + `parseAsync` (`1.0ms`) + Render khung hình WebGL (**Warm**) | `8` | **`35.10`** | **`74.84`** | **`42.52 ± 17.83`** | `27.80 / 84.50` |

### 4.3. Kết quả Chạy Tải Đồng Thời Có Giới Hạn (Bounded Concurrent Load Test)

| Mức tải (`Load Level`) | Concurrency (`C`) | Tổng Request (`N`) | Thành công (`Completed`) | Từ chối `HTTP 429` | Lỗi khác / Timeout | `queue_wait_ms` (`P50 / P95`) | `worker_processing_ms` (`P50 / P95`) | `client_total_ms` (`P50 / P95 / Max`) | Tổng thời gian thực (`Wall-Clock`) | **Throughput Quan Sát Thực Tế (`completed / wall_clock_min`)** |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: | ---: | ---: | ---: | :---: |
| **Mức 1 (Tuần tự)** | `1` | `5` | `5` | `0` | `0 / 0` | `1.00 / 2.00` | `2482.1 / 3076.3` | `2614.2 / 3221.5 / 3341.4` | `13.74 s` | **`21.84 scans/phút`** |
| **Mức 2 (Song song 2)** | `2` | `6` | `6` | `0` | `0 / 0` | `1311.7 / 2749.9` | `2780.8 / 3065.2` | `4309.0 / 5993.6 / 6027.1` | `17.71 s` | **`20.33 scans/phút`** |
| **Mức 3 (Song song 4)** | `4` | `8` | `8` | `0` | `0 / 0` | `6586.8 / 12394.1` | `3934.8 / 5113.8` | `10792.6 / 16419.2 / 17338.9` | `32.40 s` | **`14.81 scans/phút`** |
| **Mức 4 (Burst 10 — Test ngưỡng `MAX_ACTIVE_JOBS = 8`)** | `10` | `10` | `8` | **`2`** | `0 / 0` | `12352.7 / 20898.1` | `2864.2 / 4219.3` | `15646.4 / 23819.1 / 24699.7` | `24.77 s` | **`19.38 scans/phút`** |

- **Nhận xét kỹ thuật từ Load Test**:
  1. Do backend sử dụng `ThreadPoolExecutor(max_workers=1)` để tránh tranh chấp CPU giữa các tiến trình MediaPipe/Trimesh, **throughput thực tế quan sát được đạt `14.81 – 21.84 scans/phút`** (thấp hơn tốc độ lý thuyết in-process `34.69 scans/phút` do chi phí HTTP multipart, polling, giải mã ảnh và tranh chấp GIL khi nhận request đồng thời).
  2. Khi số người quét đồng thời tăng lên `C = 4` hoặc `C = 10`, các request xếp hàng tuần tự làm `queue_wait_ms P95` tăng lên **`12.39 s` (`C=4`)** và **`20.90 s` (`C=10`)**, kéo tổng thời gian chờ của client (`client_total_ms P95`) lên **`16.42 s – 23.82 s`**.
  3. Khi bắn burst `10` request đồng thời vượt ngưỡng `MAX_ACTIVE_JOBS = 8`, hệ thống trả về `HTTP 429 Too Many Requests` ngay trong `~30–40 ms` cho `2` request dư, bảo vệ `8` job đang chạy hoàn tất mà không phát sinh lỗi `500` hay timeout.

### 4.4. Bộ Nhớ Process: Phân Biệt OS Working Set (`RSS`) Với Python Managed Heap (`tracemalloc`)

| Điểm đo trong vòng đời Server (`Checkpoint`) | OS Working Set `RSS (MB)` | OS `Peak RSS (MB)` | Python Heap `Current (MB)` | Python Heap `Peak (MB)` | Số Jobs / File `.glb` đang giữ |
| :--- | ---: | ---: | ---: | ---: | :---: |
| 1. Uvicorn Cold Boot (Chưa nạp MediaPipe & Template) | `218.94` | `224.51` | `70.49` | `70.52` | `0 jobs / 0 .glb` |
| 2. Sau 10 lượt chạy Full HTTP Lifecycle (Đã nạp MediaPipe + Mesh) | `302.60` | `373.55` | `90.36` | `106.53` | `10 jobs / 10 .glb` |
| 3. Trước chuỗi Load Test (Sau khi xóa jobs + `cleanup()` + `gc.collect()`) | `279.74` | `373.55` | `70.99` | `106.53` | `0 jobs / 0 .glb` |
| 4. Đỉnh tải đồng thời Mức 4 (`Concurrency = 10`, giữ `27` jobs trên RAM/đĩa) | `307.09` | `373.55` | `92.92` | `124.80` | `27 jobs / 27 .glb` |
| 5. Sau khi thu hồi toàn bộ `27` jobs + xóa `.glb` + `cleanup()` + `gc.collect()` | **`283.31`** | **`373.55`** | **`71.01`** | **`124.80`** | **`0 jobs / 0 .glb`** |

- **Sự khác biệt giữa OS RSS và Python Heap**: `tracemalloc` chỉ đo các đối tượng do bộ cấp phát Python quản lý (`70.99 – 92.92 MB`, đỉnh `124.80 MB`), trong khi `OS Working Set RSS` (`279.74 – 309.10 MB`, đỉnh `373.55 MB`) bao gồm thêm `~210 MB` bộ nhớ C++ native của MediaPipe TFLite XNNPACK runtime, OpenCV/Pillow và Trimesh. Sau 37 lượt dựng hình 3D và dọn dẹp, Python Heap quay về `71.01 MB` (chênh `+0.02 MB` so với trước tải), xác nhận không rò rỉ bộ nhớ.

---

## 5. Các Giới Hạn Kỹ Thuật Còn Lại (Remaining Limitations)

1. **Chưa có tập dữ liệu kiểm định trên người thật (`N_human = 0`)**:
   - Mọi sai số báo cáo ở Mục 3.2 là sai số nội bộ trên tập hình học tổng hợp (`N_cal = 36`, `N_eval = 30`). Độ chính xác thực tế trên cơ thể người thật (với biến thiên mô mềm, nhịp thở, tư thế tự nhiên) **chưa được xác nhận**.
2. **Độ chệch cấu trúc giữa mốc MediaPipe `11–12` và mỏm xương `Acromion` (`shoulder_width_cm`)**:
   - Khoảng cách ngang giữa hai tâm khớp vai MediaPipe `11–12` hẹp hơn khoảng cách *Biacromial breadth* theo ISO 7250-1 khoảng `2.4 – 4.4 cm`. Nếu chưa có hệ số bù thực nghiệm trên người thật, `shoulder_width_cm` phản ánh khoảng cách liên khớp vai 2D chứ không phải chiều rộng vai may đo ngoài da.
3. **Độ nhạy với trang phục rộng và chiều cao tự nhập** (`N = 10` kịch bản trong [`benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py)):
   - Khi người dùng mặc áo khoác/quần áo rộng làm biên dạng mask phình thêm `+6 px` mỗi bên, chu vi ước lượng tăng giả tạo **`+8.7 cm` đến `+9.1 cm`** (lệch tăng `1 – 1.5` size).
   - Khi người dùng nhập sai chiều cao `±5 cm` (trên `172 cm`, tương đương `±2.91%`), các số đo chu vi trôi tuyến tính **`±2.2 cm` đến `±3.0 cm`**.
4. **Giới hạn chế độ `upper_body` trên Laptop**:
   - Không quan sát được vùng mông và chân; hệ thống bắt buộc khóa `hip_cm = None`, `inseam_cm = None` và từ chối gợi ý tự động cho `78/160` sản phẩm quần/chân váy cần `hip_cm` (trừ khi người dùng tự nhập số đo vòng mông thực tế `source = "user_input"`).
5. **Giới hạn kiến trúc xử lý đơn worker (`max_workers = 1`)**:
   - Phù hợp cho môi trường local / demo / cửa hàng quy mô nhỏ (`~15–22 scans/phút`), nhưng khi có `>= 4` người gửi lệnh dựng 3D cùng một thời điểm, thời gian chờ hàng đợi tăng lên `12–21 giây`.

---

## 6. Cổng Nghiệm Thu Bắt Buộc (Acceptance Gates) Trước Khi Kết Luận Product-Ready

Hệ thống chỉ được chuyển trạng thái sang **Product-Ready** sau khi hoàn thành thu thập dữ liệu theo [`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md) và chạy [`verification/scripts/evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py) đạt tất cả các cổng mục tiêu đề xuất sau:

1. **Gate 1 — Tập dữ liệu Người thật có Đồng ý & Kiểm soát TEM**:
   - Tối thiểu **`N >= 35` tình nguyện viên** có ký `informed_consent_signed = true`, chia tách hoàn toàn theo `subject_id` (`N_cal >= 15` người cho hiệu chuẩn Split Conformal, `N_eval >= 20` người cho kiểm định độc lập, `overlap == 0`).
   - Sai số kỹ thuật của người đo thước dây đạt $\text{TEM}_{\text{intra}} \le 0.4\text{ cm}$ và $\text{TEM}_{\text{inter}} \le 0.6\text{ cm}$.
2. **Gate 2 — Mục tiêu Đề xuất cho Pilot (Proposed Pilot Target Thresholds) trên Tập `evaluation_split` (Trang phục ôm chuẩn)**:
   *(Lưu ý: Đây là mục tiêu kỹ thuật đề xuất dựa trên nửa bước nhảy size may sẵn `4–8 cm`, không phải quy định của ISO)*:
   - `chest_cm`: $\text{MAE} \le 2.5\text{ cm}$ (`full_body`) / $\le 3.0\text{ cm}$ (`upper_body`), $|\text{Bias}| \le 1.0\text{ cm}$, $\text{P90} \le 4.0\text{ cm}$.
   - `waist_cm`: $\text{MAE} \le 2.5\text{ cm}$ (`full_body`) / $\le 3.0\text{ cm}$ (`upper_body`), $|\text{Bias}| \le 1.0\text{ cm}$, $\text{P90} \le 4.0\text{ cm}$.
   - `hip_cm`: $\text{MAE} \le 2.5\text{ cm}$ (`full_body`), khóa cứng `None` ở `upper_body`.
   - `shoulder_width_cm` (sau hiệu chuẩn bù độ chệch mốc Acromion): $\text{MAE} \le 1.8\text{ cm}$ (`full_body`) / $\le 2.0\text{ cm}$ (`upper_body`).
   - **Độ lặp lại (Repeatability SD qua 3 lần chụp liên tiếp)**: $\le 0.8\text{ cm}$ (`full_body`) / $\le 1.0\text{ cm}$ (`upper_body`).
   - **Tỷ lệ đồng thuận gợi ý size (Proposed RTW Size Agreement Target)**: $\ge 85\%$ (`full_body`) và $\ge 82\%$ (`upper_body` cho áo).
3. **Gate 3 — Hiệu chuẩn Khoảng Dự Đoán (Calibrated Prediction Intervals)**:
   - Khoảng dự đoán Split Conformal 90% hiệu chuẩn trên `calibration_split` phải đạt **Empirical Coverage $\ge 85\%$** trên tập `evaluation_split` và độ rộng nửa khoảng $\hat{q}_{0.90} \le 4.0\text{ cm}$ trước khi được phép gán vào trường `uncertainty_cm` trên giao diện.
4. **Gate 4 — Kiểm thử Thực địa Camera Phần cứng**:
   - Kiểm chứng trên tối thiểu `3` dòng webcam laptop (720p/1080p) và `2` camera điện thoại trong điều kiện ánh sáng phòng thực tế (`150–500 lux`).

---

## 7. Danh Mục Artifacts Theo Run ID & Lệnh Chạy Lại

Toàn bộ log, screenshot và báo cáo JSON của đợt nghiệm thu `run-20261014-v2` được lưu trữ tại [`output/runs/run-20261014-v2/`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/):
- **Browser E2E (`capture-e2e/`)**: [`report.json`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/capture-e2e/report.json), [`console.log`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/capture-e2e/console.log), bộ 11 ảnh screenshot `01a..07` và 2 ảnh JPEG trích xuất từ `POST /api/scans`.
- **API & Load Benchmark (`benchmark/`)**: [`benchmark_api_and_load.json`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/benchmark/benchmark_api_and_load.json), [`BENCHMARK_API_AND_LOAD_SUMMARY.md`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/benchmark/BENCHMARK_API_AND_LOAD_SUMMARY.md), [`benchmark_console.log`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/benchmark/benchmark_console.log), [`uvicorn_server.log`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/benchmark/uvicorn_server.log).
- **Validation & Conformal Calibration (`validation/`)**: [`human_validation_cohort_report.json`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/validation/human_validation_cohort_report.json), [`scan_product_readiness_benchmark.json`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/validation/scan_product_readiness_benchmark.json), [`evaluate_human_validation_cohort.log`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/validation/evaluate_human_validation_cohort.log), [`benchmark_scan_product_readiness.log`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/validation/benchmark_scan_product_readiness.log).
- **Integration Verification (`integration/`)**: `pytest_backend.log`, `test_capture_quality.log`, `tsc_typecheck.log`.

### Lệnh chạy lại toàn bộ các bộ kiểm định:
```powershell
$env:PATHEXT = ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL"
$env:PYTHONIOENCODING = "utf-8"

# 1. Kiểm thử Backend (107 tests)
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" -m pytest "D:\MORPH-AI\backend\tests" -q

# 2. Kiểm thử Unit Chất lượng Camera & Hình học (16 checks)
& "C:\Program Files\nodejs\node.exe" "D:\MORPH-AI\verification\scripts\test_capture_quality.cjs"

# 3. Kiểm thử Hành vi CaptureSession E2E trên Trình duyệt Chromium (8 kịch bản)
& "C:\Program Files\nodejs\node.exe" "D:\MORPH-AI\verification\scripts\test_capture_session_e2e.cjs"

# 4. Benchmark Tách biệt Hàm reconstruct(), Toàn luồng API, WebGL Render, Load Test & Memory RSS/Heap
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\benchmark_scan_api_and_load.py"

# 5. Harness Kiểm định Nhân trắc học & Hiệu chuẩn Khoảng dự đoán Split Conformal
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\evaluate_human_validation_cohort.py"
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\benchmark_scan_product_readiness.py"

# 6. Kiểm tra TypeScript Frontend
& "C:\Program Files\nodejs\node.exe" "D:\MORPH-AI\frontend\node_modules\typescript\bin\tsc" --project "D:\MORPH-AI\frontend\tsconfig.json" --noEmit
```
