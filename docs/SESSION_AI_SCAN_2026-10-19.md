# Nhật Ký Phiên Làm Việc — AI Vision Scan & Upload ảnh (19/10/2026)

Tài liệu này tổng hợp toàn bộ thay đổi đã thực hiện trong phiên làm việc ngày **19/10/2026**:
cài dependency, thêm tính năng quét bằng AI (Gemini + LangChain + LangGraph), upload ảnh,
khung tư thế, sửa lỗi vòng lặp render và các kiểm chứng đi kèm.

> Phạm vi: **bổ sung**, không thay thế pipeline 3D MediaPipe. AI Vision là mode mặc định của
> `/scan`, nhưng người dùng vẫn chuyển về **Quét 3D** bất cứ lúc nào.

---

## 1. Quyết định & phạm vi

| Hạng mục | Lựa chọn đã chốt |
| --- | --- |
| Model AI | Google Gemini qua `langchain-google-genai` |
| Orchestration | LangGraph (`analyze → validate → finalize`) |
| Kết quả AI | Số đo ước lượng + gợi ý size (tái sử dụng logic size hiện có) |
| Mode mặc định | **AI Vision · Beta**; vẫn giữ **Quét 3D** |
| Upload ảnh | Chỉ cho AI Vision; không thêm upload cho quét 3D |
| Phân tích | Tự động sau khi đủ 2 ảnh (camera hoặc upload) |
| API key | Người dùng tự đặt trong `backend/.env`; không commit |

---

## 2. Dependency đã cài

### Backend (Python)

Đã cài vào `backend/.venv`:

```text
langchain==1.4.6
langgraph==1.2.16
langchain-google-genai==4.4.2
python-dotenv==1.2.4
```

Khai báo tách riêng trong [`backend/requirements-ai.txt`](../backend/requirements-ai.txt) để
pipeline 3D không bắt buộc phải cài AI extras.

Cài lại:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-ai.txt
```

`pip check`: **No broken requirements found**.

### Frontend / E2E

- Cài `playwright@1.64.1` vào `frontend/devDependencies`.
- Tải Chromium + headless shell + FFmpeg cho Playwright.
- Thêm [`verification/scripts/playwright-runtime.cjs`](../verification/scripts/playwright-runtime.cjs)
  để resolve Playwright từ `frontend/node_modules`.
- Bỏ các đường dẫn hard-code của máy khác trong 15 script E2E:
  - Playwright path → `require('./playwright-runtime.cjs')`.
  - Root `D:/MORPH-AI` → `path.resolve(__dirname, '..', '..')`.
  - `benchmark_scan_api_and_load.py`: `PLAYWRIGHT_MODULE` → đường dẫn local.

---

## 3. Backend — package `backend/app/ai_scan/`

### Cấu trúc

```text
backend/app/ai_scan/
├── __init__.py      # export ai_scan_router
├── config.py        # GOOGLE_API_KEY / GEMINI_API_KEY, MORPH_AI_MODEL, backend/.env
├── prompts.py       # prompt hệ thống + prompt 2 ảnh
├── schemas.py       # VisionMeasurementEstimate, AiScanResponse
├── graph.py         # LangGraph analyze -> validate -> finalize
├── service.py       # ChatGoogleGenerativeAI + chạy graph + map lỗi
└── router.py        # GET /api/ai-scan/health, POST /api/ai-scan/analyze
```

`router.py` chỉ import config/schemas ở module level; LangChain được import **lazy** trong
`service.py`. Vì vậy backend 3D vẫn khởi động bình thường nếu chưa cài AI dependencies.

### Luồng LangGraph

```text
START
  └─ analyze    Gemini vision, structured output
  └─ validate   loại giá trị bất khả thi, ép hip=null ở upper_body, thêm cảnh báo
  └─ finalize   đóng gói measurements + provenance ai_vision_estimate
END
```

- `analyze`: gửi 2 ảnh base64 + chiều cao + `capture_mode` tới Gemini.
- `validate`: không tự sửa số đo; giá trị ngoài khoảng sinh lý → `null` + warning; tỷ lệ bất
  thường so với chiều cao → warning + giảm confidence.
- `finalize`: trả `AiScanResponse`, không tạo mô hình 3D.

### API

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/api/ai-scan/health` | `ready`, provider, model, message; không lộ key |
| `POST` | `/api/ai-scan/analyze` | `front`, `side`, `height_cm`, `consent`, `capture_mode` |

- Ảnh ≤ 10 MB, phải khác nhau, JPG/PNG/WebP.
- Ảnh chỉ nằm trong bộ nhớ; **không ghi đĩa**, **không lưu job/DB**.
- Timeout 90 giây.
- Lỗi: `400` consent/ảnh lỗi, `413` quá dung lượng, `422` AI không ước lượng được,
  `502` lỗi model, `503` thiếu key/deps, `504` timeout.

### Cấu hình môi trường

Tạo `backend/.env` từ `backend/.env.example`:

```env
GOOGLE_API_KEY=<key Google AI Studio>
MORPH_AI_MODEL=gemini-2.5-flash
```

Không dùng ngoặc kép, không `<...>`, không `export`. `backend/.env` đã được `.gitignore`.
Nếu đang đứng trong thư mục `backend/`, dùng:

```powershell
Copy-Item .env.example .env
```

Nếu đang ở thư mục gốc project:

```powershell
Copy-Item backend/.env.example backend/.env
```

> ⚠️ **Bảo mật:** trong phiên này key từng bị in ra terminal/chat do thao tác kiểm tra file.
> Cần **thu hồi (rotate) key cũ** tại Google AI Studio và chỉ cập nhật key mới trong
> `backend/.env`. Không đưa key vào tài liệu, commit hoặc chat.

---

## 4. Frontend

### File mới

```text
frontend/lib/useAiScan.ts                     # health + analyze + state
frontend/components/ai-scan/AiScanResult.tsx  # kết quả số đo + gợi ý size
frontend/components/ai-scan/AiPhotoUpload.tsx # upload 2 ảnh + tự phân tích
frontend/components/shop/PoseGuide.tsx        # khung tư thế SVG
```

### File hiện có được sửa (theo hướng bổ sung)

- `frontend/components/shop/FitExperience.tsx`
  - AI Vision là mode mặc định.
  - Nút chuyển **AI Vision / Quét 3D**.
  - State upload 2 ảnh + effect tự động gọi AI khi đủ ảnh, chiều cao hợp lệ và đã consent.
  - Reset/retry upload; copy consent/privacy theo mode.
- `frontend/components/shop/CaptureSession.tsx`
  - Prop `aiMode` (badge, nhãn bước).
  - Render `PoseGuide`; logic chụp/đếm ngược/best-frame giữ nguyên.
- `frontend/app/capture-flow.css`
  - Style mode switch, AI result, pose guide, upload panel, responsive mobile.
- `frontend/lib/ScanContext.tsx`
  - `setJob` idempotent (xem mục 5).
- `backend/app/main.py`
  - Import + include `ai_scan_router` (2 dòng, additive).
- `verification/scripts/test_capture_session_e2e.cjs`
  - Vì AI là mặc định, suite chủ động bấm **Quét 3D** trước khi test luồng cũ.

### Hai cách quét trong AI Vision

1. **Camera trực tiếp**
   - Dùng `CaptureSession`: tự đếm ngược, chọn frame nét nhất, chụp chính diện → nghiêng 90°.
   - Sau ảnh thứ hai, tự gọi `/api/ai-scan/analyze`.
   - Khung tư thế chuyển vàng khi tư thế/chất lượng ảnh đạt.
2. **Upload ảnh**
   - Hai ô: **Chính diện** và **Góc nghiêng 90°**.
   - Chọn file hoặc kéo-thả; hỗ trợ JPG/PNG/WebP ≤ 10 MB.
   - Preview + xóa từng ảnh.
   - Khi đủ 2 ảnh + chiều cao hợp lệ + consent → **tự động phân tích**.
   - Lỗi AI giữ nguyên ảnh đã chọn và có nút **Thử phân tích lại**.

### Kết quả AI

- Hiển thị số đo ngực/eo/mông/vai, confidence, pose quality, cảnh báo.
- Gợi ý size bằng `computeClientSizeAdvice` sẵn có (không nhân bản logic).
- Nút **Quét lại bằng AI** và **Chuyển sang quét 3D**.
- Luôn hiển thị nhãn thử nghiệm, chưa kiểm chứng trên người thật, không dùng cho may đo.

---

## 5. Sửa lỗi `Maximum update depth exceeded`

### Triệu chứng

- React báo tối đa update depth tại `ScanContext.tsx`.
- Countdown/scan bị kẹt, UI re-render liên tục.

### Nguyên nhân

`FitExperience` đồng bộ job vào context bằng:

```tsx
useEffect(() => {
  if (s.job) scanContext.setJob(s.job);
}, [s.job, scanContext]);
```

`scanContext` là object mới mỗi lần provider render → effect chạy lại liên tục. `setJob` lại
luôn tạo `adviceCache`/`guestTokens` mới → vòng lặp setState.

### Cách sửa

- `FitExperience`: dependency chỉ còn setter ổn định `[s.job, scanContext.setJob]`.
- `ScanContext.setJob`:
  - `setJobState` trả về nguyên reference nếu job không đổi.
  - Chỉ clear `adviceCache` khi cache đang có dữ liệu.
  - Không tạo object `guestTokens` mới nếu token đã tồn tại.

---

## 6. Kiểm chứng đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| `pytest backend/tests/test_ai_scan.py -q` | **8 passed** |
| `pytest backend/tests -q` | **115 passed** (107 cũ + 8 mới) |
| `npm run typecheck` | **pass** |
| `test_capture_quality.cjs` | **16/16 passed** |
| `test_capture_session_e2e.cjs` | **8/8 scenarios passed**, `pageErrors=0`, `consoleErrors=0` |
| `GET /api/ai-scan/health` | `ready:true`, model `gemini-2.5-flash` |
| `POST /api/ai-scan/analyze` với ảnh QA | **HTTP 200**, Gemini trả số đo thật |
| Upload UI → tự phân tích | **thành công**: hiển thị số đo + gợi ý size |
| `pip check` | No broken requirements |
| `git diff --check` | pass (chỉ còn warning line-ending của Git) |

Ví dụ kết quả gọi Gemini thật với ảnh mannequin tổng hợp trong `verification/scripts/qa/`:

- Chế độ `upper_body`, chiều cao 170 cm.
- Ngực 82–88 cm, eo 62–68 cm, vai 39–40 cm.
- Mông `null` (đúng quy tắc `upper_body`).
- Confidence ~0.85.

Đây là ảnh tổng hợp, **không phải kiểm định trên người thật**.

---

## 7. Tài liệu liên quan

- [`docs/AI_SCAN_FEATURE.md`](./AI_SCAN_FEATURE.md) — kiến trúc, API, cấu hình, UI, giới hạn.
- [`docs/API_CONTRACT.md`](./API_CONTRACT.md) — mục 7: API AI Vision.
- [`docs/HANDOFF.md`](./HANDOFF.md) — mục 6 & 7: trạng thái tính năng và bug fix.
- [`backend/requirements-ai.txt`](../backend/requirements-ai.txt)
- [`backend/.env.example`](../backend/.env.example)

---

## 8. Cách chạy

```powershell
# 1. Cài dependency AI (nếu chưa)
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-ai.txt

# 2. Cấu hình key
Copy-Item backend/.env.example backend/.env
# Mở backend/.env, điền GOOGLE_API_KEY

# 3. Chạy backend + frontend
powershell -ExecutionPolicy Bypass -File start-backend.ps1
powershell -ExecutionPolicy Bypass -File start-frontend.ps1
```

Mở http://127.0.0.1:3000/scan — AI Vision là mode mặc định.

---

## 9. Giới hạn & việc cần làm tiếp

1. **Chưa có ground truth trên người thật**: kết quả AI chỉ là ước lượng thị giác; cần cohort
   người thật có consent để đánh giá sai số.
2. **Chưa kiểm thử trên nhiều webcam vật lý**: ánh sáng, méo góc rộng, rolling shutter có thể
   ảnh hưởng kết quả.
3. **Phụ thuộc Gemini**: chi phí, độ trễ, quota và thay đổi model của nhà cung cấp.
4. **Rate limiting cho AI**: endpoint hiện chưa có giới hạn concurrency/rate riêng; nên bổ sung
   nếu mở public.
5. **Rotate key**: key từng bị lộ trong log phiên này; cần thu hồi và cập nhật key mới.
6. **Không dùng cho may đo/y tế** hoặc nhận diện danh tính.

---

## 10. Trạng thái cuối phiên

- Frontend: http://127.0.0.1:3000/scan — HTTP 200.
- Backend: http://127.0.0.1:8000 — `/api/ai-scan/health` trả `ready:true`.
- AI Vision + camera auto-analyze + upload auto-analyze hoạt động.
- Quét 3D cũ vẫn hoạt động và được kiểm chứng bằng E2E 8/8.
