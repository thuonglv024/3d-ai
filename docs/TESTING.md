# Hướng Dẫn Kiểm Thử & Bộ Kịch Bản QA (Testing & Verification)

Tài liệu này mô tả cấu trúc kiểm thử hiện tại của **MORPH AI**, phân biệt rõ giữa **mã nguồn kiểm thử tự động / fixture đang sử dụng** và **artifact kiểm thử sinh ra theo phiên** (log, screenshot, báo cáo lịch sử).

---

## 1. Cấu trúc kiểm thử tổng quan

| Nhóm kiểm thử | Vị trí | Công cụ | Mục đích |
| :--- | :--- | :--- | :--- |
| **Backend Unit & Integration Tests** | [`backend/tests/`](file:///d:/MORPH-AI/backend/tests) | `pytest`, `fastapi.testclient` | Kiểm thử API, xác thực, giỏ hàng/đặt hàng, catalog, khôi phục 3D, số đo giải phẫu và tư vấn kích cỡ (95 tests). |
| **3D Scan Accuracy Benchmark** | [`verification/scripts/evaluate_3d_scan_accuracy.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_3d_scan_accuracy.py) | Python, `trimesh`, `numpy`, `scipy` | Đo kiểm định lượng Pipeline 3 tầng (Multi-Anchor Height, Camera Scale Fusion, Anatomical Calibration & PCHIP Fit) kèm thời gian xử lý (`< 15 ms`). |
| **Backend Regression & Security Suites** | [`verification/scripts/repro_reported_issues.py`](file:///d:/MORPH-AI/verification/scripts/repro_reported_issues.py), [`verification/scripts/regression_suite_auth_chart_checkout.py`](file:///d:/MORPH-AI/verification/scripts/regression_suite_auth_chart_checkout.py), [`verification/scripts/check-upper.py`](file:///d:/MORPH-AI/verification/scripts/check-upper.py) | Python | Kiểm thử lỗ hổng `guest_token`, rate-limit đăng nhập, claim scan idempotent, trừ kho nguyên tử (`BEGIN IMMEDIATE;`), `Idempotency-Key` và pipeline `upper_body`. |
| **Frontend Static & Build Checks** | [`frontend/package.json`](file:///d:/MORPH-AI/frontend/package.json) | `tsc --noEmit`, `next build` | Kiểm tra kiểu dữ liệu TypeScript và biên dịch production bundle. |
| **Frontend / E2E Playwright Scripts** | [`verification/scripts/*.cjs`](file:///d:/MORPH-AI/verification/scripts) | Node.js, Playwright | Kiểm thử luồng camera tự động, cửa hàng 160 sản phẩm, Wishlist/Cart, BodyChart, Auth và đặt hàng. |
| **Synthetic QA Image Fixtures** | [`verification/scripts/qa/`](file:///d:/MORPH-AI/verification/scripts/qa) | PNG tĩnh | Ảnh giả lập mannequin chuẩn dùng làm đầu vào cho bài test tự động (**BẮT BUỘC GIỮ NGUYÊN**). |

---

## 2. Chạy bộ kiểm thử Backend (`pytest` — 107 tests)

Luôn sử dụng Python trong môi trường ảo của dự án (`backend/.venv/Scripts/python.exe`), không dùng alias Python của Windows Store:

```powershell
D:\MORPH-AI\backend\.venv\Scripts\python.exe -m pytest D:\MORPH-AI\backend\tests -q
```

### Danh sách các file test trong [`backend/tests/`](file:///d:/MORPH-AI/backend/tests):
1. **[`test_api.py`](file:///d:/MORPH-AI/backend/tests/test_api.py)**:
   - Kiểm tra `/api/health`, danh mục sản phẩm, kích cỡ, vòng đời phiên quét `/api/scans`, giới hạn `MAX_STORED_JOBS = 50` và giải phóng job treo (`JOB_PROCESSING_TIMEOUT_SECONDS = 120`).
   - Kiểm tra bảo mật `guest_token`: truy cập `GET /api/scans/{id}`, `/measurements`, `/model`, `/size-advice`, `DELETE /api/scans/{id}` khi thiếu hoặc sai token đều bị chặn `403 Forbidden`, và ẩn `guest_token` khi scan thuộc về user đã đăng nhập.
2. **[`test_auth_and_history.py`](file:///d:/MORPH-AI/backend/tests/test_auth_and_history.py)**:
   - Đăng ký, đăng nhập, đăng xuất, khóa tài khoản tạm thời khi sai mật khẩu quá 5 lần (`429 Too Many Requests`).
   - Lưu phiên quét khách vào tài khoản (`POST /api/user/scans/save`) có kiểm tra `guest_token` bằng `secrets.compare_digest`, xóa `guest_token` cũ sau khi claim và chống lưu trùng lặp.
   - Kiểm tra parity 100% giữa gợi ý size từ job trong RAM và bản lưu trong SQLite (`body_scans`), đảm bảo scan `upper_body` đã lưu với `hip_cm` có `source = "template_model"` trả về `insufficient_measurements` cho quần/váy.
3. **[`test_camera_fusion.py`](file:///d:/MORPH-AI/backend/tests/test_camera_fusion.py)**:
   - Kiểm thử Tầng 2 ([`camera_fusion.py`](file:///d:/MORPH-AI/backend/app/camera_fusion.py)): đồng bộ mốc giải phẫu `aligned_torso_landmarks`, khóa tỷ lệ quy đổi chung `fuse_camera_scale`, kiểm định chênh lệch khoảng cách đứng `assess_cross_view_quality` và bảo toàn tỷ lệ $D/W$ (`0.00%` sai lệch).
4. **[`test_catalog_db.py`](file:///d:/MORPH-AI/backend/tests/test_catalog_db.py)**:
   - Kiểm tra seed 160 sản phẩm (80 Nam, 80 Nữ, 10 danh mục $\times$ 8 sản phẩm), bảng size, biến thể màu/tồn kho và bộ lọc tìm kiếm.
5. **[`test_orders.py`](file:///d:/MORPH-AI/backend/tests/test_orders.py)**:
   - Kiểm tra đặt hàng `POST /api/orders`, chuẩn hóa số điện thoại Việt Nam, trừ tồn kho nguyên tử (`BEGIN IMMEDIATE;`), chống đặt vượt tồn kho (`400 Bad Request` + rollback), chống trùng đơn qua `Idempotency-Key` (`409 Conflict` nếu khác payload) và phân quyền xem đơn hàng (`order_token` / chủ đơn).
6. **[`test_photo_measurements.py`](file:///d:/MORPH-AI/backend/tests/test_photo_measurements.py)** & **[`test_measurements.py`](file:///d:/MORPH-AI/backend/tests/test_measurements.py)**:
   - Kiểm thử Tầng 3 ([`measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py)): hệ số hiệu chuẩn giải phẫu `ANATOMICAL_SECTION_FACTORS`, `anatomical_perimeter`, `estimate_from_profiles`, `fit_measurement_targets` và kiểm định lưới `.glb` (`validate_glb_mesh`).
7. **[`test_size_advice.py`](file:///d:/MORPH-AI/backend/tests/test_size_advice.py)** & **[`test_sizing.py`](file:///d:/MORPH-AI/backend/tests/test_sizing.py)**:
   - Kiểm thử thuật toán gợi ý size theo từng nhóm trang phục (`top`, `bottom`, `dress`, `outerwear`), lọc bỏ `template_model` / `unavailable` / `<= 0` qua `filter_valid_sizing_measurements`, và xử lý biên giữa 2 size.
8. **[`test_upper_body.py`](file:///d:/MORPH-AI/backend/tests/test_upper_body.py)**, **[`test_capture.py`](file:///d:/MORPH-AI/backend/tests/test_capture.py)**, **[`test_reconstruction.py`](file:///d:/MORPH-AI/backend/tests/test_reconstruction.py)** & **[`test_images.py`](file:///d:/MORPH-AI/backend/tests/test_images.py)**:
   - Kiểm thử Tầng 1 ([`reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py)): hàm `estimate_upper_body_height` đa mỏ neo, độ nhạy với chiều cao nhập lệch $\pm 5\text{ cm}$ / trang phục dày / góc xoay lệch, và kiểm tra đầy đủ metadata provenance trong [`report.py`](file:///d:/MORPH-AI/backend/app/report.py).

---

## 3. Chạy các kịch bản kiểm thử chuyên biệt trong `verification/scripts/`

### 3.1. Benchmark Product Readiness, API/Load & Kiểm định Khoảng Dự Đoán Split Conformal
```powershell
$env:PATHEXT = ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL"
$env:PYTHONIOENCODING = "utf-8"
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\benchmark_scan_api_and_load.py"
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\evaluate_human_validation_cohort.py"
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\benchmark_scan_product_readiness.py"
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\evaluate_3d_scan_accuracy.py"
```
- **[`benchmark_scan_api_and_load.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_api_and_load.py)**: Tách riêng benchmark hàm `reconstruct()` (Cold Start vs Warm Start) với toàn trình API (`POST /api/capture-check`, `POST /api/scans` upload, `queue_wait_ms`, `worker_processing_ms`, tải `.glb` và render WebGL trên Chromium), chạy tải đồng thời có giới hạn (`Concurrency = 1, 2, 4, 10`) và đo tách biệt bộ nhớ `OS Working Set RSS` vs `Python Heap (tracemalloc)`.
- **[`evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py)** & **[`benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py)**: Kiểm định tách tập hiệu chỉnh/đánh giá theo `subject_id`, hiệu chuẩn khoảng dự đoán **Split Conformal Prediction / Empirical Residual Quantiles** (đánh giá coverage & độ rộng theo metric, mode và nhóm dữ liệu độc lập), 10 kịch bản nhiễu/từ chối và gợi ý size trên 160 sản phẩm (xem [`SCAN_PRODUCT_READINESS.md`](file:///d:/MORPH-AI/SCAN_PRODUCT_READINESS.md) và [`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md)).

### 3.2. Kiểm thử nhanh pipeline `upper_body` với fixture chuẩn
```powershell
$env:PYTHONIOENCODING = "utf-8"
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\check-upper.py"
```
- Sử dụng cặp ảnh fixture [`verification/scripts/qa/upper-front.png`](file:///d:/MORPH-AI/verification/scripts/qa/upper-front.png) và [`verification/scripts/qa/upper-side.png`](file:///d:/MORPH-AI/verification/scripts/qa/upper-side.png) để kiểm tra toàn trình dựng hình 3D và trích xuất JSON số đo.

### 3.3. Kiểm thử hồi quy Backend (Auth, Guest Token, Checkout)
```powershell
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\repro_reported_issues.py"
& "D:\MORPH-AI\backend\.venv\Scripts\python.exe" "D:\MORPH-AI\verification\scripts\regression_suite_auth_chart_checkout.py"
```

### 3.4. Kiểm thử Frontend TypeScript, Chất lượng Camera, Browser E2E `CaptureSession` & Logic Hồi quy
```powershell
& "C:\Program Files\nodejs\node.exe" "D:\MORPH-AI\frontend\node_modules\next\dist\bin\next" typegen
& "C:\Program Files\nodejs\node.exe" "D:\MORPH-AI\frontend\node_modules\typescript\bin\tsc" --project "D:\MORPH-AI\frontend\tsconfig.json" --noEmit
& "C:\Program Files\nodejs\node.exe" "D:\MORPH-AI\verification\scripts\test_capture_quality.cjs"
& "C:\Program Files\nodejs\node.exe" "D:\MORPH-AI\verification\scripts\test_capture_session_e2e.cjs"
& "C:\Program Files\nodejs\node.exe" "D:\MORPH-AI\verification\scripts\wishlist-escape-cart-verification.cjs"
& "C:\Program Files\nodejs\node.exe" "D:\MORPH-AI\verification\scripts\regression_frontend_chart_checkout.cjs"
```
- **[`test_capture_session_e2e.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_session_e2e.cjs)**: Thực thi trực tiếp `CaptureSession` trên trình duyệt Chromium với luồng camera xác định (`canvas.captureStream(30)`), kiểm chứng 8 kịch bản hành vi thực tế (hủy countdown khi mất điều kiện, chọn đúng frame có `frameQualityScore` cao nhất trong cửa sổ `1600ms` qua giải mã JPEG gửi lên `POST /api/scans`, chuyển `front → turn → side`, chặn lệch khoảng cách giữa 2 góc, đổi thiết bị camera, mất kết nối giữa chừng, đóng phiên và retry).

### 3.5. Các kịch bản E2E Playwright bổ trợ trong `verification/scripts/`
- [`camera-flow-ui.cjs`](file:///d:/MORPH-AI/verification/scripts/camera-flow-ui.cjs), [`camera-layout-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/camera-layout-verification.cjs) & [`overlay-camera-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/overlay-camera-verification.cjs): Kiểm thử giao diện luồng webcam và overlay.
- [`upper-ui.cjs`](file:///d:/MORPH-AI/verification/scripts/upper-ui.cjs): Kiểm thử giao diện `/scan` và dark measurement workspace.
- [`commerce-ui.cjs`](file:///d:/MORPH-AI/verification/scripts/commerce-ui.cjs) & [`popups-ui-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/popups-ui-verification.cjs): Kiểm thử trang chi tiết sản phẩm, custom dropdown, bảng chọn size và giỏ hàng.
- [`catalog-e2e-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/catalog-e2e-verification.cjs), [`storefront-multi-product-ui.cjs`](file:///d:/MORPH-AI/verification/scripts/storefront-multi-product-ui.cjs) & [`product-images-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/product-images-verification.cjs): Kiểm thử trang chủ, bộ lọc 160 sản phẩm, ảnh sản phẩm và tìm kiếm.
- [`auth-scan-chart-size-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/auth-scan-chart-size-verification.cjs), [`auth-a11y-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/auth-a11y-verification.cjs) & [`profile-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/profile-verification.cjs): Kiểm thử đăng ký, đăng nhập, lưu phiên quét, hồ sơ số đo và biểu đồ `BodyChart`.

---

## 4. Quy tắc quản lý Fixture và Lưu trữ Artifact theo Run ID

1. **Giữ nguyên Fixture (`verification/scripts/qa/`)**:
   - 4 file ảnh PNG trong [`verification/scripts/qa/`](file:///d:/MORPH-AI/verification/scripts/qa) (`rendered-front.png`, `rendered-side.png`, `upper-front.png`, `upper-side.png`) là dữ liệu đầu vào cố định cho các script kiểm thử tự động. **Tuyệt đối không xóa.**
2. **Lưu trữ Log / Screenshot / Báo cáo theo Run ID (`output/runs/<run-id>/`)**:
   - Toàn bộ bằng chứng thực thi của từng đợt nghiệm thu được lưu theo mã Run ID tại `output/runs/<run-id>/` (ví dụ [`output/runs/run-20261014-v2/`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/) gồm `capture-e2e/`, `benchmark/`, `validation/`, `integration/`).
   - Không xóa toàn bộ thư mục `output/` để bảo toàn bằng chứng đối chiếu giữa các lần chạy; thư mục `output/runs/` đã được cấu hình trong [`.gitignore`](file:///d:/MORPH-AI/.gitignore) để không đẩy file nhị phân/log lớn lên Git.

---

## 5. Lịch sử Nghiệm thu Hệ thống (Historical Verification Milestones)

- **Đợt 1 (10/10 – 12/10/2026)**:
  - Nghiệm thu giao diện Luxury Editorial (**Warm Ivory & Champagne Gold**) và **Dark Measurement Workspace** (`#141312`).
  - Nghiệm thu luồng Camera-Only tự động chụp 2 góc (`upper_body` mặc định & `full_body` tùy chọn), danh mục 160 sản phẩm (80 Nam / 80 Nữ), luồng đặt hàng `/checkout` $\rightarrow$ `/orders/[id]` và tài khoản `/account` + `BodyProfile`.
- **Đợt 2 (13/10 – 14/10/2026, Run ID `run-20261014-v2`)**:
  - **Implementation & Security Verification**: Đạt `107/107` tests `pytest`, `16/16` unit checks `test_capture_quality.cjs`, `8/8` kịch bản hành vi trình duyệt `test_capture_session_e2e.cjs`, và `0` lỗi TypeScript.
  - **Synthetic / Geometric & Conformal Validation**: Đánh giá trên tập tách biệt theo `subject_id` (`N_cal = 12` subjects / `36` scans, `N_eval = 10` subjects / `30` scans), thay thế `±1.96 × RMSE` bằng khoảng dự đoán **Split Conformal Prediction / Empirical Residual Quantiles**, kiểm tra 10 kịch bản nhiễu/từ chối và 160 sản phẩm catalog.
  - **API Lifecycle & Bounded Concurrent Load Test**: Đo tách biệt Cold/Warm start in-process `reconstruct()`, toàn trình HTTP API + WebGL render, chạy tải đồng thời `Concurrency = 1, 2, 4, 10` (`MAX_ACTIVE_JOBS = 8`), và đo tách biệt `OS Working Set RSS` với `Python Heap (tracemalloc)`.
  - **Real-Human Anthropometric Accuracy**: Ghi nhận trung thực trạng thái `MISSING_EMPIRICAL_COHORT` (`N_human = 0`); chưa nghiệm thu độ chính xác trên người thật cho tới khi có tập dữ liệu thực nghiệm có đồng ý sử dụng.


