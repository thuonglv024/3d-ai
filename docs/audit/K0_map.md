# K0 — Bản đồ dự án: từ số đo đến mô hình 3D

> Mục đích: bản đồ đọc hiểu, **không sửa code**. Thời điểm lập: 2026-10-23.
> Phạm vi: luồng tạo mô hình 3D từ 2 ảnh webcam + số đo; không đi sâu vào cửa hàng/thanh toán.

---

## 1. Cây thư mục 2 cấp

Đã bỏ qua: `node_modules/`, `.git/`, `backend/.venv/`, `.next/`, `.next-review/`, `__pycache__/`,
`backend/.anny-cache/`, `output/`, `backend/runtime/`, `backend/data/`, các file ảnh/model lớn.

```text
morph3d-ai/
├─ backend/
│  ├─ app/                     # toàn bộ xử lý phía server
│  │  └─ ai_scan/              # nhánh AI Vision (Gemini/LangGraph)
│  ├─ models/                  # pose_landmarker_full.task, body-template.obj,
│  │                           # anny-bases.npz/json
│  ├─ scripts/                 # prepare_assets.py, import_catalog_media_v2.py
│  └─ tests/                   # 19 file test + conftest.py
├─ frontend/
│  ├─ app/                     # route Next.js: /, /scan, /products, /account...
│  ├─ components/
│  │  ├─ shop/                 # FitExperience, CaptureSession, ScanResult...
│  │  └─ ai-scan/              # AiPhotoUpload, AiScanResult
│  ├─ lib/                     # useBodyScan, ScanContext, fitMap, catalog...
│  └─ public/                  # ảnh sản phẩm, sample-body.obj
├─ docs/                       # tài liệu kỹ thuật (xem mục 4)
├─ verification/
│  └─ scripts/                 # QA, benchmark, build_anny_bases.py, E2E
├─ design/                     # ảnh tham chiếu thiết kế
├─ AGENTS.md                   # quy tắc cho agent
├─ README.md
├─ setup.ps1                   # cài Python/venv/asset
├─ start-backend.ps1           # uvicorn :8000
├─ start-frontend.ps1          # next dev :3000
└─ start-all.bat / stop-all.bat
```

Ghi chú: `backend/data/` chứa file `.glb` tạm của từng phiên quét; `backend/runtime/` chứa SQLite
(`orders.db`) và dữ liệu runtime — cả hai đều là dữ liệu sinh ra, không phải mã nguồn.

---

## 2. Các file liên quan tới việc biến số đo thành mô hình 3D

Cách tìm: grep `makehuman|modifier|measure|mesh|\.obj|\.glb|gender|shape` trên
`backend/app`, `backend/scripts`, `verification/scripts`, `frontend/components`, `frontend/lib`,
`frontend/app`, sau đó đọc các file có mật độ khớp cao nhất.

### 2.1. Backend — lõi dựng hình

| File | Mô tả 1 dòng |
|---|---|
| `backend/app/reconstruction.py` | Điều phối toàn bộ: MediaPipe → chiều cao → profile 2 ảnh → dựng lưới nền → khớp số đo → xuất GLB; chứa cả `refit_avatar()` khi người dùng sửa số đo. |
| `backend/app/measurements.py` | Toán học số đo: chu vi elip/giải phẫu, `estimate_from_profiles()`, cắt lát `closed_torso_section()`, `fit_measurement_targets()` và kiểm định lưới. |
| `backend/app/anny_body.py` | Đọc basis Anny đã nướng sẵn, chọn phenotype theo giới/cân nặng/cơ, nội suy và trả lưới nền 13.718 đỉnh. |
| `backend/app/anatomy.py` | Phân giải giới, prior tỷ lệ nam/nữ (`shape_sex`), chia độ sâu trước/sau, đọc mốc xương từ `body-template.obj`. |
| `backend/app/proportions.py` | Hệ số cho các vòng phụ (cổ/đùi/bắp chân/cổ chân) ăn theo ngực/hông và scale lưới theo dải. |
| `backend/app/report.py` | Tạo 12 dòng số đo kèm nguồn (`photo_estimate`, `template_model`, `user_input`…), cảnh báo và đường đo 3D. |
| `backend/app/camera_fusion.py` | Ghép 2 góc chụp: đồng bộ mốc, dùng chung tỷ lệ cm/pixel, trích profile rộng–sâu. |
| `backend/app/main.py` | API FastAPI: `POST /api/scans`, `GET /api/scans/{id}`, `/model`, `PATCH /api/scans/{id}/measurements`; chạy `reconstruct()` trong thread pool. |
| `backend/app/config.py` | Đường dẫn `backend/models`, `backend/data`, giới hạn upload. |
| `backend/app/images.py` | Decode JPG/PNG/WebP, xoay EXIF, chuẩn hoá RGB, giới hạn kích thước. |
| `backend/app/fitmap.py` | Từ số đo + bảng size/số đo may → ước lượng chật/sát/vừa/rộng theo vùng (không tạo mesh). |
| `backend/app/ai_scan/*` | Nhánh AI Vision: Gemini ước lượng số đo từ 2 ảnh; không dựng mesh, chỉ cung cấp số đo và nút chuyển sang luồng 3D. |

### 2.2. Tài nguyên mô hình

| File | Mô tả 1 dòng |
|---|---|
| `backend/models/anny-bases.npz` | 12 lưới nền đã nướng sẵn từ Anny 0.6.1 (giới × cân nặng × cơ), ~1,9 MB. |
| `backend/models/anny-bases.json` | Metadata/giấy phép của basis Anny (Apache-2.0 + asset MakeHuman CC0). |
| `backend/models/body-template.obj` | Lưới MakeHuman gốc (CC0): nguồn mốc xương `g joint-*` và là fallback khi thiếu basis Anny. |
| `backend/models/pose_landmarker_full.task` | Model MediaPipe Pose Landmarker (CPU). |
| `backend/scripts/prepare_assets.py` | Tải/chuẩn bị `body-template.obj` khi setup. |
| `verification/scripts/build_anny_bases.py` | Sinh `anny-bases.npz` từ Anny (chạy offline, cần torch/warp). |
| `verification/scripts/qa_export_avatars.py` | Xuất 6 avatar QA (3 archetype × nam/nữ) để so sánh engine. |
| `verification/scripts/render_avatar_qa.py` | Render avatar QA ra PNG để kiểm tra hình dáng. |

### 2.3. Frontend — hiển thị và điều khiển

| File | Mô tả 1 dòng |
|---|---|
| `frontend/lib/useBodyScan.ts` | Gửi 2 ảnh + chiều cao lên `/api/scans`, poll trạng thái job, giữ job/measurements. |
| `frontend/lib/ScanContext.tsx` | Context toàn cục: job hiện tại, cache gợi ý size, lưu scan vào hồ sơ, mở modal thử đồ. |
| `frontend/components/shop/CaptureSession.tsx` | Luồng camera: đếm ngược, chụp chính diện → xoay 90° → chụp nghiêng, kiểm tra tư thế. |
| `frontend/components/shop/FitExperience.tsx` | Modal "Tìm size": chọn AI Vision/Quét 3D, nhập chiều cao, gọi scan và render kết quả. |
| `frontend/components/shop/ScanResult.tsx` | Màn hình kết quả: bảng 12 số đo, sửa số đo, bản đồ độ vừa, nhúng `BodyViewer`. |
| `frontend/components/BodyViewer.tsx` | Three.js/R3F: tải GLB, xoay/zoom, tô dải màu độ vừa, vẽ đường đo. |
| `frontend/components/shop/FitMapPanel.tsx` | Panel chọn size và hiển thị chật/sát/vừa/rộng theo vùng. |
| `frontend/lib/fitMap.ts` | Gọi `POST /api/fit-map`. |
| `frontend/components/shop/ProductDetail.tsx` | Trang sản phẩm: chọn size, mở FitExperience, hiện gợi ý size. |
| `frontend/components/ai-scan/AiScanResult.tsx` | Kết quả AI + nút "Dựng mô hình 3D từ hai ảnh này" → chuyển sang luồng scan. |
| `frontend/components/ai-scan/AiPhotoUpload.tsx` | Chọn/kéo 2 ảnh cho nhánh AI Vision. |
| `frontend/lib/catalog.ts` | Kiểu dữ liệu sản phẩm/size chart; có `garment_specs` cho 2 áo thun mẫu. |

### 2.4. Tài liệu & kiểm thử liên quan

| File | Mô tả 1 dòng |
|---|---|
| `docs/ARCHITECTURE.md` | Kiến trúc tổng thể frontend/backend/database. |
| `docs/SCAN_QUALITY.md` | Pipeline 3 tầng, mốc giải phẫu, giới hạn kỹ thuật. |
| `docs/API_CONTRACT.md` | Hợp đồng API và cấu trúc `Job`. |
| `docs/HANDOFF.md` | Trạng thái hiện tại, các thay đổi theo phiên. |
| `docs/BODY_MODEL_AND_FIT_RESEARCH.md` | Nghiên cứu chọn Anny/MHR/SAM 3D, lộ trình thử đồ. |
| `backend/tests/test_reconstruction.py` | Test MediaPipe/mask, `deform_template`, end-to-end GLB. |
| `backend/tests/test_measurements.py`, `test_photo_measurements.py` | Test chu vi, fit chu vi, validate GLB. |
| `backend/tests/test_anny_body.py`, `test_anatomy.py`, `test_proportions.py` | Test basis Anny, prior giới, hệ số vòng phụ. |
| `backend/tests/test_refit.py` | Test dựng lại avatar khi sửa số đo. |
| `verification/scripts/evaluate_3d_scan_accuracy.py` | Benchmark hình học 3 tầng. |

---

## 3. Luồng dữ liệu: số đo → mô hình 3D

### 3.1. Luồng chính (2 ảnh webcam)

```text
[Trình duyệt]
  CaptureSession (chụp 2 góc)
        │  File front + File side + height_cm + sex
        ▼
  useBodyScan.scan()
        │  POST /api/scans  (multipart)
        ▼
[FastAPI]
  main.create_scan()
        │  tạo Job(queued), đưa vào ThreadPoolExecutor
        ▼
  main.process()
        │  reconstruct(front, side, height_cm, path, report, capture_mode, sex)
        ▼
  reconstruction.reconstruct()
        │
        ├─ 1. observe(front), observe(side)
        │      MediaPipe Pose + Segmentation → landmarks, mask, top/bottom
        │      (ảnh được align_mask_width + chuẩn hoá RGB)
        │
        ├─ 2. estimate_upper_body_height()            [chế độ upper_body]
        │      hoặc bottom-top                         [chế độ full_body]
        │
        ├─ 3. fuse_camera_scale() + synchronized_torso_profile()
        │      → fractions[], widths[] (ảnh trước), depths[] (ảnh nghiêng)
        │
        ├─ 4. estimate_from_profiles(fractions, widths, depths, height_cm, ...)
        │      → measurements{chest_cm, waist_cm, hip_cm, shoulder_width_cm}
        │      → targets[] {key, level, target_cm, width_cm, depth_cm}
        │
        ├─ 5. resolve_sex() → "female" | "male" (auto hoặc người dùng chọn)
        │
        ├─ 6. anny_body.phenotype_from_measurements()
        │      → weight (từ eo/chiều cao), muscle
        │      anny_body.build(sex, weight, muscle, height_cm)
        │      → lưới nền 13.718 đỉnh          ── fallback ──► deform_template()
        │                                                   (MakeHuman .obj + shape_sex)
        │
        ├─ 7. proportions.ring_scales() + proportions.apply_rings()
        │      → scale cổ/đùi/bắp chân/cổ chân theo ngực/hông
        │
        ├─ 8. fit_measurement_targets(mesh, targets, height_cm)
        │      4 vòng PCHIP, scale_lateral → 3 vòng khớp target (0,00 cm)
        │
        ├─ 9. smooth_avatar()
        │      Laplacian 1 lượt + fit lại để không đổi chu vi
        │
        ├─ 10. measurement_report()  → 12 dòng số đo kèm nguồn
        │      validate_glb_mesh()   → kiểm tra mét, chân y=0, mặt cắt
        │      mesh.export(backend/data/{job_id}.glb)
        ▼
  Job completed { measurements, body_profile, model_url }
        │
        ▼
[Trình duyệt]
  useBodyScan.poll()  GET /api/scans/{id}
        ▼
  ScanResult
        ├─ bảng số đo + bản đồ độ vừa
        └─ BodyViewer
              GET /api/scans/{id}/model  → GLTFLoader → Three.js
```

### 3.2. Luồng sửa số đo (không cần ảnh gốc)

```text
ScanResult.saveEdits()
   │ PATCH /api/scans/{id}/measurements {chest_cm?, waist_cm?, hip_cm?, height_cm?}
   ▼
main.patch_measurements()
   │ đọc Job.fitting (targets + profile ảnh + basis + levels)
   ▼
reconstruction.refit_avatar()
   │ chuẩn hoá target theo giá trị mới (giữ tỷ lệ W/D)
   │ build lại lưới nền → proportions → fit_measurement_targets → smooth_avatar
   │ measurement_report(overrides) → ghi đè GLB → revision += 1
   ▼
Job trả về → frontend setJob() → BodyViewer tải GLB?v=revision
```

### 3.3. Vai trò thực tế của MakeHuman trong code hiện tại

- **Mặc định**: lưới nền là **Anny** — mô hình tham số Apache-2.0 xây trên asset MakeHuman/MPFB2 (CC0).
  `anny-bases.npz` được sinh sẵn bởi `build_anny_bases.py`; runtime không import Anny/torch.
- **MakeHuman trực tiếp**:
  - `backend/models/body-template.obj` — lưới MakeHuman gốc, dùng để đọc mốc xương
    (`template_landmarks`) và làm fallback.
  - `deform_template()` trong `reconstruction.py` — biến dạng lưới MakeHuman theo profile 2 ảnh,
    kèm `shape_sex()` (prior nam/nữ) khi không có basis Anny.
- Vì vậy, nếu tài liệu mô tả "dựng bằng MakeHuman", cần hiểu: **MakeHuman là nguồn lưới/asset**,
  còn lớp dựng hiện tại là Anny (dựa trên MakeHuman) + phép khớp số đo.

### 3.4. Đường nhánh AI Vision (không tạo mesh)

```text
AiPhotoUpload (2 ảnh)
   ▼
POST /api/ai-scan/analyze  → LangGraph (analyze → validate → finalize)
   ▼
AiScanResult (số đo ước lượng)
   ▼  nút "Dựng mô hình 3D từ hai ảnh này"
FitExperience.onBuild3D
   ▼  dùng chính 2 file ảnh đó
POST /api/scans → luồng 3.1
```

---

## 4. Điểm neo để đọc code nhanh

| Việc cần tìm | Vị trí |
|---|---|
| API nhận scan | `backend/app/main.py::create_scan` (dòng ~272) |
| Chạy dựng hình | `backend/app/main.py::process` (~213) → `reconstruction.reconstruct` (~478) |
| Ước lượng số đo | `backend/app/measurements.py::estimate_from_profiles` (~43) |
| Khớp mesh theo số đo | `backend/app/measurements.py::fit_measurement_targets` (~212) |
| Dựng lưới nền | `backend/app/anny_body.py::build` (~97) |
| Fallback MakeHuman | `backend/app/reconstruction.py::deform_template` (~324) |
| Hệ số vòng phụ | `backend/app/proportions.py::ring_scales` (~35), `apply_rings` (~78) |
| Sửa số đo | `backend/app/main.py::patch_measurements` (~351) → `refit_avatar` (~400) |
| Xuất GLB | `reconstruction.py` (~579) `mesh.export(..., "glb")` |
| Tải GLB ở UI | `frontend/components/BodyViewer.tsx::Result` (~117) |

---

## 5. Ghi chú phạm vi

- Bản đồ này chỉ mô tả luồng hình học 3D; phần catalog/thanh toán/auth không đi sâu.
- Không có thay đổi mã nguồn nào được thực hiện khi lập bản đồ.
- Số đo vẫn là **ước lượng từ ảnh**, chưa kiểm chứng bằng thước dây trên người thật;
  các dòng `template_model` và vòng phụ chỉ dùng để mô tả hình thể, không dùng chọn size.
