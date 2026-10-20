# AI Vision Scan (thử nghiệm)

Tính năng quét số đo bằng model AI (Google Gemini) qua **LangChain + LangGraph**, bổ sung
song song với pipeline quét 3D MediaPipe hiện có. Đây là một nhánh **thử nghiệm, độc lập**:
không thay đổi hành vi mặc định của `/scan`, không thay thế pipeline 3D và không ghi ảnh
người dùng ra đĩa.

> Cảnh báo: kết quả AI chỉ là **ước lượng thị giác** từ hai ảnh, chưa được kiểm chứng trên
> người thật và không dùng cho may đo. UI luôn hiển thị nhãn `AI Vision · Beta` và
> `ai_vision_estimate`.

---

## 1. Cấu trúc thư mục

### Backend

```
backend/app/ai_scan/
├── __init__.py      # export ai_scan_router (router nhẹ, không import LangChain)
├── config.py        # đọc GOOGLE_API_KEY / GEMINI_API_KEY, MORPH_AI_MODEL, backend/.env
├── prompts.py       # system + user prompt cho ảnh chính diện/nghiêng
├── schemas.py       # Pydantic: VisionMeasurementEstimate, AiScanResponse
├── graph.py         # LangGraph: analyze -> validate -> finalize
├── service.py       # khởi tạo ChatGoogleGenerativeAI, chạy graph, map lỗi
└── router.py        # GET /api/ai-scan/health, POST /api/ai-scan/analyze
```

`router.py` chỉ import config/schemas ở module level. LangChain và
`langchain-google-genai` được import **lazy** trong `service.py`, nên backend 3D hiện tại
vẫn khởi động bình thường nếu chưa cài AI dependencies.

### Frontend

```
frontend/lib/useAiScan.ts                    # health + analyze + state
frontend/components/ai-scan/AiScanResult.tsx # kết quả số đo AI + gợi ý size
frontend/components/ai-scan/AiPhotoUpload.tsx # upload 2 ảnh, tự phân tích
frontend/components/shop/PoseGuide.tsx       # khung tư thế SVG trên camera
```

Các file hiện có được sửa **theo hướng bổ sung**:
- `frontend/components/shop/FitExperience.tsx`: AI Vision mặc định, nút chuyển `Quét 3D`,
  state upload 2 ảnh và tự gọi phân tích khi đủ điều kiện.
  copy theo mode, gọi `useAiScan`, hiển thị kết quả AI.
- `frontend/components/shop/CaptureSession.tsx`: thêm prop `aiMode` (badge, nhãn bước) và
  render `PoseGuide`; logic chụp/đếm ngược/best-frame giữ nguyên.
- `frontend/app/capture-flow.css`: thêm style cho mode switch, pose guide, AI result và upload.
- `frontend/components/ai-scan/AiScanResult.tsx` và `AiPhotoUpload.tsx` tái sử dụng
  `computeClientSizeAdvice` cùng các class `scan-result`, `scan-size-panel`, `scan-data-grid`,
  `scan-advice-*` sẵn có.

---

## 2. Luồng LangGraph

```
START
  └─ analyze    : gửi 2 ảnh + chiều cao + capture_mode tới Gemini (structured output)
  └─ validate   : loại giá trị bất khả thi, ép hip=null ở upper_body, thêm cảnh báo
  └─ finalize   : đóng gói measurements + provenance ai_vision_estimate
END
```

- `analyze` dùng `ChatGoogleGenerativeAI(...).with_structured_output(VisionMeasurementEstimate)`.
  Ảnh được gửi dưới dạng data URL base64 trong `HumanMessage`.
- `validate` không tự sửa số đo. Giá trị ngoài khoảng sinh lý → `null` + warning; các tỷ lệ
  bất thường so với chiều cao → warning và giảm confidence.
- `finalize` trả về đúng contract `AiScanResponse`, không tạo mô hình 3D.

Có thể test graph mà không gọi mạng bằng một fake model (xem
`backend/tests/test_ai_scan.py::test_langgraph_pipeline_with_fake_model`).

---

## 3. Cấu hình

1. Cài dependencies AI (không bắt buộc cho pipeline 3D):

   ```powershell
   D:\MORPH-AI\backend\.venv\Scripts\python.exe -m pip install -r D:\MORPH-AI\backend\requirements-ai.txt
   ```

2. Tạo `backend/.env` từ `backend/.env.example`:

   ```env
   GOOGLE_API_KEY=<key từ Google AI Studio>
   MORPH_AI_MODEL=gemini-2.5-flash
   ```

   Có thể dùng biến môi trường `GEMINI_API_KEY` thay cho `GOOGLE_API_KEY`.
   `MORPH_AI_MODEL` có thể đổi sang model Gemini khác hỗ trợ ảnh.

3. Khởi động lại backend. Kiểm tra:

   ```powershell
   curl http://127.0.0.1:8000/api/ai-scan/health
   ```

   Khi chưa có key, endpoint trả `ready: false` và UI hiển thị
   “Chưa cấu hình GOOGLE_API_KEY”; **không sinh kết quả giả**.

---

## 4. API

### `GET /api/ai-scan/health`

```json
{
  "ready": true,
  "provider": "google-genai",
  "model": "gemini-2.5-flash",
  "message": "Sẵn sàng · google-genai · gemini-2.5-flash"
}
```

### `POST /api/ai-scan/analyze`

`multipart/form-data`:

| Field | Kiểu | Ghi chú |
| --- | --- | --- |
| `front` | file | ảnh chính diện, JPG/PNG/WebP, ≤ 10 MB |
| `side` | file | ảnh nghiêng 90°, khác ảnh front |
| `height_cm` | float | 100–230 |
| `consent` | bool | bắt buộc `true` |
| `capture_mode` | `upper_body` \| `full_body` | mặc định `upper_body` |

Response `200` (rút gọn):

```json
{
  "status": "completed",
  "provider": "google-genai",
  "model": "gemini-2.5-flash",
  "capture_mode": "upper_body",
  "measurements": {
    "height_cm": 170,
    "chest_cm": 95.0,
    "waist_cm": 77.0,
    "hip_cm": null,
    "shoulder_width_cm": 39.0
  },
  "details": [
    { "key": "chest_cm", "label": "Vòng ngực", "value_cm": 95.0, "source": "ai_vision_estimate" }
  ],
  "confidence": 0.72,
  "pose_quality": "good",
  "notes": "...",
  "warnings": [],
  "elapsed_seconds": 6.42,
  "source": "ai_vision_estimate"
}
```

Lỗi: `400` (consent/ảnh trùng/ảnh lỗi), `413` (quá 10 MB), `422` (AI không ước lượng được
số đo nào), `502` (lỗi model), `503` (thiếu key/dependencies), `504` (quá 90 giây).

**Quyền riêng tư:** backend chỉ giữ bytes trong bộ nhớ, base64 hoá để gọi Gemini, không ghi
file, không lưu job/DB. Kết quả AI không được tự động lưu vào hồ sơ hình thể.

---

## 5. UI

- Màn hình `/scan` mặc định mở **AI Vision · Beta**; vẫn có nút chuyển sang **Quét 3D** để
  giữ nguyên luồng MediaPipe cũ.
- Khi chọn AI Vision, copy, consent và nút hành động đổi theo mode; nút bị vô hiệu nếu
  `/api/ai-scan/health` báo chưa cấu hình.
- Có hai cách đưa ảnh vào AI mode:
  1. **Camera trực tiếp**: dùng chung `CaptureSession` hiện tại, tự đếm ngược, chọn frame nét
     nhất, chuyển front → side rồi tự gọi AI phân tích.
  2. **Tải ảnh có sẵn**: hai ô chính diện / nghiêng 90°, hỗ trợ chọn file hoặc kéo-thả
     (JPG/PNG/WebP, ≤ 10 MB). Khi đủ hai ảnh, chiều cao hợp lệ và đã đồng ý xử lý ảnh,
     AI **tự động phân tích** ngay; không cần bấm thêm.
- Thêm **khung tư thế** (đầu/vai/eo/hông/bàn chân) trên preview camera, chuyển sang màu vàng
  khi tư thế và chất lượng ảnh đạt.
- Kết quả AI tái sử dụng `computeClientSizeAdvice` để gợi ý size và các class kết quả sẵn có;
  có nút “Quét lại bằng AI” và “Chuyển sang quét 3D”.

---

## 6. Kiểm thử đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| `pytest backend/tests/test_ai_scan.py -q` | 8 passed (health, consent, ảnh trùng, thiếu key, validate, LangGraph fake model, endpoint response) |
| `pytest backend/tests -q` | 115 passed (107 cũ + 8 mới) |
| `npm run typecheck` | pass |
| `GET /api/ai-scan/health` | `ready:true` với key đã cấu hình; `ready:false` khi thiếu key |
| `POST /api/ai-scan/analyze` với 2 ảnh QA | HTTP 200, Gemini trả số đo và confidence (đã gọi provider thật) |
| Upload UI → tự phân tích | Upload 2 ảnh fixture, tick consent → tự chuyển sang màn hình phân tích → hiển thị số đo + gợi ý size |
| `test_capture_session_e2e.cjs` | 8/8 browser scenarios passed, `pageErrors = 0`, `consoleErrors = 0` (suite chuyển sang Quét 3D để kiểm tra luồng cũ) |

Kết quả gọi Gemini thật dùng ảnh mannequin tổng hợp trong `verification/scripts/qa/`, không
phải kiểm định trên người thật.

---

## 7. Giới hạn

1. AI ước lượng **không có ground truth** và chưa được kiểm định trên người thật.
2. Chất lượng phụ thuộc ánh sáng, trang phục, góc chụp và model Gemini; kết quả có thể `null`
   hoặc bị cảnh báo.
3. Không tạo mô hình 3D, không lưu lịch sử, không thay thế `/api/scans`.
4. Chi phí và độ trễ phụ thuộc tài khoản Gemini; endpoint có timeout 90 giây.
5. Không dùng mode này cho mục đích y tế, may đo chuyên nghiệp hoặc nhận diện danh tính.

---

## 8. Nhật ký phiên

Xem [`docs/SESSION_AI_SCAN_2026-10-19.md`](./SESSION_AI_SCAN_2026-10-19.md) để biết toàn bộ
dependency đã cài, các file đã thêm/sửa, bug fix vòng lặp render và kết quả kiểm chứng.
