# Báo Cáo Nghiệm Thu & Mức Độ Sẵn Sàng Sản Phẩm 3D Body Scan (`SCAN_PRODUCT_READINESS.md`)

Tài liệu này tổng hợp kết quả nâng cấp kỹ thuật, các lỗ hổng/lỗi đã tái hiện và khắc phục, đối chiếu số liệu **Baseline (Trước nâng cấp)** và **After (Sau nâng cấp)**, bằng chứng kiểm thử thực tế, cấu hình phần cứng/mô hình, và các điều kiện bắt buộc còn thiếu trước khi mở **Pilot trên người dùng thật**.

> [!IMPORTANT]
> **Tuyên bố trung thực về kỹ thuật & dữ liệu (Engineering Honesty Statement)**:
> 1. Hệ thống 3D Body Scan của **MORPH AI** sử dụng **MediaPipe Pose & Selfie Segmentation** kết hợp **hiệu chuẩn hình học 3 tầng** và **biến dạng lưới cơ sở MakeHuman (`body-template.obj`)** bằng nội suy PCHIP. Đây **không phải** SAM 3D Body / MHR hay quét quang trắc/LiDAR y tế; diện mạo khuôn mặt, bàn tay, bàn chân và chi tiết giải phẫu ngoài vùng thân được giữ theo mẫu.
> 2. Chúng tôi **không đánh đồng mô hình 3D đẹp mắt với số đo nhân trắc học chính xác**, và **không tuyên bố "production-ready" hay cam kết sai số lâm sàng $\pm X\text{ cm}$ trên người thật** khi chưa có tập dữ liệu kiểm định thực nghiệm độc lập đo bằng thước dây (`REAL_HUMAN_DATASET_STATUS = "MISSING_EMPIRICAL_COHORT"`).
> 3. Mọi chỉ số sai số dưới đây được phân tách rõ giữa **Kiểm thử Hình học / Tổng hợp (Synthetic/Geometric Verification)** và **Yêu cầu Kiểm định Người thật (Real-Human Pilot Gate)**.

---

## 1. Các lỗi đã tái hiện và khắc phục ( kèm File liên quan)

| STT | Vấn đề đã tái hiện | Nguyên nhân gốc (Root Cause) | Giải pháp kỹ thuật đã triển khai | File mã nguồn & Kiểm thử liên quan |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Lỗ hổng bỏ qua `guest_token` & nguy cơ rò rỉ token khách** | `check_scan_access` chỉ kiểm tra khi client có gửi `guest_token`, cho qua khi thiếu token; khi user lưu scan (`POST /api/user/scans/save`), `guest_token` cũ vẫn còn trên job trong RAM. | - Bắt buộc mọi request tới phiên scan khách (`GET /api/scans/{id}`, `/model`, `/measurements`, `/size-advice`, `POST /api/sizing/recommend`, `DELETE /api/scans/{id}`) phải gửi `guest_token` và khớp qua `secrets.compare_digest` (`403 Forbidden` nếu thiếu/sai).<br>- Khi user đăng nhập và claim scan qua `/api/user/scans/save`, gán `job.user_id` và xóa `job.guest_token = None`.<br>- Ẩn `guest_token` trong response khi `job.user_id is not None` và không ghi token vào log. | - [`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py)<br>- [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py)<br>- [`frontend/lib/ScanContext.tsx`](file:///d:/MORPH-AI/frontend/lib/ScanContext.tsx)<br>- [`frontend/lib/useBodyScan.ts`](file:///d:/MORPH-AI/frontend/lib/useBodyScan.ts)<br>- [`frontend/components/shop/ScanResult.tsx`](file:///d:/MORPH-AI/frontend/components/shop/ScanResult.tsx)<br>- [`backend/tests/test_api.py`](file:///d:/MORPH-AI/backend/tests/test_api.py)<br>- [`verification/scripts/repro_reported_issues.py`](file:///d:/MORPH-AI/verification/scripts/repro_reported_issues.py) |
| **2** | **Nhánh gợi ý size từ DB (`body_measurements`) bỏ qua `source`, dùng vòng mông mẫu 3D (`template_model`) để gợi ý quần/váy cho scan `upper_body`** | `POST /api/sizing/recommend` khi đọc từ bảng `body_measurements` chỉ `SELECT metric_key, value_cm` mà không đọc `source` và `capture_mode`. Vì bản ghi `upper_body` lưu cả `hip_cm = 94.1` (`source = "template_model"`), sau khi job trong RAM hết hạn, hệ thống lấy nhầm vòng mông mẫu để gợi ý size quần/váy. | - Định nghĩa `VALID_SIZING_SOURCES = {"photo_estimate", "photo_with_prior", "user_input"}` và hàm [`filter_valid_sizing_measurements`](file:///d:/MORPH-AI/backend/app/sizing.py#L71-L120).<br>- Loại bỏ hoàn toàn mọi chỉ số có `source in {"template_model", "unavailable"}` hoặc `<= 0` ở cả nhánh in-memory (`jobs`) lẫn nhánh SQLite (`body_measurements`).<br>- Đảm bảo scan `upper_body` luôn trả về `status = "insufficient_measurements"` (`missing = ["hip_cm"]`) cho sản phẩm cần vòng mông (`bottom` / `dress` có `hip_cm`), nhất quán 100% giữa RAM và DB. | - [`backend/app/sizing.py`](file:///d:/MORPH-AI/backend/app/sizing.py)<br>- [`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py)<br>- [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py)<br>- [`backend/tests/test_auth_and_history.py`](file:///d:/MORPH-AI/backend/tests/test_auth_and_history.py)<br>- [`backend/tests/test_sizing.py`](file:///d:/MORPH-AI/backend/tests/test_sizing.py)<br>- [`backend/tests/test_size_advice.py`](file:///d:/MORPH-AI/backend/tests/test_size_advice.py) |
| **3** | **Lịch sử scan (`GET /api/user/scans`) hiển thị `hip_cm` của mẫu 3D trong `key_measurements`** | `list_scans` trong `history.py` gộp tất cả các dòng `metric_key` vào `key_measurements` không phân biệt `source`. | - Lọc bỏ `source in ("template_model", "unavailable")` và giá trị `<= 0` khỏi `key_measurements` trong `list_scans` (giữ `null` là thiếu dữ liệu, không biến thành `0` và không đưa vào `BodyChart`). | - [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py)<br>- [`backend/tests/test_auth_and_history.py`](file:///d:/MORPH-AI/backend/tests/test_auth_and_history.py) |
| **4** | **Camera lấy ngẫu nhiên 1 frame đúng lúc `t = 0` và thiếu kiểm tra chất lượng khung hình / khoảng cách giữa 2 góc** | `CaptureSession.tsx` chỉ đếm số lần đứng yên rồi chụp đúng 1 frame tại thời điểm hết giờ (dễ dính frame bị rung đúng lúc `t=0`), chưa kiểm tra độ sáng/nhòe/thay đổi khoảng cách đứng giữa góc chính diện và góc nghiêng. | - Xây dựng [`frontend/lib/captureQuality.ts`](file:///d:/MORPH-AI/frontend/lib/captureQuality.ts) với bộ ngưỡng cấu hình được (`CAMERA_QUALITY_THRESHOLDS`).<br>- Kiểm tra độ sáng (`45..235`), độ nét Laplacian (`>= 14.0`), độ ổn định mốc giải phẫu (`motion < 0.018`), và độ lệch tỷ lệ khoảng cách đứng giữa 2 góc (`<= 18%`).<br>- Lưu `candidateBuffer` trong cửa sổ `1600ms` cuối của countdown và chọn frame có `frameQualityScore` cao nhất (`selectBestFrameFromWindow`).<br>- Hủy đếm ngược tức thì nếu mất điều kiện và hiển thị lý do tiếng Việt cụ thể.<br>- Bảo toàn tỷ lệ khung hình (`aspectRatioDelta < 0.002`, ma trận đồng nhất không méo/crop). | - [`frontend/lib/captureQuality.ts`](file:///d:/MORPH-AI/frontend/lib/captureQuality.ts)<br>- [`frontend/components/shop/CaptureSession.tsx`](file:///d:/MORPH-AI/frontend/components/shop/CaptureSession.tsx)<br>- [`frontend/components/shop/FitExperience.tsx`](file:///d:/MORPH-AI/frontend/components/shop/FitExperience.tsx)<br>- [`verification/scripts/test_capture_quality.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_quality.cjs) |
| **5** | **Thiếu metadata nguồn dữ liệu chi tiết trên từng chỉ số & chưa kiểm định lưới `.glb` xuất ra** | `report.py` chỉ trả về `key, label, value_cm, source` mà thiếu vùng quan sát, cờ hợp lệ cho sizing/tracking, cảnh báo chất lượng riêng và kiểm định hình học `.glb`. | - Nâng cấp [`measurement_report()`](file:///d:/MORPH-AI/backend/app/report.py) bổ sung `observed_region`, `valid_for_sizing`, `valid_for_tracking`, `quality_warnings`, `engine_version`, `uncertainty_cm: None`.<br>- Bổ sung [`validate_glb_mesh()`](file:///d:/MORPH-AI/backend/app/measurements.py) kiểm tra đơn vị mét, chiều cao khớp `height_cm / 100`, chân chạm mặt sàn `y ≈ 0`, không có đỉnh `NaN/Inf` hay mặt suy biến, và các vòng đo nằm đúng vị trí giải phẫu.<br>- Phân biệt rõ `detector_confidence` (`pose_visibility_mean`) với chất lượng ảnh và độ chính xác số đo. | - [`backend/app/report.py`](file:///d:/MORPH-AI/backend/app/report.py)<br>- [`backend/app/measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py)<br>- [`backend/app/reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py)<br>- [`backend/app/camera_fusion.py`](file:///d:/MORPH-AI/backend/app/camera_fusion.py)<br>- [`backend/tests/test_reconstruction.py`](file:///d:/MORPH-AI/backend/tests/test_reconstruction.py) |
| **6** | **Hiển thị kết quả scan cũ khi API quét mới bị lỗi & Câu chữ Auth nói sai về xử lý ảnh trên trình duyệt** | - `useBodyScan.ts` giữ nguyên `job` cũ nếu `POST /api/scans` thất bại.<br>- Trang đăng nhập/đăng ký ghi *"Xử lý hình ảnh trực tiếp trên trình duyệt"* trong khi thực tế gửi 2 ảnh về backend. | - Xóa `setJob(null)` ngay trước khi gửi `POST /api/scans` và xóa cache gợi ý size khi lỗi API để không bao giờ hiển thị kết quả cũ như kết quả mới.<br>- Cập nhật câu chữ tại `/auth/login`, `/auth/register` và `FitExperience.tsx` thống nhất với consent: ảnh chỉ gửi tới máy chủ khi người dùng đồng ý để dựng mô hình 3D, giữ tối đa 1 giờ (`RESULT_TTL_SECONDS = 3600`) và có thể xóa bất kỳ lúc nào.<br>- Bổ sung `JOB_PROCESSING_TIMEOUT_SECONDS = 120` và `MAX_STORED_JOBS = 50` trong `main.py`. | - [`frontend/lib/useBodyScan.ts`](file:///d:/MORPH-AI/frontend/lib/useBodyScan.ts)<br>- [`frontend/lib/ScanContext.tsx`](file:///d:/MORPH-AI/frontend/lib/ScanContext.tsx)<br>- [`frontend/app/auth/login/page.tsx`](file:///d:/MORPH-AI/frontend/app/auth/login/page.tsx)<br>- [`frontend/app/auth/register/page.tsx`](file:///d:/MORPH-AI/frontend/app/auth/register/page.tsx)<br>- [`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py) |
| **7** | **Nhấn phím `Escape` khi mở dropdown màu làm đóng luôn cả Wishlist Drawer & Cộng đôi số lượng giỏ hàng** | `CustomSelect.tsx` không chặn sự kiện `Escape` ở capture phase; `WishlistDrawer.tsx` gọi `addToCart` cộng dồn lần 2 khi bấm *"Tiếp tục đặt hàng"*. | - Bắt `Escape` ở capture phase trong `CustomSelect.tsx` (`stopImmediatePropagation`) và kiểm tra `e.defaultPrevented` trong `useDrawerA11y.ts`.<br>- Đồng bộ số lượng tuyệt đối (`isAbsolute = true`) trong `WishlistDrawer.tsx`. | - [`frontend/components/shop/CustomSelect.tsx`](file:///d:/MORPH-AI/frontend/components/shop/CustomSelect.tsx)<br>- [`frontend/lib/useDrawerA11y.ts`](file:///d:/MORPH-AI/frontend/lib/useDrawerA11y.ts)<br>- [`frontend/components/shop/WishlistDrawer.tsx`](file:///d:/MORPH-AI/frontend/components/shop/WishlistDrawer.tsx)<br>- [`verification/scripts/wishlist-escape-cart-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/wishlist-escape-cart-verification.cjs) |

---

## 2. Đối chiếu Baseline (Trước nâng cấp) và Kết quả Sau Thay Đổi

### 2.1. Chất lượng Hình học & Thuật toán 3 Tầng (Đánh giá trên tập kiểm thử hình học chuẩn)

| Hạng mục đánh giá | Baseline (Legacy v1) | Sau nâng cấp (3-Tier Calibrated v2) | Ý nghĩa kỹ thuật |
| :--- | :---: | :---: | :--- |
| **Độ trôi chiều cao tham chiếu `obs.height` (`upper_body`) khi tỷ lệ lưng $r_{\text{torso}} \in [0.26, 0.32]$** | `-9.38%` đến `+11.54%` (kéo theo lệch ngực `-8.6..+10.6 cm`) | **`-1.20%` đến `+1.20%`** (lệch ngực chỉ `-1.2..+1.2 cm`) | Kết hợp đa mỏ neo Đỉnh đầu $\rightarrow$ Vai (`0.195 H`) và Vai $\rightarrow$ Hông (`0.290 H`) qua hàm Huber/Tanh giới hạn biên độ. |
| **Độ méo tỷ lệ Độ sâu / Bề rộng ($D/W$) khi mốc hông góc nghiêng 90° trôi $\pm 10\%$** | `-7.73%` đến `+10.52%` | **`0.00%`** (bất biến tuyệt đối) | Khóa chung mẫu số quy đổi `shared_height = fuse_camera_scale(frontal, lateral)` và đồng bộ mặt phẳng quét ngang `aligned_torso_landmarks`. |
| **Sai số chu vi mặt cắt ngang (Uncalibrated Ellipse vs Anatomical Section, LOSO-CV 13 mẫu)** | Ngực: `6.19 cm`<br>Eo: `1.37 cm`<br>Mông: `6.70 cm` | Ngực: **`0.15 cm`** (`P95 = 0.40 cm`)<br>Eo: **`0.16 cm`** (`P95 = 0.42 cm`)<br>Mông: **`0.44 cm`** (`P95 = 1.11 cm`) | Bù trừ độ lõm giải phẫu mặt cắt ngang (`ANATOMICAL_SECTION_FACTORS`: Ngực `1.08074`, Eo `1.03209`, Mông `1.06234`). |
| **Sai số khớp lưới 3D `.glb` (`max_fit_error_cm` trên 6 dáng người chuẩn)** | `5.20 cm – 8.30 cm` (mô hình bị co ngang/sâu `~6.5%`) | **`0.00 cm`** (bảo toàn đồng thời chu vi và tỷ lệ $D/W$) | Khớp lưới PCHIP 4 vòng lặp điều chỉnh đồng thời hệ số ngang `factor_x` và hệ số sâu `factor_z`. |
| **Gợi ý size quần/váy từ scan `upper_body` đã lưu trong SQLite** | **SAI**: Dùng `hip_cm = 94.1 cm` của mẫu 3D để gợi ý size quần/váy | **ĐÚNG (`100%`)**: Trả về `insufficient_measurements` (`missing = ["hip_cm"]`) | Lọc nghiêm ngặt theo `VALID_SIZING_SOURCES`, loại bỏ `template_model` và `unavailable` ở cả RAM và SQLite. |

### 2.2. Chỉ số Thống kê trên Tập Đánh Giá Hình Học Độc Lập (`N = 10` Held-out Archetypes, tách biệt hoàn toàn với tập Calibration)

*(Lưu ý: Đây là kết quả đánh giá trên silhouette lượng tử hóa pixel nguyên có nhiễu tỷ lệ lưng $r_{\text{torso}} \in [0.26, 0.32]$, trôi mốc hông góc nghiêng $+4\%$ và nhiễu tọa độ mốc $\pm 1.5\text{ px}$ — **không phải** sai số trên người thật)*:

| Chế độ (`capture_mode`) | Chỉ số (`metric_key`) | Nguồn (`source`) | Độ bao phủ Sizing (`Coverage`) | MAE (cm) | Signed Bias (cm) | P90 Error (cm) | P95 Error (cm) | Repeatability SD (cm) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`full_body`** | `chest_cm` | `photo_estimate` | **100.0%** | **0.22** | -0.20 | 0.40 | 0.47 | 0.025 |
| **`full_body`** | `waist_cm` | `photo_estimate` | **100.0%** | **0.68** | +0.68 | 0.91 | 0.92 | 0.056 |
| **`full_body`** | `hip_cm` | `photo_estimate` | **100.0%** | **0.72** | -0.72 | 0.93 | 0.95 | 0.064 |
| **`full_body`** | `shoulder_width_cm` | `photo_estimate` | **100.0%** | **0.00** | +0.00 | 0.00 | 0.00 | 0.260 |
| **`upper_body`** | `chest_cm` | `photo_with_prior` | **100.0%** | **0.60** | -0.26 | 1.12 | 1.20 | 0.346 |
| **`upper_body`** | `waist_cm` | `photo_with_prior` | **100.0%** | **0.80** | +0.64 | 1.32 | 1.47 | 0.285 |
| **`upper_body`** | `hip_cm` | `template_model` | **0.0%** *(Chặn sizing)* | *N/A* | *N/A* | *N/A* | *N/A* | *N/A* |
| **`upper_body`** | `shoulder_width_cm` | `photo_with_prior` | **100.0%** | **0.24** | -0.02 | 0.50 | 0.50 | 0.287 |

---

## 3. Bằng chứng Kiểm thử Thực tế, Độ nhạy (Sensitivity) & Giới hạn Kỹ thuật

### 3.1. Báo cáo Ca Thất Bại & Nhiễu Thực Tế (Failure & Perturbation Matrix)
Bộ benchmark kiểm tra cả các trường hợp suy giảm chất lượng và vi phạm điều kiện chụp (`True Rejection Rate = 5/5 = 100.0%`, `False Acceptance Rate = 0.0%`):

1. **Độ nhạy với chiều cao tự nhập sai (`±5 cm` trên người cao `172 cm`, tương đương `±2.91%`)**:
   - Do toàn bộ chiều rộng và độ sâu pixel được quy đổi ra cm theo chiều cao tự nhập, việc nhập sai chiều cao `-5 cm` / `+5 cm` làm trôi tuyến tính các vòng đo: Ngực **`-2.3 / +2.4 cm`**, Eo **`-2.2 / +2.3 cm`**, Mông **`-3.0 / +2.9 cm`**, Rộng vai **`-0.9 / +0.9 cm`**.
2. **Độ nhạy với quần áo rộng / áo khoác dày (Silhouette phình `+6 px` mỗi bên thân)**:
   - MediaPipe Selfie Segmentation tách biên dạng ngoài của trang phục chứ không nhìn xuyên qua quần áo. Khi mặc áo khoác/đồ rộng làm phình `+6 px` mỗi bên, số đo ước lượng tăng giả tạo: Ngực **`+9.1 cm`**, Eo **`+8.7 cm`**, Mông **`+9.0 cm`** (tương đương lệch tăng `1` đến `1.5` bậc size).
3. **Các ca bị từ chối tự động kèm lý do cụ thể (`InvalidPhoto`)**:
   - **Góc nghiêng chưa đủ 90°** (xoay ~45°): Bị chặn ở cả `capture_feedback` và `reconstruct` (*"Xoay người thêm, gần 90° so với camera"*).
   - **Cơ thể chạm sát mép ảnh (`full_body`)**: Bị chặn (*"Ảnh chính diện: cơ thể chạm mép ảnh. Chụp lại để đủ đầu, tay và bàn chân."*).
   - **Đứng quá xa camera (`< 42%` chiều cao khung)**: Bị chặn (*"Ảnh chính diện: người quá nhỏ. Hãy tiến gần camera hơn."*).
   - **Ánh sáng quá tối (`mean < 25/255`) hoặc cháy sáng (`mean > 248/255`)**: Bị chặn ngay tại cổng đầu vào `observe()`.
   - **Thay đổi khoảng cách đứng cực đoan giữa 2 góc chụp (`> 45%`)**: Bị chặn tại `fuse_camera_scale()`.

### 3.2. Kết quả chạy toàn bộ các bộ Test tự động
- **Backend Unit & Integration Tests (`pytest backend/tests`)**: **`107 passed in 27.95s`** (bao gồm toàn bộ regression test cho `guest_token`, truy cập chéo giữa 2 user, parity giữa in-memory scan và DB scan, chặn `template_model` khỏi gợi ý size quần/váy, kiểm định `.glb`, và timeout job treo).
- **Frontend Capture Quality & Geometry Suite (`test_capture_quality.cjs`)**: **`16/16 checks PASSED`**.
- **Frontend TypeScript (`tsc --noEmit`)**: **`0 errors (PASSED)`**.
- **Backend & Frontend Regression Suites (`repro_reported_issues.py`, `regression_suite_auth_chart_checkout.py`, `wishlist-escape-cart-verification.cjs`, `regression_frontend_chart_checkout.cjs`)**: **`100% PASSED`**.

---

## 4. Cấu hình Phần cứng, Phiên bản Model & Cách chạy Benchmark

### 4.1. Cấu hình máy và Phiên bản Model đã đo kiểm
- **Hệ điều hành**: `Windows 10 (Build 10.0.26200) | AMD64`
- **Vi xử lý (CPU)**: `11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz` (`8` luồng logic, chạy thuần CPU với TFLite XNNPACK Delegate, `VRAM = 0.0 MB`)
- **Bộ nhớ hệ thống (RAM)**: `7.73 GB`
- **Môi trường Python**: `Python 3.11.17` (`D:\MORPH-AI\backend\.venv\Scripts\python.exe`)
- **Thư viện chính**: `mediapipe==0.10.35`, `trimesh==5.1.1`, `numpy==2.4.6`, `scipy==1.17.1`, `pillow==12.3.0`, `fastapi==0.143.0`
- **Phiên bản Engine & Tài nguyên Model**:
  - `ENGINE = "mediapipe-two-photo-fit-v4"`
  - `backend/models/pose_landmarker_full.task` (`8.96 MB`, SHA-256 prefix: `5134a3aad27a58b9`)
  - `backend/models/body-template.obj` (`1708.3 KB`, `13,380` đỉnh, `26,756` mặt tam giác, SHA-256 prefix: `8e761e6624b8f545`)

### 4.2. Hiệu năng thực tế trên cấu hình trên
- **Thuật toán toán học 3 tầng (Tier 1 + Tier 2 + Tier 3 PCHIP)**: `P50 = 5.90 ms`, `P95 = 13.40 ms` (`< 15 ms` mục tiêu).
- **Kiểm tra tư thế thời gian thực (`capture_feedback`)**: `P50 = 52.70 ms`, `P95 = 63.67 ms`.
- **Toàn trình dựng hình 3D & xuất `.glb` (`reconstruct` 2 ảnh)**: `P50 = 1338.54 ms` (`1.34 s`), `P95 = 1401.52 ms` (`1.40 s`), Throughput **`~45.1 scans/phút`** trên 1 worker CPU.
- **Bộ nhớ tiêu thụ**: Python Peak Heap `24.98 MB`, Process Working Set RSS `287.36 MB`.

### 4.3. Lệnh chạy lại toàn bộ Benchmark & Kiểm thử
```powershell
$env:PYTHONIOENCODING = "utf-8"

# 1. Chạy bộ Benchmark Product Readiness độc lập (xuất báo cáo console + JSON)
D:\MORPH-AI\backend\.venv\Scripts\python.exe D:\MORPH-AI\verification\scripts\benchmark_scan_product_readiness.py

# 2. Chạy Benchmark đối chiếu 3 tầng Before vs After
D:\MORPH-AI\backend\.venv\Scripts\python.exe D:\MORPH-AI\verification\scripts\evaluate_3d_scan_accuracy.py

# 3. Chạy toàn bộ 107 bài test Backend (pytest)
D:\MORPH-AI\backend\.venv\Scripts\python.exe -m pytest D:\MORPH-AI\backend\tests -q

# 4. Chạy bộ kiểm thử Chất lượng Camera & Hình học Frontend (16 checks)
C:\Program Files\nodejs\node.exe D:\MORPH-AI\verification\scripts\test_capture_quality.cjs

# 5. Kiểm tra TypeScript Frontend
C:\Program Files\nodejs\node.exe D:\MORPH-AI\frontend\node_modules\typescript\bin\tsc --project D:\MORPH-AI\frontend\tsconfig.json --noEmit
```

---

## 5. Điều kiện còn thiếu & Tiêu chuẩn Gating để mở Pilot với Người dùng thật

Mặc dù toàn bộ luồng phần mềm, bảo mật dữ liệu, kiểm soát chất lượng khung hình và thuật toán hình học đã được kiểm chứng tự động 100%, hệ thống **chưa được phép công bố độ chính xác nhân trắc học thực tế** cho đến khi hoàn thành **Giai đoạn Thu thập & Kiểm định trên Người thật** theo đúng quy trình tại [`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md):

1. **Thu thập Tập dữ liệu Người thật có Đồng ý (Informed Consent Cohort)**:
   - Tối thiểu **`N >= 30` tình nguyện viên** (`15` cá thể trong `calibration_split` và `15` cá thể hoàn toàn khác trong `evaluation_split`, kiểm tra bằng `verify_subject_disjoint_split`), đa dạng giới tính, BMI (`< 18.5`, `18.5–24.9`, `25.0–29.9`, `>= 30.0`), chiều cao (`150–188 cm`), trang phục (đồ ôm sát vs đồ thường ngày), và thiết bị (webcam laptop 720p/1080p + camera điện thoại).
2. **Đo chuẩn Vàng (Ground-Truth) theo ISO 8559-1:2017**:
   - Mỗi tình nguyện viên được đo độc lập bởi 2 kỹ thuật viên bằng thước dây không giãn tại 5 vị trí giải phẫu (Chiều cao đỉnh đầu, Rộng vai biacromial, Vòng ngực mesosternale, Vòng eo tự nhiên iliocristale, Vòng mông gluteal prominence), đảm bảo sai số kỹ thuật giữa người đo $\text{TEM} \le 0.5\text{ cm}$ (vòng đo) và $\le 0.4\text{ cm}$ (rộng vai).
3. **Ngưỡng Chấp nhận (Acceptance Gate) trên Tập Held-out `evaluation_split` để mở Pilot Gợi ý Size**:
   - **Vòng ngực (`chest_cm`)**: $\text{MAE} \le 2.5\text{ cm}$, $|\text{Bias}| \le 1.0\text{ cm}$, $\text{P90} \le 4.0\text{ cm}$, $\text{Repeatability SD} \le 1.2\text{ cm}$.
   - **Vòng eo (`waist_cm`)**: $\text{MAE} \le 2.5\text{ cm}$, $|\text{Bias}| \le 1.0\text{ cm}$, $\text{P90} \le 4.0\text{ cm}$, $\text{Repeatability SD} \le 1.2\text{ cm}$.
   - **Vòng mông (`hip_cm` — chỉ xét `full_body`)**: $\text{MAE} \le 2.8\text{ cm}$, $|\text{Bias}| \le 1.2\text{ cm}$, $\text{P90} \le 4.5\text{ cm}$, $\text{Repeatability SD} \le 1.4\text{ cm}$.
   - **Rộng vai (`shoulder_width_cm`)**: $\text{MAE} \le 1.8\text{ cm}$, $|\text{Bias}| \le 0.8\text{ cm}$, $\text{P90} \le 3.0\text{ cm}$.
   - **Tỷ lệ gợi ý trùng khớp bậc size chuẩn (Size Match Agreement Rate)**: $\ge 80\%$ trùng khớp chính xác bậc size thực tế của người mặc, và $0\%$ trường hợp gợi ý sai lệch quá 1 bậc size.
   - Sau khi đạt ngưỡng trên tập `evaluation_split`, mới được phép tính và hiển thị khoảng bất định thực nghiệm (`uncertainty_cm = ±1.96 * RMSE_empirical`) trên giao diện người dùng.
