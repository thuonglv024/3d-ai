# MORPH AI — Hoàn thiện luồng AUTH → SCAN → GỢI Ý SIZE → LƯU HỒ SƠ → BIỂU ĐỒ

**Ngày hoàn thành**: 13/10/2026  
**Phạm vi**: Toàn bộ luồng kết nối từ Camera Scan đến Tư vấn size, Tài khoản người dùng, Lưu trữ hồ sơ hình thể và Biểu đồ thời gian thực.  
**Thực hiện**: Agent Điều Phối + 3 Sub-agents chạy song song (Agent BE, Agent FE Scan, Agent FE Profile).

---

## 1. Tóm tắt Kết quả Thực hiện & Mục tiêu Đạt được

| Mục tiêu Yêu cầu | Hiện trạng Giải quyết | Bằng chứng Kiểm nghiệm |
| :--- | :--- | :--- |
| **1. Scan xong nhìn thấy kết quả đối chiếu size của đúng sản phẩm đang chọn** | • Triển khai endpoint mới `POST /api/sizing/recommend` tra cứu bảng size chính thức từ SQLite DB theo `product_id` / `product_slug`.<br>• Đổi cấu hình Pydantic `extra="ignore"` trên `SizeChart`, `SizeRow`, `Range`.<br>• Card gợi ý size hiển thị ngay phía trên 3D viewer với nút "Áp dụng size [X] →" đồng bộ trực tiếp vào PDP size selector và giỏ hàng. | • API trả về `matched` với candidate chính xác (Size M cho sơ mi, Size 29 cho quần tây).<br>• Playwright E2E Test 2: PASSED.<br>• Pytest 74/74 passed. |
| **2. Quần, chân váy và đầm phải được hướng dẫn scan toàn thân ngay từ bước nhập thông tin** | • Hàm phát hiện tự động `isFullBodyRequired` cho các sản phẩm quần/váy/đầm (`cat-quan`, `cat-vay`, `garment: "bottom"` hoặc `"dress"`).<br>• Mặc định chọn `captureMode = "full_body"`.<br>• Hiển thị Card hướng dẫn thiết bị nổi bật: góc nghiêng laptop, khoảng cách 2m–2.5m, điện thoại ngang ngực.<br>• Cảnh báo màu hổ phách nếu người dùng cố tình chuyển sang `upper_body`.<br>• Khi thiếu số đo mông, hiển thị thông điệp chẩn đoán rõ ràng kèm CTA "Quét lại toàn thân". | • Ảnh Playwright `01-pdp-bottom-fullbody-guidance.png`.<br>• E2E Test 1 & 3: PASSED 100%. |
| **3. Đăng nhập / lưu hồ sơ hoạt động xuyên suốt, không mất kết quả và không lẫn tài khoản** | • Chuẩn hóa token sở hữu: Frontend sử dụng trực tiếp `guest_token = secrets.token_urlsafe(24)` do backend cấp phát, loại bỏ chuỗi random giả.<br>• `POST /api/user/scans/save` kiểm tra `secrets.compare_digest`, chuyển quyền sở hữu scan guest sang tài khoản vừa đăng nhập/đăng ký một cách an toàn và idempotent.<br>• `AuthModal` mount toàn cục trong `Providers`, thực thi `pendingAction` trơn tru sau khi auth thành công.<br>• Khi đăng xuất: xóa sạch cache cá nhân và token phiên trong `sessionStorage`. | • E2E Test 4: PASSED.<br>• Pytest `test_guest_scan_creation_access_and_user_claim` & `test_save_scan_urlsafe_token_and_idempotency_scenarios`: PASSED. |
| **4. Chart phản ánh đúng số đo và thời gian, không tạo xu hướng sai** | • Trục X tính theo tỷ lệ thời gian tuyến tính thực tế: `x = padding.left + ((t - minTime) / span) * width`. Loại bỏ hoàn toàn việc dịch điểm nhân tạo `minSpacing = 44px`.<br>• Các lần scan sát nhau (< 16px) giữ nguyên tọa độ thời gian thực và hiển thị **Cluster Badge** (viên thuốc số lượng lần scan) kèm popover tương tác mở chi tiết từng lần scan.<br>• Xử lý trung thực: các giá trị `null` hoặc `template_model` ngắt đường line, tuyệt đối không vẽ về 0 và không vẽ đường biến thiên giả mạo. | • Ảnh Playwright `02-body-profile-chart-with-cluster.png`.<br>• E2E Test 5: PASSED. |

---

## 2. Chi tiết Kiến trúc & Các File Đã Chỉnh Sửa

### 2.1 Backend (`backend/app/`)
1. **[`backend/app/sizing.py`](file:///d:/MORPH-AI/backend/app/sizing.py)**:
   - Cấu hình `model_config = ConfigDict(extra="ignore")` trên toàn bộ schemas (`Range`, `SizeRow`, `SizeChart`, `SizingRecommendRequest`).
   - Hỗ trợ `garment: Literal["top", "bottom", "dress", "outerwear"] | str`.
   - Validator `dimensions`: bắt buộc ngực/eo cho áo; bắt buộc eo/mông cho quần; linh hoạt cho đầm.
   - `recommend_size`: khi thiếu số đo bắt buộc (như `hip_cm` cho quần), trả về `status: "insufficient_measurements"`, `missing: ["hip_cm"]`, và chẩn đoán rõ ràng.
2. **[`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py)**:
   - Triển khai endpoint mới `POST /api/sizing/recommend`: tự động query SQLite products table để lấy bảng size và tra cứu measurements từ active job memory hoặc database scan đã lưu.
   - Cập nhật `check_scan_access` hỗ trợ `X-Guest-Token` header, query param và token param, không chặn 403 trái phép.
3. **[`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py)**:
   - Sửa `POST /api/user/scans/save` kiểm tra DB trước (idempotent), xác thực `guest_token` qua `secrets.compare_digest`.
4. **Backend Tests**:
   - `backend/tests/test_size_advice.py` & `backend/tests/test_sizing.py`: bổ sung test case cho full-body vs upper-body bottom, dress, `POST /api/sizing/recommend`.
   - **Kết quả pytest: 74/74 tests passed 100%**.

### 2.2 Frontend Shared Layer & Sizing (`frontend/lib/`)
1. **[`frontend/lib/useBodyScan.ts`](file:///d:/MORPH-AI/frontend/lib/useBodyScan.ts)**:
   - Mở rộng kiểu `Job`: bổ sung `guest_token?: string; user_id?: string | null;`.
   - Gửi `credentials: "include"` khi tạo scan và tự động lưu `guest_token` thật từ backend vào `sessionStorage`.
2. **[`frontend/lib/ScanContext.tsx`](file:///d:/MORPH-AI/frontend/lib/ScanContext.tsx)**:
   - Hàm `getGuestToken`: trả về token thật từ backend/sessionStorage, không tự sinh chuỗi `gst_` ngẫu nhiên.
   - `fetchAdviceForProduct`: gửi `credentials: "include"` và header `X-Guest-Token`, gọi endpoint `POST /api/sizing/recommend` ưu tiên trước khi fallback.
   - Bổ sung `applySavedScanToSession` cho phép nạp số đo từ hồ sơ vào phiên thử đồ.
   - Lắng nghe sự kiện logout để xóa sạch cache trạng thái lưu và số đo cá nhân.
3. **[`frontend/lib/AuthContext.tsx`](file:///d:/MORPH-AI/frontend/lib/AuthContext.tsx)**:
   - Đảm bảo thực thi `pendingAction` sau khi đăng nhập / đăng ký thành công.
   - Xóa token scan cá nhân khi đăng xuất.

### 2.3 Giao diện Scan & Trang Sản phẩm (`frontend/components/shop/`)
1. **[`frontend/components/shop/FitExperience.tsx`](file:///d:/MORPH-AI/frontend/components/shop/FitExperience.tsx)**:
   - Phát hiện danh mục quần, chân váy, đầm -> mặc định chọn `full_body`.
   - Hiển thị Card hướng dẫn thiết bị (góc đặt laptop, khoảng cách 2m–2.5m, điện thoại).
   - Cảnh báo màu hổ phách khi chọn chế độ thân trên cho trang phục cần vòng mông.
2. **[`frontend/components/shop/ScanResult.tsx`](file:///d:/MORPH-AI/frontend/components/shop/ScanResult.tsx)**:
   - Đặt khối Gợi ý Size lên vị trí nổi bật hàng đầu trước workspace 3D.
   - Nút "Áp dụng size [X] →" kích hoạt chọn size trên trang sản phẩm.
   - Nút "Quét lại toàn thân" chuyển ngay vào chế độ `full_body` khi thiếu số đo.
3. **[`frontend/components/shop/ProductDetail.tsx`](file:///d:/MORPH-AI/frontend/components/shop/ProductDetail.tsx)**:
   - Loại bỏ re-render lặp trong `useEffect`.
   - Hiển thị huy hiệu "Size gợi ý cho bạn: Size [X]" với biểu tượng Sparkles Champagne Gold.
   - Tự động đánh dấu nút size gợi ý và áp dụng vào giỏ hàng.
4. **[`frontend/app/providers.tsx`](file:///d:/MORPH-AI/frontend/app/providers.tsx)**:
   - Mount `<AuthModal />` toàn cục, đảm bảo mở được modal ở mọi trang kể cả `/scan`.

### 2.4 Hồ sơ Hình thể & Biểu đồ (`frontend/app/account/` & `BodyChart.tsx`)
1. **[`frontend/components/shop/BodyChart.tsx`](file:///d:/MORPH-AI/frontend/components/shop/BodyChart.tsx)**:
   - Biểu đồ thời gian tuyến tính chuẩn xác, ngắt quãng đường line cho giá trị `null`/`template_model`.
   - Tự động phát hiện và gom nhóm các lần scan sát giờ (< 16px) thành **Cluster Badge** kèm popover tương tác chọn scan chi tiết.
2. **[`frontend/app/account/body-profile/page.tsx`](file:///d:/MORPH-AI/frontend/app/account/body-profile/page.tsx)**:
   - Hiển thị số đo gần nhất kèm nguồn gốc minh bạch (`Bạn nhập`, `Ước lượng ảnh`, `Ảnh + tỷ lệ mẫu`, `Theo mẫu 3D`).
   - Bổ sung nút "Thử áp dụng số đo này để chọn size trang phục".
3. **[`frontend/app/account/body-profile/scans/[id]/page.tsx`](file:///d:/MORPH-AI/frontend/app/account/body-profile/scans/[id]/page.tsx)**:
   - Khối Detail Size Fitting Card điều hướng sang catalog với số đo đã lưu.

---

## 3. Kết Quả Kiểm Thử Toàn Diện

1. **Frontend Typecheck (`npm --prefix frontend run typecheck`)**:
   - **0 errors** (Exit code 0).
2. **Next.js Production Build (`npm --prefix frontend run build`)**:
   - **Biên dịch thành công 31/31 routes** (Exit code 0) trong 8.4s.
3. **Backend Pytest Suite (`backend/.venv/Scripts/python.exe -m pytest backend/tests -v`)**:
   - **74/74 tests passed 100%**.
4. **Playwright E2E Verification Script (`verification/scripts/auth-scan-chart-size-verification.cjs`)**:
   - `test1_product_bottom_guidance`: **PASSED** (Full-body guidance card & default full_body mode verified on PDP).
   - `test2_size_advice_api_top_and_bottom`: **PASSED** (Size M matched for top, Size 29 matched for bottom).
   - `test3_insufficient_measurements_bottom`: **PASSED** (Diagnosed missing `hip_cm` for bottom).
   - `test4_guest_token_claim_and_auth_save`: **PASSED** (Guest token verified and claimed into user profile).
   - `test5_body_chart_linear_time_and_cluster`: **PASSED** (Linear time coordinates, broken path for missing hip in upper scan, cluster badge rendered).
   - `test6_scan_detail_and_size_apply_action`: **PASSED** (Scan detail with apply size CTA).
   - **Tất cả 6/6 bài kiểm tra E2E đã đạt**.

---

## 4. Bằng chứng Hình ảnh Đã Kiểm Nghiệm

Các ảnh chụp nghiệm thu lưu trữ tại thư mục: `output/playwright/auth-scan-chart-size/`:
- `01-pdp-bottom-fullbody-guidance.png`: Hướng dẫn chụp toàn thân nổi bật cho Quần tây Xếp ly Dáng rộng ở bước Onboarding chiều cao.
- `02-body-profile-chart-with-cluster.png`: Hero card số đo mới nhất, biểu đồ thời gian thực ngắt dòng mông ở lần scan thân trên cũ, cụm Cluster Badge `2` ở thời điểm hiện tại.
- `04-scan-detail-with-apply-cta.png`: Chi tiết số đo lần scan kèm khối "Chọn size trang phục với số đo này".

---

## 5. Giới hạn & Khuyến nghị Tiếp theo
- **Độ chính xác số đo**: Tiếp tục duy trì tuyên bố minh bạch công nghệ rằng số đo ước lượng từ 2 góc chụp và mô hình MakeHuman chưa được kiểm chứng lâm sàng y tế hay may đo chính xác.
- **Mở rộng catalog**: Catalog hiện tại có 160 sản phẩm với đầy đủ ảnh và size chart chuẩn lưu trong SQLite, sẵn sàng mở rộng thêm bộ lọc nâng cao nếu cần.
