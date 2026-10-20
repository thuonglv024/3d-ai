# MORPH Studio — Hợp Đồng Giao Tiếp API (`docs/API_CONTRACT.md`)

Tài liệu hợp đồng dữ liệu chuẩn giữa Frontend (`http://127.0.0.1:3000`) và Backend FastAPI (`http://127.0.0.1:8000`, được proxy qua `/api/*`).  
Cập nhật: 14/10/2026.

---

## 1. Nhóm API Quét Hình Thể 3D & Gợi Ý Size (`backend/app/main.py` & `sizing.py`)

| Method | Endpoint | Mô tả | Request | Response & Bảo mật |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Kiểm tra trạng thái backend & engine | None | `200 OK`: `{ ready: bool, engine: str, message: str, retention_seconds: int }` |
| `POST` | `/api/capture-check` | Kiểm tra tư thế và góc chụp webcam theo thời gian thực | `multipart/form-data`: `photo` (file $\le 2\text{MB}$), `view` (`"front" \| "side"`), `consent` (`bool`), `capture_mode` (`"upper_body" \| "full_body"`) | `200 OK`: `{ ready: bool, message: str, landmarks: number[][], view: str, capture_mode: str }` |
| `POST` | `/api/scans` | Khởi tạo phiên dựng hình 3D từ 2 frame camera | `multipart/form-data`: `front` ($\le 10\text{MB}$), `side` ($\le 10\text{MB}$), `height_cm` (`100..230`), `consent` (`true`), `capture_mode` (`"upper_body" \| "full_body"`) | `202 Accepted`: `Job` object (kèm `guest_token` nếu chưa đăng nhập) |
| `GET` | `/api/scans/{key}` | Lấy trạng thái xử lý & số đo phiên scan | Path `key`; Header `X-Guest-Token` hoặc `?guest_token=` | `200 OK`: `Job` object; `403`: Thiếu/sai token hoặc khác chủ sở hữu; `404`: Hết hạn/không tồn tại |
| `GET` | `/api/scans/{key}/model` | Tải file mô hình `.glb` 3D | Path `key`; `?guest_token=` hoặc `X-Guest-Token` | `200 OK` (`model/gltf-binary`); `403` / `404` |
| `GET` | `/api/scans/{key}/measurements` | Tải báo cáo số đo JSON | Path `key`; `?guest_token=` hoặc `X-Guest-Token` | `200 OK` (`application/json`); `403` / `404` |
| `POST` | `/api/scans/{key}/size-advice` | Đối chiếu số đo của phiên scan với `SizeChart` gửi kèm | Path `key`, Header `X-Guest-Token`, Body `SizeChart` | `200 OK`: `SizeAdviceResponse`; `403` / `404` |
| `POST` | `/api/sizing/recommend` | Đối chiếu size theo `product_id` / `product_slug` từ SQLite | Body: `{ scan_id?, product_id?, product_slug?, measurements?, size_chart?, guest_token? }` | `200 OK`: `SizeAdviceResponse` |
| `DELETE` | `/api/scans/{key}` | Xóa phiên scan & file `.glb` trên đĩa ngay lập tức | Path `key`; Header `X-Guest-Token` hoặc `?guest_token=` | `204 No Content`; `403`: Thiếu hoặc sai token |

### Quy tắc Bảo mật Phiên Scan (`check_scan_access`)
- Nếu phiên scan thuộc về người dùng đã đăng nhập (`job.user_id is not None`): chỉ chủ sở hữu có phiên `morph_session` khớp `user_id` mới được phép truy cập hoặc xóa (`403` nếu khác người dùng).
- Nếu phiên scan là của khách (`job.user_id is None` và `job.guest_token` tồn tại): **bắt buộc** request phải gửi `guest_token` (qua header `X-Guest-Token` hoặc query `?guest_token=`) và khớp qua `secrets.compare_digest`. Request không gửi token hoặc gửi sai token đều bị chặn với HTTP `403 Forbidden`.

### Cấu trúc `Job` & `SizeAdviceResponse`
```typescript
export interface Job {
  id: string;
  status: "queued" | "processing" | "completed" | "failed";
  stage: string;
  created: number;
  finished: number | null;
  model_url: string | null;
  error: string | null;
  warnings: string[];
  measurements: {
    height_cm: number;
    shoulder_width_cm: number;
    chest_cm: number;
    waist_cm: number;
    hip_cm: number | null; // Bắt buộc là null khi capture_mode === "upper_body"
    inseam_cm: null;
  } | null;
  body_profile: {
    capture_mode: "upper_body" | "full_body";
    scale_method: string;
    measurement_method: string;
    fit_status: "matched" | "approximate";
    max_fit_error_cm: number;
    sections: Array<{
      key: string;
      label: string;
      target_cm: number;
      model_cm: number;
      fit_error_cm: number;
      points_m: number[][];
    }>;
    measurement_details: Array<{
      key: string;
      label: string;
      kind: "circumference" | "breadth" | "length";
      source: "user_input" | "photo_estimate" | "photo_with_prior" | "template_model" | "unavailable";
      value_cm: number | null;
      points_m: number[][];
    }>;
  } | null;
  guest_token?: string;
  user_id?: string | null;
}
```

---

## 2. Quy Tắc Nguồn Gốc Số Đo (`Measurement Provenance`)

1. **`user_input`**: Chiều cao (`height_cm`) do người dùng nhập.
2. **`photo_estimate`**: Vòng ngực (`chest_cm`), vòng eo (`waist_cm`), vòng mông (`hip_cm`), rộng vai (`shoulder_width_cm`) khi chụp toàn thân (`capture_mode="full_body"`).
3. **`photo_with_prior`**: Vòng ngực (`chest_cm`), vòng eo (`waist_cm`), rộng vai (`shoulder_width_cm`) khi chụp thân trên (`capture_mode="upper_body"` — suy tỷ lệ cm từ chiều cao nhập và đa mỏ neo sọ–vai–hông trên mẫu).
4. **`template_model`**: Các vòng trích từ mặt cắt lưới MakeHuman (`head_cm`, `neck_cm`, `thigh_cm`, `calf_cm`, `ankle_cm`, và `hip_cm` trong `measurement_details` khi chụp `upper_body`).
   - **Quy tắc bất biến**: Trong `measurements` cấp cao nhất dùng để tư vấn size, khi `capture_mode="upper_body"`, `measurements.hip_cm` **bắt buộc là `null`**. Nếu bảng size sản phẩm yêu cầu `hip_cm` (quần, chân váy, đầm cần số đo mông), API trả về `status: "insufficient_measurements"` và `missing: ["hip_cm"]`, tuyệt đối không lấy vòng mông của mẫu 3D để tư vấn size quần/váy.
5. **`unavailable`**: Chiều dài tay (`arm_length_cm`) và chiều dài đũng quần (`inseam_cm`) luôn giữ giá trị `null`.

---

## 3. Nhóm API Danh Mục Sản Phẩm (`backend/app/catalog.py`)

| Method | Endpoint | Mô tả | Query / Params | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/products` | Danh sách 160 sản phẩm (hỗ trợ lọc, tìm kiếm, sắp xếp, phân trang) | `page`, `limit` (mặc định 24), `category`, `search`, `sort` (`featured \| price_asc \| price_desc \| name_asc \| newest`), `min_price`, `max_price`, `color`, `size` | Khi có `page`/`limit`: `{ items, total, page, page_size, total_pages }`; khi không truyền: `Product[]` |
| `GET` | `/api/products/{slug}` | Chi tiết sản phẩm kèm biến thể màu/size/stock, ảnh studio v2 và `size_chart` | Path `slug` hoặc `id` | `200 OK`: `Product`; `404`: Không tìm thấy |
| `GET` | `/api/products/categories` | Danh sách 5 danh mục kèm `product_count` (alias `/api/categories`) | None | `200 OK`: `Category[]` |

---

## 4. Nhóm API Báo Giá & Đặt Hàng (`backend/app/orders.py`)

| Method | Endpoint | Mô tả | Request | Response & Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/orders/quote` | Tính tạm tính, phí giao hàng (`30.000₫`, miễn phí từ `500.000₫`) và tổng tiền từ giá niêm yết trong SQLite | Body: `{ items: [{ product_id, color, size, quantity }] }` | `200 OK`: `{ items, subtotal_vnd, shipping_fee_vnd, total_vnd, free_shipping_threshold_vnd }` |
| `POST` | `/api/orders` | Tạo đơn hàng mới và trừ tồn kho nguyên tử (`BEGIN IMMEDIATE;`) | Header `Idempotency-Key` (tùy chọn); Body: `{ customer: { full_name, phone, email?, address, note? }, items: [...] }` | `201 Created`: `{ id, order_code, token, status, status_label, ... }`; `400`: Hết hàng hoặc SĐT không hợp lệ; `409`: Trùng `Idempotency-Key` khác dữ liệu |
| `GET` | `/api/orders/{id}` | Tra cứu chi tiết đơn hàng theo `id` hoặc `order_code` | Query `?token=` hoặc Header `X-Order-Token` / `Authorization: Bearer <token>` | `200 OK`: Chi tiết đơn hàng; `404`: Thiếu hoặc sai token |

---

## 5. Nhóm API Xác Thực & Tài Khoản (`backend/app/auth.py`)

| Method | Endpoint | Mô tả | Request | Response & Cookie |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Đăng ký tài khoản mới | `{ email, password (min 8), display_name }` | `201 Created`: `{ user }` + Set-Cookie `morph_session` (`HttpOnly`, `SameSite=lax`, `Max-Age=2592000`) |
| `POST` | `/api/auth/login` | Đăng nhập (có rate limit khóa 5 phút sau 5 lần sai liên tiếp) | `{ email, password }` | `200 OK`: `{ user }` + Set-Cookie `morph_session`; `401`: Sai thông tin; `429`: Khóa tạm thời |
| `POST` | `/api/auth/logout` | Đăng xuất và xóa session trong SQLite | Cookie `morph_session` | `200 OK` + Xóa cookie `morph_session` |
| `GET` | `/api/auth/me` | Lấy thông tin người dùng hiện tại | Cookie `morph_session` | `200 OK`: `{ user: User \| null }` |
| `PATCH` | `/api/auth/profile` | Cập nhật `display_name` hoặc cài đặt `auto_save_scans` | `{ display_name?, auto_save_scans? }` | `200 OK`: `{ user }`; `401`: Chưa đăng nhập |

---

## 6. Nhóm API Hồ Sơ Hình Thể & Lịch Sử Scan (`backend/app/history.py`)

Tất cả các endpoint dưới đây yêu cầu xác thực qua cookie `morph_session` (`401 Unauthorized` nếu chưa đăng nhập):

| Method | Endpoint | Mô tả | Request / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/user/scans/save` | Lưu kết quả scan (hoặc claim scan khách bằng `guest_token`) vào hồ sơ cá nhân | `{ scan_id, guest_token?, note? }` | `200 OK`: Bản ghi scan đã lưu (idempotent nếu gọi lặp lại); `403`: Sai/thiếu `guest_token` |
| `GET` | `/api/user/scans` | Danh sách lịch sử các lần scan của người dùng | `?limit=50&offset=0` | `200 OK`: `{ items: SavedScan[], total: number }` |
| `GET` | `/api/user/scans/latest` | Lấy lần scan gần nhất | None | `200 OK`: `{ scan: SavedScan \| null }` |
| `GET` | `/api/user/scans/chart` | Dữ liệu biểu đồ số đo theo thời gian (loại trừ `template_model` khỏi đường biểu diễn) | `?range=30d\|90d\|all` | `200 OK`: `{ points: ChartPoint[], range: string }` |
| `GET` | `/api/user/scans/compare` | Đối chiếu toán học trung tính giữa 2 lần scan | `?scan_a={id1}&scan_b={id2}` | `200 OK`: `{ scan_a, scan_b, deltas, warnings, compatible }` |
| `GET` | `/api/user/scans/{scan_id}` | Xem chi tiết một bản ghi scan đã lưu | Path `scan_id` | `200 OK`: `SavedScan`; `403` / `404` |
| `PATCH` | `/api/user/scans/{scan_id}` | Cập nhật ghi chú cá nhân (`note`) cho bản ghi scan | `{ note: string }` | `200 OK`: `SavedScan` |
| `DELETE` | `/api/user/scans/{scan_id}` | Xóa bản ghi scan khỏi lịch sử cá nhân | Path `scan_id` | `200 OK`: `{ deleted: true, id: scan_id }` |

---

## 7. Nhóm API Quét AI Thử Nghiệm (`backend/app/ai_scan`) — AI Vision · Beta

Đây là nhánh thử nghiệm độc lập, **không thay thế** `/api/scans` hay pipeline MediaPipe.
Kết quả luôn mang provenance `ai_vision_estimate`, không tạo mô hình 3D và không lưu ảnh.

| Method | Endpoint | Mô tả | Request | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/ai-scan/health` | Kiểm tra cấu hình AI (không lộ key) | None | `200 OK`: `{ ready, provider: "google-genai", model, message }` |
| `POST` | `/api/ai-scan/analyze` | Ước lượng số đo từ 2 ảnh bằng Gemini + LangGraph | `multipart/form-data`: `front`, `side` (≤ 10 MB, khác nhau), `height_cm` (`100..230`), `consent=true`, `capture_mode` | `200 OK`: `AiScanResponse`; `400` consent/ảnh lỗi; `413` quá dung lượng; `422` không ước lượng được; `502` lỗi model; `503` thiếu key/deps; `504` timeout |

`AiScanResponse`:
```typescript
{
  status: "completed";
  provider: "google-genai";
  model: string;
  capture_mode: "upper_body" | "full_body";
  measurements: {
    height_cm: number;
    chest_cm: number | null;
    waist_cm: number | null;
    hip_cm: number | null;          // luôn null ở upper_body
    shoulder_width_cm: number | null;
  };
  details: Array<{
    key: string;
    label: string;
    value_cm: number | null;
    source: "ai_vision_estimate";
  }>;
  confidence: number;               // 0..1
  pose_quality: "good" | "fair" | "poor" | string;
  notes: string;
  warnings: string[];
  elapsed_seconds: number;
  source: "ai_vision_estimate";
}
```

Cấu hình: đặt `GOOGLE_API_KEY` (hoặc `GEMINI_API_KEY`) và tuỳ chọn `MORPH_AI_MODEL`
trong `backend/.env`; cài `backend/requirements-ai.txt`. Xem
[`docs/AI_SCAN_FEATURE.md`](file:///d:/MORPH-AI/docs/AI_SCAN_FEATURE.md).
