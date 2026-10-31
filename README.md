# MORPH AI — Studio Thời Trang & Tư Vấn Kích Cỡ 3D

**MORPH AI** là nền tảng cửa hàng thời trang điện tử tích hợp công nghệ **Quét Hình Thể 3D qua Webcam (Camera-Only)** và **Phân Tích Số Đo & Gợi Ý Kích Cỡ (Size Recommendation)**. Hệ thống kết hợp trải nghiệm mua sắm phong cách Luxury Editorial (**Warm Ivory & Champagne Gold**) với không gian đo đạc chuyên sâu (**Dark Measurement Workspace**).

---

## 1. Tính năng nổi bật

- **Cửa hàng Thời trang 162 Sản phẩm**:
  - Danh mục 162 sản phẩm (160 sản phẩm gốc + 2 mẫu áo thun có **số đo may trải phẳng** công bố từ Gildan 5000 và Uniqlo Supima Oversized) với đầy đủ biến thể màu sắc, tồn kho theo size và bảng thông số `size_chart` riêng cho từng sản phẩm.
  - Bộ lọc đa chiều theo giới tính, danh mục, khoảng giá, từ khóa tìm kiếm và danh sách yêu thích (**Wishlist**) đồng bộ mượt mà với giỏ hàng.
- **Quét Hình Thể 3D Tự Động Qua Webcam (Camera-Only)**:
  - Hỗ trợ chế độ mặc định **Quét Thân Trên (`upper_body`)** phù hợp góc webcam laptop/PC và chế độ **Quét Toàn Thân (`full_body`)**.
  - Nhận diện tư thế thời gian thực qua **MediaPipe Pose & Selfie Segmentation**, hướng dẫn giọng nói/overlay trực quan và tự động đếm ngược chụp 2 góc: **Chính diện (Frontal)** $\rightarrow$ **Nghiêng 90° (Lateral)**.
  - Không sử dụng tải ảnh tĩnh hay hiển thị mannequin mẫu trước khi quét.
- **Pipeline Tối Ưu Hóa 3D Body Scan 3 Tầng (`< 15 ms` xử lý toán học)**:
  - **Tầng 1 (Multi-Anchor Height Observation)**: Kết hợp mỏ neo Đỉnh đầu $\rightarrow$ Vai (`0.195 H`) và Vai $\rightarrow$ Hông (`0.290 H`) bằng hàm Huber/Tanh giới hạn biên độ, ổn định chiều cao tham chiếu với sai số $\le \pm 1.20\%$.
  - **Tầng 2 (Camera Scale Fusion)**: Đồng bộ mốc giải phẫu và dùng chung hệ số quy đổi chiều cao giữa góc chính diện và góc nghiêng 90°, bảo toàn tuyệt đối tỷ lệ Độ sâu / Bề rộng ($D/W$).
  - **Tầng 3 (Anatomical Calibration & PCHIP Mesh Fitting)**: Bù trừ độ lõm giải phẫu mặt cắt ngang (`ANATOMICAL_SECTION_FACTORS`) tại Ngực, Eo, Hông và khớp lưới 3D với số đo. Lưới nền là **basis Anny** (Apache-2.0, asset MakeHuman CC0) sinh sẵn cho nam/nữ, kèm fallback MakeHuman; xuất file `.glb` trực quan.
- **Minh Bạch Nguồn Số Đo & Hồ Sơ Hình Thể (`BodyProfile`)**:
  - Phân biệt rõ 5 nguồn dữ liệu: `photo_estimate`, `photo_with_prior`, `template_model`, `user_input`, `unavailable`.
  - Cho phép nhập bổ sung số đo phần dưới (`hip_cm`, `inseam_cm`) khi quét `upper_body` để tư vấn chính xác cả quần, chân váy và đầm liền.
  - **Sửa số đo sau khi quét**: chỉnh chiều cao/ngực/eo/mông ngay trên màn hình kết quả; backend dựng lại mô hình 3D và cập nhật gợi ý size, ghi nguồn `user_input` cho các dòng đã sửa.
- **Bản Đồ Độ Vừa Theo Vùng (Beta)**:
  - Chọn size của sản phẩm để tô màu ngực/eo/mông trên mô hình 3D theo mức **chật / sát / vừa / rộng**, kèm chênh lệch chu vi và khe hở ước tính.
  - Ước lượng từ khoảng số đo cơ thể trong bảng size và nhãn `fit`/chất liệu; **chưa phải** số đo may trải phẳng hay mô phỏng vải. API: `POST /api/fit-map`.
- **Tài Khoản, Biểu Đồ Lịch Sử & Đặt Hàng Nguyên Tử**:
  - Xác thực qua `HttpOnly` session cookie (`morph_session`, băm `SHA-256` trong SQLite, mật khẩu băm `PBKDF2-HMAC-SHA256` 200.000 vòng) kèm cơ chế khóa tạm thời khi đăng nhập sai quá 5 lần.
  - Biểu đồ theo dõi tiến trình số đo ([`BodyChart.tsx`](file:///d:/MORPH-AI/frontend/components/shop/BodyChart.tsx)) với trục thời gian tuyến tính và gom cụm thông minh.
  - Đặt hàng nguyên tử (`BEGIN IMMEDIATE;`), chống đặt trùng đơn qua `Idempotency-Key` và bảo vệ đơn hàng khách bằng `order_token`.

---

## 2. Cấu trúc thư mục dự án

```text
MORPH-AI/
├── AGENTS.md                        # Hướng dẫn nhanh và quy tắc cho AI Agent
├── DESIGN.md                        # Hệ thống thiết kế (Warm Ivory & Dark Studio)
├── PRODUCT.md                       # Định hướng sản phẩm và phạm vi chức năng
├── THIRD_PARTY_NOTICES.md           # Giấy phép mã nguồn mở và tài nguyên bên thứ ba
├── docs/                            # Tài liệu kỹ thuật tập trung
│   ├── ARCHITECTURE.md              # Kiến trúc hệ thống, cơ sở dữ liệu và luồng dữ liệu
│   ├── API_CONTRACT.md              # Đặc tả chi tiết toàn bộ REST API
│   ├── SCAN_QUALITY.md              # Phương pháp luận 3D Scan 3 tầng, benchmark & giới hạn
│   ├── TESTING.md                   # Hướng dẫn chạy kiểm thử pytest, benchmark & E2E
│   └── HANDOFF.md                   # Trạng thái bàn giao hiện tại & công việc tiếp theo
├── design/
│   └── ASSET_PROVENANCE.md          # Nguồn gốc và bản quyền hình ảnh sản phẩm
├── backend/                         # FastAPI Backend (Python 3.11)
│   ├── app/
│   │   ├── main.py                  # Điểm vào FastAPI, định tuyến REST API & quản lý phiên quét
│   │   ├── auth.py                  # Xác thực người dùng, PBKDF2-HMAC-SHA256 & session cookie
│   │   ├── catalog.py               # Quản lý 162 sản phẩm, biến thể, size chart & gợi ý size
│   │   ├── seed_160_catalog.py      # Dữ liệu khởi tạo catalog (160 gốc + 2 mẫu số đo may)
│   │   ├── orders.py                # Xử lý đơn hàng nguyên tử, trừ tồn kho & Idempotency-Key
│   │   ├── history.py               # Lưu trữ lịch sử quét 3D và hồ sơ số đo cá nhân
│   │   ├── reconstruction.py        # Tầng 1 & 2: Phân tích ảnh MediaPipe & biến dạng lưới 3D
│   │   ├── camera_fusion.py         # Tầng 2: Đồng bộ tỷ lệ Camera chính diện & nghiêng 90°
│   │   ├── measurements.py          # Tầng 3: Hiệu chuẩn giải phẫu & khớp lưới PCHIP (.glb)
│   │   ├── anny_body.py             # Basis Anny (nam/nữ × cân nặng × cơ) + fallback MakeHuman
│   │   └── models/                  # Model MediaPipe (.task), basis Anny (.npz) và lưới dự phòng (.obj)
│   └── tests/                       # Bộ 135 unit & integration tests (pytest)
├── frontend/                        # Next.js 15 App Router Frontend (React 19, TypeScript)
│   ├── AGENTS.md                    # Hướng dẫn thiết kế giao diện dành cho Agent
│   ├── app/                         # Các trang: /, /products/[id], /scan, /checkout, /orders/[id], /account
│   ├── components/                  # CameraCoach, Viewer (Three.js), SizeFinderModal, BodyChart, Drawers
│   └── lib/                         # AuthContext, CartContext, WishlistContext, ScanContext, usePoseDetection
└── verification/
    └── scripts/                     # Kịch bản kiểm thử hồi quy, benchmark 3D & fixture QA (qa/)
```

---

## 3. Hướng dẫn cài đặt và khởi chạy

### 3.1. Yêu cầu hệ thống
- **Hệ điều hành**: Windows 10/11, macOS hoặc Linux.
- **Python**: `3.11.x` (Sử dụng môi trường ảo tại `backend/.venv/Scripts/python.exe`; **không** dùng alias Python của Windows Store).
- **Node.js**: `>= 20.x` kèm `npm`.
- **Trình duyệt**: Chrome hoặc Edge bản mới nhất (cấp quyền truy cập Webcam trên `http://localhost:3000`).

### 3.2. Khởi chạy Backend (Cổng `8000`)
Mở PowerShell tại thư mục gốc `D:\MORPH-AI`:

```powershell
# Nếu chưa tạo môi trường ảo:
# py -3.11 -m venv backend\.venv
# .\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
- Kiểm tra trạng thái Backend: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Tài liệu Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3.3. Khởi chạy Frontend (Cổng `3000`)
Mở một cửa sổ PowerShell thứ hai tại `D:\MORPH-AI`:

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```
- Truy cập cửa hàng: [http://localhost:3000](http://localhost:3000)
- Truy cập phòng đo 3D độc lập: [http://localhost:3000/scan](http://localhost:3000/scan)

---

## 4. Kiểm thử & Xác minh chất lượng

Chạy toàn bộ các bài kiểm tra tự động trước khi bàn giao (xem chi tiết tại [`docs/TESTING.md`](file:///d:/MORPH-AI/docs/TESTING.md)):

```powershell
# 1. Chạy 95 bài test Backend (pytest)
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q

# 2. Chạy Benchmark độ chính xác & tốc độ 3D Body Scan 3 Tầng (< 15ms)
.\backend\.venv\Scripts\python.exe verification\scripts\evaluate_3d_scan_accuracy.py

# 3. Kiểm tra pipeline quét thân trên với ảnh fixture chuẩn
.\backend\.venv\Scripts\python.exe verification\scripts\check-upper.py

# 4. Kiểm tra kiểu dữ liệu TypeScript phía Frontend
npm --prefix frontend run typecheck
```

---

## 5. Xử lý sự cố thường gặp (Troubleshooting)

1. **Không mở được Webcam trên trình duyệt**:
   - Đảm bảo truy cập qua `http://localhost:3000` (trình duyệt chặn `navigator.mediaDevices.getUserMedia` trên địa chỉ IP LAN không có HTTPS).
   - Đóng các ứng dụng đang chiếm quyền camera (Zoom, Teams, Camera app) rồi bấm *"Thử kết nối lại camera"*.
2. **Xung đột cổng `8000` hoặc `3000`**:
   - Kiểm tra tiến trình đang chiếm cổng bằng `Get-NetTCPConnection -LocalPort 8000,3000` và dừng tiến trình cũ trước khi khởi chạy lại.
3. **Làm mới cơ sở dữ liệu SQLite (`catalog.db`)**:
   - File SQLite được tạo tự động tại `backend/runtime/catalog.db`. Nếu muốn reset toàn bộ đơn hàng và tài khoản thử nghiệm về mặc định 160 sản phẩm, dừng Backend và xóa `backend/runtime/catalog.db` — hệ thống sẽ tự động khởi tạo và seed lại khi bật server.

---

## 6. Liên kết tài liệu chuyên sâu

- [**Kiến trúc hệ thống (`docs/ARCHITECTURE.md`)**](file:///d:/MORPH-AI/docs/ARCHITECTURE.md)
- [**Đặc tả REST API (`docs/API_CONTRACT.md`)**](file:///d:/MORPH-AI/docs/API_CONTRACT.md)
- [**Chất lượng 3D Scan & Giới hạn kỹ thuật (`docs/SCAN_QUALITY.md`)**](file:///d:/MORPH-AI/docs/SCAN_QUALITY.md)
- [**Hướng dẫn kiểm thử (`docs/TESTING.md`)**](file:///d:/MORPH-AI/docs/TESTING.md)
- [**Trạng thái bàn giao hiện tại (`docs/HANDOFF.md`)**](file:///d:/MORPH-AI/docs/HANDOFF.md)
- [**Hệ thống thiết kế (`DESIGN.md`)**](file:///d:/MORPH-AI/DESIGN.md) & [**Định hướng sản phẩm (`PRODUCT.md`)**](file:///d:/MORPH-AI/PRODUCT.md)
- [**Bản quyền bên thứ ba (`THIRD_PARTY_NOTICES.md`)**](file:///d:/MORPH-AI/THIRD_PARTY_NOTICES.md) & [**Nguồn gốc hình ảnh (`design/ASSET_PROVENANCE.md`)**](file:///d:/MORPH-AI/design/ASSET_PROVENANCE.md)
