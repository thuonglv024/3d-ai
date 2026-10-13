# MORPH AI — Body Profile, Measurement History & Scan Comparison Handoff

**Ngày hoàn thành**: 13/10/2026  
**Phạm vi**: Frontend Account & Body Profile Module (`frontend/app/account/`, `BodyChart.tsx`, `ScanCompareModal.tsx`, `userScansApi.ts`, `account.css`)  
**Tác giả**: Agent FE Profile  

---

## 1. Tổng quan Kiến trúc & Thành phần Đã Triển khai

### 1.1 Trang Hồ sơ Tổng quan (`frontend/app/account/page.tsx`)
- **Quản lý Thông tin Cá nhân**:
  - Avatar viết tắt họ tên / email, Email hiển thị dạng thẻ bảo mật.
  - Tên hiển thị hỗ trợ chỉnh sửa inline trực tiếp, lưu tức thì qua `PATCH /api/auth/profile` với xử lý lỗi mạng và phản hồi UX mượt mà.
- **Tùy chọn Cài đặt Lưu trữ**:
  - Toggle switch "Tự động lưu kết quả scan sau khi quét xong" (`auto_save_scans`).
  - Đồng bộ hóa thời gian thực với backend, có toast thông báo trạng thái.
- **Khối Thống kê & Điều hướng**:
  - Đếm tổng số lần scan đã lưu và hiển thị mốc thời gian lần scan gần nhất.
  - Featured Banner liên kết trực tiếp tới "Hồ sơ hình thể & Biểu đồ số đo" (`/account/body-profile`).
  - Nút CTA quét hình thể mới (`/scan`) và nút Đăng xuất an toàn.
- **Bảo vệ Trạng thái Đăng nhập (Auth Guard)**:
  - Khi chưa đăng nhập: Giao diện thẻ Warm Ivory & Champagne Gold thân thiện, mời người dùng đăng nhập/đăng ký hoặc trải nghiệm thử không cần tài khoản.

---

### 1.2 Trang Hồ sơ Hình thể & Biểu đồ (`frontend/app/account/body-profile/page.tsx`)
- **Phần 1 — Hero Card (Số đo gần nhất)**:
  - Hiển thị bộ số đo mới nhất: Chiều cao (Bạn nhập), Vòng ngực, Vòng eo, Vòng mông, Rộng vai kèm nhãn nguồn gốc số đo chuẩn xác (`user_input`, `photo_with_prior`, `photo_estimate`, `template_model`).
  - **Minh bạch thời gian**: Banner ghi rõ ngày giờ chụp thực tế (`captured_at`), chế độ chụp (Thân trên / Toàn thân), phiên bản engine. **Tuyệt đối không ghép nối số đo từ các ngày khác nhau thành một bộ mà không ghi rõ thời gian!**
  - Chế độ thân trên (`upper_body`): Vòng mông hiển thị nhãn "Chưa đo (Thân trên)" kèm nguồn `Theo mẫu 3D`, không ngụy tạo số đo camera.
  - Toggle nhanh cài đặt "Tự lưu kết quả scan tiếp theo".
- **Phần 2 — Biểu đồ Thay đổi Số đo theo Thời gian (`frontend/components/shop/BodyChart.tsx`)**:
  - 100% SVG thuần, render tương tác mượt mà, loại bỏ mọi xung đột thư viện với React 19.
  - Trục X: Thời gian scan thực tế (phân biệt rõ giờ:phút cho nhiều lần scan trong cùng một ngày).
  - Trục Y: Số đo (cm) với lưới phân vạch và tỷ lệ động.
  - Chọn metric hiển thị: Ngực (`#9E6D38`, ●), Eo (`#8F4A14`, ■), Mông (`#1A5B80`, ◆), Rộng vai (`#196347`, ▲). Đáp ứng chuẩn tương phản WCAG AA (> 5:1) và phân biệt bằng cả màu sắc lẫn ký hiệu hình học.
  - Bộ lọc thời gian: "30 ngày", "90 ngày", "Toàn bộ".
  - **Xử lý dữ liệu trung thực**: Nếu giá trị là `null` hoặc `template_model`, đường SVG tự động ngắt quãng tạo khoảng trống; KHÔNG biến thành số 0; KHÔNG vẽ biến thiên giả mạo từ mẫu MakeHuman. Nếu chỉ có 1 lần scan, hiển thị 1 điểm duy nhất.
  - Floating Tooltip: Hiển thị ngày giờ scan, số đo cm, nhãn nguồn, chế độ chụp và nút mở chi tiết lần scan.
  - Bảng số đo tương đương (Accessible Data Table) có thể mở bên dưới cho người dùng đọc số đo trực tiếp hoặc sử dụng screen reader.
  - Chú thích công nghệ bắt buộc đi kèm biểu đồ.
- **Phần 3 — Danh sách Lịch sử Scan & Bộ chọn So sánh**:
  - Danh sách thẻ scan với ngày giờ, chế độ chụp, phiên bản engine, các số đo chính và ghi chú người dùng.
  - Hỗ trợ chọn tối đa 2 lần scan bất kỳ bằng checkbox:
    - Khi chọn 1 lần: Thanh thông báo nổi hướng dẫn chọn thêm 1 lần nữa.
    - Khi chọn 2 lần: Nút "So sánh 2 lần scan" kích hoạt, mở `ScanCompareModal`.
  - Nút "Xem chi tiết", nút "Sửa ghi chú" (modal chỉnh sửa nhanh), nút "Xóa" (kèm modal xác nhận, xóa thất bại giữ nguyên dữ liệu và thông báo lỗi).
- **Trạng thái Trống (Empty State)**:
  - Khi chưa có scan: Minh họa tối giản, thông điệp hướng dẫn và nút "Bắt đầu scan ngay".

---

### 1.3 Trang Chi tiết Lần Scan (`frontend/app/account/body-profile/scans/[id]/page.tsx`)
- Breadcrumbs phân cấp: `Trang chủ / Tài khoản / Hồ sơ hình thể / Chi tiết lần scan`.
- Metadata 4 cột: Thời gian chụp (`captured_at`), Thời gian lưu (`saved_at`), Chế độ chụp (`capture_mode`), Phiên bản Engine (`engine_version`).
- Bảng số đo toàn diện kèm cột Nguồn số đo (`user_input`, `photo_estimate`, `photo_with_prior`, `template_model`) và giải thích phương pháp đo.
- Cảnh báo công nghệ được ghi nhận trong phiên scan (nếu có).
- Hộp chỉnh sửa ghi chú cá nhân (lưu ngữ cảnh đo như "Đo sau tập gym", "Đo buổi sáng").
- Nút "So sánh với lần scan trước đó" (tự động phát hiện lần scan liền kề và mở modal đối chiếu).
- Nút "Xóa bản ghi này" (xác nhận xong chuyển hướng về `/account/body-profile`).

---

### 1.4 Modal Đối Chiếu Hai Lần Scan (`frontend/components/shop/ScanCompareModal.tsx`)
- Gọi API `/api/user/scans/compare?scan_a={id1}&scan_b={id2}`.
- Hiển thị hai thẻ tóm tắt phiên scan trước / sau (thời gian, chế độ, engine, ghi chú).
- Cảnh báo không tương thích rõ ràng khi hai lần scan khác chế độ chụp (`upper_body` vs `full_body`) hoặc khác phiên bản engine.
- Bảng đối chiếu chi tiết từng số đo:
  - Giá trị cũ, Giá trị mới, Chênh lệch có dấu (`+0.5 cm`, `-0.8 cm`, `0 cm`, hoặc `Không đối chiếu`).
  - **Câu văn so sánh toán học trung tính**: Ví dụ *"Eo thay đổi -0.8 cm giữa hai lần ước lượng."* **Tuyệt đối không đưa ra kết luận giảm béo, tăng cơ hay chẩn đoán sức khỏe.**
- Chú thích minh bạch về tính chất ước lượng của thị giác máy tính.

---

### 1.5 Định kiểu & Thiết kế (`frontend/app/account/account.css`)
- Tuân thủ bảng màu Warm Ivory (`#FAF7F0`) & Champagne Gold (`#C6A15B`), text `#26211A`, nền thẻ `#FFFFFF`, viền `#E5DEC9`.
- Bo góc phân cấp: 24px cho container/hero, 18px cho card, 12px cho controls, 9999px cho pills.
- Đổ bóng mềm nhẹ sang trọng (`0 12px 36px -4px rgba(198, 161, 91, 0.12)`).
- Đầy đủ responsive: máy tính bảng, màn hình nhỏ và thiết bị di động (< 640px).

---

## 2. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Typecheck Frontend**:
   ```powershell
   npm --prefix frontend run typecheck
   ```
   *Kết quả*: **Exit Code 0** (0 errors).

2. **Next.js Production Build**:
   ```powershell
   npm --prefix frontend run build
   ```
   *Kết quả*: **Exit Code 0** — Biên dịch thành công 31/31 routes, tối ưu hóa bundle tĩnh & động hoàn hảo.
   - `○ /account`
   - `○ /account/body-profile`
   - `ƒ /account/body-profile/scans/[id]`

3. **Backend Pytest Suite**:
   ```powershell
   python -m pytest backend/tests -v
   ```
   *Kết quả*: **66/66 test passed 100%**, bao gồm 7 test cho auth & history:
   - `test_auth_register_login_lifecycle_and_profile`: PASSED
   - `test_auth_rate_limiting_lockout`: PASSED
   - `test_guest_scan_creation_access_and_user_claim`: PASSED
   - `test_user_ownership_and_permission_isolation`: PASSED
   - `test_idempotent_save_and_null_preservation`: PASSED
   - `test_chart_api_template_model_exclusion_and_range_filtering`: PASSED
   - `test_compare_api_deltas_warnings_and_neutral_summaries`: PASSED

4. **Playwright Visual Verification**:
   - `01-account-unauth.png`: Giao diện bảo vệ unauthenticated thân thiện.
   - `02-body-profile-unauth.png`: Trang hồ sơ hình thể unauthenticated.
   - `03-account-auth.png`: Trang tài khoản authenticated (Minh Thảo, toggle tự lưu, thống kê số scan).
   - `04-body-profile-auth.png`: Hero card số đo mới nhất, biểu đồ SVG ngắt dòng trung thực khi thiếu mông thân trên, danh sách scan có checkbox so sánh.
   - `05-scan-compare-modal.png`: Modal so sánh trước / sau với delta cm và nhận định trung tính.
   - `06-scan-detail.png`: Chi tiết lần scan, bảng số đo, nguồn gốc nhân trắc và trình soạn ghi chú.

---

## 3. Danh sách File Tạo Mới & Chỉnh Sửa

| Đường dẫn File | Loại | Mô tả |
| :--- | :--- | :--- |
| `frontend/lib/userScansApi.ts` | Tạo mới | Client API types, utilities, date formatting và fetch functions cho scan history, chart & compare |
| `frontend/components/shop/BodyChart.tsx` | Tạo mới | SVG interactive chart, metric toggles, null handling, WCAG symbols, data table |
| `frontend/components/shop/ScanCompareModal.tsx` | Tạo mới | Modal so sánh 2 lần scan, delta cm, câu văn so sánh trung tính, cảnh báo tương thích |
| `frontend/app/account/page.tsx` | Tạo mới | Trang tổng quan tài khoản, sửa tên trực tiếp, toggle auto-save, thống kê tóm tắt |
| `frontend/app/account/body-profile/page.tsx` | Tạo mới | Trang hồ sơ hình thể, Hero card số đo gần nhất, biểu đồ BodyChart, danh sách lịch sử |
| `frontend/app/account/body-profile/scans/[id]/page.tsx` | Tạo mới | Trang chi tiết số đo lần scan, ghi chú cá nhân, xóa có xác nhận, nút so sánh lần trước |
| `frontend/app/account/account.css` | Tạo mới | Hệ thống styling Warm Ivory & Champagne Gold, responsive desktop/tablet/mobile |
| `frontend/app/layout.tsx` | Chỉnh sửa | Bổ sung import `./account/account.css` |
| `verification/scripts/seed_demo_scans.py` | Tạo mới | Script gieo dữ liệu scan kiểm thử mẫu vào SQLite |
| `verification/scripts/profile-verification.cjs` | Tạo mới | Kịch bản kiểm thử E2E Playwright và chụp ảnh màn hình nghiệm thu |
| `BODY_PROFILE_HANDOFF.md` | Tạo mới | Tài liệu bàn giao chi tiết module hồ sơ hình thể |
