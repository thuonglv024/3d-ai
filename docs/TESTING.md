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

### 3.1. Benchmark Product Readiness & Độ chính xác 3D Scan
```powershell
$env:PYTHONIOENCODING = "utf-8"
D:\MORPH-AI\backend\.venv\Scripts\python.exe D:\MORPH-AI\verification\scripts\benchmark_scan_product_readiness.py
D:\MORPH-AI\backend\.venv\Scripts\python.exe D:\MORPH-AI\verification\scripts\evaluate_3d_scan_accuracy.py
```
- Đo đầy đủ MAE, Bias, P90/P95, Repeatability SD, Coverage, 10 kịch bản nhiễu/thất bại (`True Rejection Rate = 100%`), kiểm tra tách tập hiệu chỉnh/đánh giá theo `subject_id`, Latency P50/P95 & RAM, và đánh giá gợi ý size trên toàn bộ 160 sản phẩm (xem báo cáo tại [`SCAN_PRODUCT_READINESS.md`](file:///d:/MORPH-AI/SCAN_PRODUCT_READINESS.md) và quy trình đo thực tế tại [`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md)).

### 3.2. Kiểm thử nhanh pipeline `upper_body` với fixture chuẩn
```powershell
$env:PYTHONIOENCODING = "utf-8"
D:\MORPH-AI\backend\.venv\Scripts\python.exe D:\MORPH-AI\verification\scripts\check-upper.py
```
- Sử dụng cặp ảnh fixture [`verification/scripts/qa/upper-front.png`](file:///d:/MORPH-AI/verification/scripts/qa/upper-front.png) và [`verification/scripts/qa/upper-side.png`](file:///d:/MORPH-AI/verification/scripts/qa/upper-side.png) để kiểm tra toàn trình dựng hình 3D và trích xuất JSON số đo.

### 3.3. Kiểm thử hồi quy Backend (Auth, Guest Token, Checkout)
```powershell
D:\MORPH-AI\backend\.venv\Scripts\python.exe D:\MORPH-AI\verification\scripts\repro_reported_issues.py
D:\MORPH-AI\backend\.venv\Scripts\python.exe D:\MORPH-AI\verification\scripts\regression_suite_auth_chart_checkout.py
```

### 3.4. Kiểm thử Frontend TypeScript, Chất lượng Camera & Logic Hồi quy
```powershell
C:\Program Files\nodejs\node.exe D:\MORPH-AI\frontend\node_modules\next\dist\bin\next typegen
C:\Program Files\nodejs\node.exe D:\MORPH-AI\frontend\node_modules\typescript\bin\tsc --project D:\MORPH-AI\frontend\tsconfig.json --noEmit
C:\Program Files\nodejs\node.exe D:\MORPH-AI\verification\scripts\test_capture_quality.cjs
C:\Program Files\nodejs\node.exe D:\MORPH-AI\verification\scripts\wishlist-escape-cart-verification.cjs
C:\Program Files\nodejs\node.exe D:\MORPH-AI\verification\scripts\regression_frontend_chart_checkout.cjs
```

### 3.5. Kịch bản E2E Playwright (Yêu cầu đang chạy Backend `:8000` và Frontend `:3000`)
Các script `.cjs` trong [`verification/scripts/`](file:///d:/MORPH-AI/verification/scripts) phục vụ kiểm thử giao diện tự động khi cần:
- [`camera-flow-ui.cjs`](file:///d:/MORPH-AI/verification/scripts/camera-flow-ui.cjs), [`camera-layout-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/camera-layout-verification.cjs) & [`overlay-camera-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/overlay-camera-verification.cjs): Kiểm thử luồng webcam tự động (kèm hướng dẫn thoại/overlay) dùng fake media stream từ ảnh trong `verification/scripts/qa/`.
- [`upper-ui.cjs`](file:///d:/MORPH-AI/verification/scripts/upper-ui.cjs): Kiểm thử giao diện `/scan` và dark measurement workspace.
- [`commerce-ui.cjs`](file:///d:/MORPH-AI/verification/scripts/commerce-ui.cjs) & [`popups-ui-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/popups-ui-verification.cjs): Kiểm thử trang chi tiết sản phẩm, custom dropdown, bảng chọn size và giỏ hàng.
- [`catalog-e2e-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/catalog-e2e-verification.cjs), [`storefront-multi-product-ui.cjs`](file:///d:/MORPH-AI/verification/scripts/storefront-multi-product-ui.cjs) & [`product-images-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/product-images-verification.cjs): Kiểm thử trang chủ, bộ lọc 160 sản phẩm, ảnh sản phẩm và tìm kiếm.
- [`auth-scan-chart-size-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/auth-scan-chart-size-verification.cjs), [`auth-a11y-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/auth-a11y-verification.cjs) & [`profile-verification.cjs`](file:///d:/MORPH-AI/verification/scripts/profile-verification.cjs): Kiểm thử đăng ký, đăng nhập, lưu phiên quét, hồ sơ số đo và biểu đồ `BodyChart` (cùng helper seed [`seed_test_scans.py`](file:///d:/MORPH-AI/verification/scripts/seed_test_scans.py) và [`seed_demo_scans.py`](file:///d:/MORPH-AI/verification/scripts/seed_demo_scans.py)).
- [`review-ui.cjs`](file:///d:/MORPH-AI/verification/scripts/review-ui.cjs): Kịch bản chụp ảnh màn hình audit giao diện theo yêu cầu.

---

## 4. Quy tắc quản lý Fixture và Artifact Kiểm thử

1. **Giữ nguyên Fixture (`verification/scripts/qa/`)**:
   - 4 file ảnh PNG trong [`verification/scripts/qa/`](file:///d:/MORPH-AI/verification/scripts/qa) (`rendered-front.png`, `rendered-side.png`, `upper-front.png`, `upper-side.png`) là dữ liệu đầu vào cố định cho các script kiểm thử tự động. **Tuyệt đối không xóa.**
2. **Không commit Artifact sinh tự động**:
   - Các thư mục ảnh chụp màn hình và báo cáo tạm sinh ra khi chạy Playwright (`output/playwright/`, `verification/review-*/`, `verification/quality_gate_screenshots/`, `verification/*.png`, `verification/*.json`) đã được đưa vào [`.gitignore`](file:///d:/MORPH-AI/.gitignore) để giữ kho mã nguồn sạch gọn.
   - Sau khi chạy kiểm thử giao diện có sinh ảnh chụp màn hình, dọn dẹp các file tạm trước khi bàn giao.

---

## 5. Lịch sử Nghiệm thu Hệ thống (Historical Verification Milestones)

- **Đợt 1 (10/10 – 12/10/2026)**:
  - Nghiệm thu giao diện Luxury Editorial (**Warm Ivory & Champagne Gold**) và **Dark Measurement Workspace** (`#141312`).
  - Nghiệm thu luồng Camera-Only tự động chụp 2 góc (`upper_body` mặc định & `full_body` tùy chọn), danh mục 160 sản phẩm (80 Nam / 80 Nữ), luồng đặt hàng `/checkout` $\rightarrow$ `/orders/[id]` và tài khoản `/account` + `BodyProfile`.
- **Đợt 2 (13/10 – 14/10/2026)**:
  - Khắc phục và kiểm thử hồi quy 3 lỗi trọng yếu: bắt buộc kiểm tra `guest_token` bằng `secrets.compare_digest` cho phiên quét khách (`403 Forbidden` khi thiếu/sai token), chống cộng đôi số lượng khi chuyển sản phẩm từ Wishlist sang Giỏ hàng, và ngăn phím `Escape` trong `CustomSelect` đóng nhầm `WishlistDrawer`.
  - Triển khai và benchmark **Pipeline Tối ưu hóa 3D Body Scan 3 Tầng**: giảm sai số `obs.height` xuống $\le \pm 1.20\%$, bảo toàn tỷ lệ $D/W$ (`0.00%` sai lệch trước nhiễu mốc hông góc nghiêng), hiệu chuẩn chu vi giải phẫu (`max_fit_error_cm = 0.00 cm` trên 6 dáng người) với thời gian xử lý lõi `~9.67 ms` (`< 15 ms`), đạt **95/95 bài kiểm thử `pytest` PASS**.

