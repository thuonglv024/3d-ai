# Trạng Thái Bàn Giao Hiện Tại (Project Handoff)

Tài liệu này tổng hợp trạng thái hiện tại của dự án **MORPH AI**, các thay đổi vừa hoàn thành, các giới hạn kỹ thuật cần lưu ý và danh sách công việc tiếp theo dành cho kỹ sư hoặc AI Agent kế nhiệm.

---

## 0. Cập nhật 2026-10-31 — Pilot thật P01b, spec áo A03, lớp AI

### 0.11. PHẦN 2–3 — try-on 3 cột, heatmap 3 mức, giải thích size (2026-11-01)
- **Sản phẩm ORICANO**: thêm lại `ao-thun-oricano-nam` từ fixture thật (`verification/fixtures/garments/oricano-shirt.json`)
  vào seed backend và catalog frontend → **163 sản phẩm / 1.701 biến thể / 30 bảng size**. ½ ngực 41–49 (chu vi áo
  82–98), vai áo 38–42, dài áo 61–69, tay áo 17–21 cho S–2XL. Bảng vòng cơ thể trong catalog là **suy ra**
  (chu vi áo trừ ease 2–10 cm), gắn `source=derived_from_flat_spec` + cảnh báo trong modal bảng size; fit-map dùng
  `chest_flat_cm` (basis `garment_flat_spec`) và trả `no_garment_data` cho eo (bảng hãng không có số đo eo).
- **Bố cục try-on 3 cột** (`ScanResult`): `22% | 48% | 30%`, cao `clamp(560px, 100dvh - 220px, 900px)`, mỗi cột tự cuộn.
  Trái: tủ đồ (API, ưu tiên món có `garment_specs`, tối đa 24 món thân trên). Giữa: stage 3D nền `#141312`. Phải:
  sản phẩm + size + bảng số (kèm nguồn) + heatmap + giải thích. Đo thực tế: 1024 → 207/452/283 px; 1280 → 264/575/359;
  1440/1920 → 271/590/369. `scrollWidth == clientWidth` ở cả 4 mức (không cuộn ngang); dưới 1024 xếp dọc.
- **Heatmap 3 mức (chỉ UI)**: ease lấy từ `/api/fit-map`, **không đổi công thức backend**. Chật <0; Vừa 0–+2;
  Rộng >+2; thiếu số đo áo → xám. Màu khác cả độ sáng (`#7a2a1e` / `#3f7d55` / `#a9cbe0` / `#8b9188`) nên phân biệt
  được khi nhìn mù màu. Chỉ tô dải ngực/eo trên thân áo; tay áo và dưới gấu để xám; quần/váy không tô.
  P01b + Oricano M: ngực **+2,9 cm → Rộng**; eo **Thiếu dữ liệu**.
- **Giải thích size** (`POST /api/fit/explain`): một node LangGraph riêng trong `ai_scan/fit_explain.py`, temperature 0,
  timeout 15 s, cache theo `(size, ease_chest, ease_waist)`. Prompt cấm đề xuất/đổi size và cấm tạo số; hậu kiểm từ chối
  mọi số không khớp ease đầu vào, câu >300 ký tự hoặc JSON sai → fallback tất định. 429/503/timeout/không có key →
  fallback, **không retry vòng**, luôn HTTP 200 với `source = "ai" | "fallback"`. UI hiện nhãn "AI giải thích" hoặc
  "Giải thích tự động", basis ease từng mốc và câu "không đề xuất size khác".
- **Số thực tế**: gọi endpoint với `{size: M, chest 2,9, waist null}` → `source=fallback`, `fallback_reason=ai_error`
  sau ~2,9 s (model hiện lỗi với key này, xem 0.6); câu: “Size M: Ngực áo rộng hơn cơ thể 2,9 cm nên rộng. Eo chưa có
  số đo áo nên chưa kết luận.”
- **QC**: `pytest backend/tests -q` → **270 passed** (thêm 5 test Oricano + 9 test explain); `npx tsc --noEmit` sạch;
  `GET /scan` → 200; ảnh `output/qa/tryon-1280.png`, `tryon-1280-full.png`, `tryon-1920.png`, `tryon-1920-full.png`,
  `tryon-panel-1280.png`, `tryon-panel-1920.png`.
- **Chưa kiểm được / giới hạn**: (a) nhánh AI chưa từng trả kết quả trên key hiện tại — mọi ảnh chụp là fallback;
  (b) ảnh chụp lấy qua một trang tạm chỉ để nạp job đã quét vào `ScanProvider` (app không có khôi phục scan theo URL)
  rồi chuyển sang `/scan`; trang tạm đã xóa, ảnh vẫn là `ScanResult` thật; (c) tủ đồ giới hạn 24 món thân trên;
  (d) ví dụ 3.3 (“4 cm nên vừa”) mâu thuẫn ngưỡng 2.2 (0–+2 = vừa) — đã theo ngưỡng 2.2 nên 4 cm → “rộng”.

### 0.10. PHẦN 1 — nguồn từng số đo + tắt chu vi tay (2026-11-01)
- **Tắt chu vi bắp/cẳng tay**: `arm_metrics.ARM_GIRTHS_ENABLED = False`. Biên dạng gồm cả tay áo và chưa có
  bước trừ hao trang phục (C2), nên hai số này không phải số đo cơ thể. P01b trước đây báo cẳng tay **29,3 cm**
  (tape 20, +9,3) với `source=photo_estimate`, `valid_for_sizing=True`; nay `bicep_cm`/`forearm_cm` = **None**,
  nguồn `unavailable`, lý do ở `profile["arm_unavailable_reason"]`. Chỉ `arm_length_cm` được báo.
  Bật lại bằng `measure_arm_girths(..., enabled=True)` sau khi C2 có dữ liệu.
- **Cổng hợp lệ cho tương lai** (`enabled=True`): `radii_px` có dữ liệu; mặt cắt vuông góc **không chạm thân**
  (`torso_mask.point_in_torso_run`); bề rộng mặt cắt **4–16 cm** (bán kính 2–8 cm). Dữ liệu P01b: bắp tay
  41,5 cm, một phía ăn 36 cm vào thân → None; cẳng tay 9,32 cm, hai phía 5,29/4,03 cm (không chạm thân) →
  nếu bật cổng vẫn ra 29,3 cm. Vì vậy việc tắt là do **thiếu C2**, không phải cổng hình học.
- **Nguồn từng mốc**: `profile["sources"]` (key → source) và `profile["unavailable"]` (key → lý do) dựng từ
  `measurement_details` (`_attach_provenance` trong `reconstruction.py`, dùng cho cả `reconstruct` và `refit_avatar`).
  Mốc `template_model`/`unavailable` bị đặt `measurements[key] = None` — mesh vẫn dựng nội bộ bằng template nhưng
  số không được xuất như số đo cơ thể. `report.py`: giá trị None không còn mang nhãn `photo_*`; lý do cụ thể
  (eo/vai/tay) nằm trong `quality_warnings`.
- **Sửa kèm**: `arm_length_cm` trước bị hard-code `None`/`unavailable` dù pipeline tính được (P01b **45,3 cm**);
  nay báo `photo_estimate` (observed_region `frontal_arm_landmarks`) khi có số.
- **Frontend** (`ScanResult.tsx`): nhãn "Đo từ ảnh / Đo từ ảnh + tỷ lệ mẫu / Mô hình mẫu / Chưa đo được",
  tooltip lý do, banner "Kết quả chưa dùng được ảnh cho: …". Banner chỉ xét mốc dùng để chọn size
  (ngực/eo/hông/vai/bắp-cẳng tay/dài tay); đầu/cổ/đùi/bắp chân luôn thuộc mẫu nên không tính.

| Mốc P01b | Trước | Sau | Tape | Nguồn sau |
| :--- | ---: | ---: | ---: | :--- |
| Ngực | 83,1 | 83,1 | 80 | photo_estimate |
| Eo | — | — | 60 | unavailable + lý do |
| Hông | 94,6 | 94,6 | 92 | photo_estimate |
| Vai | 38,4 | 38,4 | 40 | photo_estimate (`silhouette`) |
| Dài tay | — (hàng báo None) | **45,3** | — | photo_estimate |
| Bắp tay | — | — | 23 | unavailable (C2) |
| Cẳng tay | **29,3** | **—** | 20 | unavailable (C2) |

- **QC**: `pytest backend/tests -q` → **256 passed** (thêm 4 test: tắt C2, mặt cắt chạm thân, bề rộng ngoài
  4–16 cm, nguồn/lý do khi thiếu số); `npx tsc --noEmit` sạch; `GET /scan` → 200, `GET /` → 200.
- **Chưa kiểm được**: chưa xem banner/nhãn trên một phiên quét thật trong trình duyệt (cần job có kết quả);
  `tape_eval` chỉ chạy trên P01b, không phải tuyên bố độ chính xác. Chu vi tay vẫn **không có** cho tới C2.

### 0.1. Việc đã làm (đều nằm trong commit ngày 2026-10-31 trên `feature/3d-scan`)
- **AI scan 4 estimator**: 3 lượt `gemini-2.5-flash` (role `anchor`/`shape`/`audit`, temperature 0.35) chạy song song
  với 1 estimator hình học MediaPipe (`backend/app/ai_scan/geometry.py`) trên chính hai ảnh đó; gộp bằng median,
  hợp nhất theo ngưỡng (`ensemble.py`), rồi guard nhân trắc học (`priors.py`).
- **Tách tay khỏi silhouette** (`backend/app/torso_mask.py`) + **fit map dùng số đo áo phẳng thật**
  (`backend/app/garment_fit.py`, quy ước `chu vi = 2 × rộng phẳng`) + **heatmap ease liên tục theo từng đỉnh**
  (`backend/app/fit_field.py`, `frontend/lib/viewerConfig.ts`).
- **Eval trên người thật đầu tiên**: `scripts/eval/eval_pilot.py` (chỉ đọc `backend/app`, ghi ra `output/eval_pilot/`).
- **Lớp prior sửa chính sách**: mặc định chỉ *cảnh báo*, không sửa số. Shrink về prior là tuỳ chọn
  (`MORPH_AI_PRIOR_SHRINK=1`), và khi bật thì mọi số bị đổi hiện trong `warnings` (`96.0 -> 94.8 cm`) kèm
  `estimated_by = "ensemble+prior"`. Lý do: chưa có tập hiệu chuẩn, prior tự đặt sẽ bóp méo cả số đúng —
  trên P01 (tape eo 60 cm, cao 156 cm) prior nữ `0.45 × 156 = 70.2` sẽ đẩy eo đúng lên ~63 cm.

### 0.2. Số đo được (không phải tuyên bố độ chính xác)
`backend/.venv/Scripts/python.exe -m pytest backend/tests -q` → **212 passed** (trước đó 161; có 22 test mới cho
`ensemble`/`priors`/`geometry`/prompt trong `backend/tests/test_ai_scan_layers.py`).

Pilot P01b (1 người, 156 cm, tape ngực 80 / eo 60 / hông 92, mặc áo len dày):

| Vòng | Tape | Pipeline trước (A) | Sau (A) | Lệch sau | Trước (B) | Sau (B) | Lệch sau |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ngực | 80 | 137.6 | 89.8 | +9.8 (+12.2%) | 130.2 | 99.9 | +19.9 (+24.9%) |
| Eo | 60 | 89.3 | 86.6 | **+26.6 (+44.3%)** | 86.6 | 74.0 | +14.0 (+23.3%) |
| Hông | 92 | 102.7 | 100.5 | +8.5 (+9.2%) | — | 91.1 (`mesh_cut`) | — |

(A = ảnh gốc, B = ảnh crop thân trên; số đọc từ `output/eval_pilot/eval_pilot.json`.)

### 0.3. Giới hạn phải nói rõ khi demo
- **n = 1**, một bộ đồ, **không có cân nặng**, không có protocol đo thước dây, landmark tape không ghi
  (xem `backend/data/pilot_selfie/ground_truth.json`). Chỉ là hướng đi, không phải độ chính xác.
- **Eo vẫn lệch +26.6 cm (44.3%)** — chưa sửa, nguyên nhân chưa chứng minh. Nghi phạm: depth từ ảnh nghiêng gần
  phẳng (spread 0.1 cm giữa ngực/eo/hông ở mode A), tức tín hiệu ảnh 90° gần như không đóng góp. **Chưa xác minh.**
- Mode B vẫn `arm_merged = true` → ngực B +24.9% vẫn nhiễm tay áo.
- Chất lượng Gemini **chưa được đo**: chưa chạy AI thật trên ảnh P01b; mọi con số test là logic, không phải accuracy.
- Bảng prior trong `priors.py` là tỉ lệ tham khảo tự đặt, **chưa dẫn nguồn ANSUR II / SizeUK** và không phải
  dữ liệu người Việt. Không được trích như dữ liệu nhân trắc học.
- 4/7 ảnh `output/eval_pilot/viewer_*.png` trùng byte ⇒ tương tác pan/zoom/resize của viewer **chưa được chứng minh**.
- Ảnh người thật nằm ở `backend/data/pilot_selfie/` (đã gitignore) và `output/` (đã gitignore) — **không commit**.

### 0.7. Trạng thái kế hoạch fix (2026-11-01) — chưa hiệu chuẩn
- **Chủ trương**: 3D là nguồn số đo; AI chỉ nhận xét. Mọi số mang nhãn nguồn, không dùng hằng số bịa.
- **Đã xong**: bỏ hệ số lõm cứng (0.5), fallback AI không đội lốt hình học (0.5), vai theo silhouette (0.6),
  AI 1 lượt/temp 0 (0.6), eo bị từ chối khi depth phẳng (A), cổng khung 65% + tay dính thân (A),
  chụp 2 s đếm ngược + 3 s xoay, cắt mô hình ở 1/5 mông (`waistLevel 0.49`), `arm_length_cm` từ mốc 11-13-15,
  `scripts/eval/tape_eval.py`, `backend/app/arm_metrics.py`.
- **Số đo trên P01b (tape 80/60/92/40; tay 23/20; đùi 40,5; bắp chân 33)**: ngực **83,1 (+3,1)**,
  hông **94,6 (+2,6)**, vai **38,4 (−1,6)**, dài tay **45,3**, eo **từ chối** (ảnh nghiêng tay che thân),
  bắp/cẳng tay/đùi/bắp chân **chưa đo**.
- **Ca nam 170 cm (tape 99/88/46; 29/28; dài tay 90)**: chưa có lần chạy hợp lệ — ảnh chính diện là nửa thân
  (chạm mép), ảnh nghiêng tay duỗi ngang làm silhouette vượt ngưỡng 0,40 H nên bị từ chối đúng.
- **Cập nhật 2026-11-01 (mảng 2, bước 1–2)**: đã ẩn nút Test API khỏi màn quét (`83d2fb8`), thêm overlay
  hình người `ScanSilhouette` (SVG, mờ 40% vùng ngoài, đổi màu idle/align/ready) và gắn vào `PoseGuide`
  (`6cb1b23`, `bf35628`). `state` suy từ `aim.ok`, chưa so khớp hình dáng thật.
- **Còn thiếu của mảng 2**: (a) ảnh chụp Playwright cho 3 trạng thái, (b) silhouette co giãn theo tỉ lệ
  vai–hông, (c) tối giản `/scan` còn 1 nút chụp + 1 dòng hướng dẫn + chỉ báo 1/2–2/2.
- **Chặn dữ liệu**: A2b (bắp/cẳng tay) và C2 (trừ hao áo) cần ảnh tay rời thân và một cặp ảnh áo bó/áo rộng.
- **Còn lại theo kế hoạch**: U2 chặn thiếu vùng đo bằng landmark 23/24, U5 ẩn hông khi
  `upper_body`, A2b/A2c bắp-cẳng tay-đùi-bắp chân (mặt cắt vuông góc), C2/C3 trừ hao áo theo silhouette
  (trần 3 cm, có nhãn), K1 chạy `tape_eval` cho 2 người. K2/K3 **bị chặn**: cần ≥8 người có tape.
- **Định nghĩa xong (QC)**: P01b ngực ≤81,5 · hông ≤93,5 · vai ≥39; ca nam ngực ≤100,5 · vai 46±2 ·
  dài tay 90±3; `pytest` xanh, `tsc` sạch, `/scan` 200; mỗi bước push `fity/feature/3d-scan`.

### 0.9. Cổng thang đo, eo theo hình dáng, bật vòng tay (2026-11-01)
- **Cổng đồng thuận thang đo (`upper_body`)** — `estimate_upper_body_height`:
  tính hai mỏ neo độc lập (đầu–vai / 0,195 H và vai–hông / 0,290 H); lệch > **20%** thì
  `InvalidPhoto` kèm hướng dẫn, **không lấy trung bình**. Ngưỡng 20% lấy từ biên dữ liệu hiện có:
  P01b lệch **15,8%** (744,0 vs 642,6 px), ảnh QA `verification/scripts/qa/upper-front.png` lệch
  **17,8%** (462,7 vs 392,9 px); ca synthetic lệch 31% bị chặn (có test).
  - Hệ quả P01b: `upper_body` **qua cổng thang đo** nhưng vẫn dừng ở cổng tay dính thân như trước,
    nên vẫn chưa có bộ số `upper_body`. `full_body` không đổi.
- **Eo theo hình dáng** — `measurements.select_waist_row`:
  chọn hàng hẹp nhất **giữa hàng ngực và hàng hông** (bỏ cửa sổ cứng .52–.78); chỉ nhận khi hẹp hơn
  **cả hai bên ≥ 1,5 cm**, nếu không `waist_cm = None` kèm lý do. Hàng vẫn dùng để đặt vòng eo của
  avatar nên vẫn đủ 3 mặt cắt và mesh hợp lệ.
  - P01b: hàng hẹp nhất **82,7 cm** (fraction 0,473), chỉ kém ngực **0,45 cm** (cần ≥1,5) → **None**;
    lý do mới nêu đúng số liệu thay vì câu chung về "bề dày phẳng".
- **Bắp/cẳng tay** — `arm_metrics.measure_arm_girths`:
  chỉ chạy khi `remove_arm_capsules` tách được tay (`frontal.arm_radius_px`), cắt **vuông góc** trên
  mask gốc, bán kính ngoài **2–8 cm** → None. Hàng `bicep_cm`/`forearm_cm` đã vào `measurement_report`
  (`observed_region = frontal_arm_silhouette`), `profile["arm_measurements"]` ghi bên tay và nguồn.
  - P01b: **bắp tay None** (mặt cắt 180,5 px → bán kính 20,8 cm > 8: phép cắt lấn sang thân);
    **cẳng tay 29,3 cm (+9,3 so tape 20)** — biên dạng gồm **tay áo dài**, nên đây là "chu vi ngoài
    lớp áo", không phải da. Cảnh báo được gắn ở từng hàng.
- **Bảng trước/sau (P01b, `tape_eval.py`, full_body)**:

  | Mốc | Trước | Sau | Tape | Lệch sau |
  | :--- | ---: | ---: | ---: | ---: |
  | Ngực | 83,1 | 83,1 | 80 | +3,1 |
  | Eo | — (depth phẳng) | — (không thon) | 60 | — |
  | Hông | 94,6 | 94,6 | 92 | +2,6 |
  | Rộng vai | 38,4 | 38,4 | 40 | −1,6 |
  | Dài tay | 45,3 | 45,3 | — | — |
  | Bắp tay | — | — | 23 | — |
  | Cẳng tay | — | 29,3 | 20 | **+9,3 (tay áo)** |

- **QC**: ba số đang tốt **không đổi**; các ngưỡng **≤81,5 / ≤93,5 / ≥39 vẫn chưa đạt** vì ba bước này
  không chạm vào ước lượng vòng/shoulder `full_body` — cần C2/C3 (trừ hao áo) và hiệu chuẩn vai.
  Cẳng tay 29,3 **không đạt** chuẩn "số đo được" (là chu vi ngoài tay áo), chỉ nên đọc như upper bound
  cho tới khi có bước trừ hao trang phục cho tay.
- **Kiểm chứng**: `pytest backend/tests -q` → **252 passed** (thêm test cổng 20%, eo theo hình dáng,
  mặt cắt tay); `npm run typecheck` sạch; `/scan` 200; log `tape_eval` ở trên.

### 0.8. U1 — khung ngắm 3 mốc trên preview camera (2026-11-01)
- **Mục tiêu**: người dùng thấy đúng 3 mốc mà pipeline cần (đỉnh đầu – vai – hông) và biết mốc nào đang
  lệch, thay vì chỉ nhận một câu từ chối chung; mốc lệch thì **không cho đếm ngược/chụp**.
- **Đã làm** (`upper_body` và `full_body`):
  - `frontend/lib/captureQuality.ts`: `extractAimAnchors()` lấy đỉnh đầu bằng **ngoại suy** từ mũi + vai theo
    đúng tỉ lệ backend dùng (`0,195 H` / `0,125 H`), fallback theo span vai–hông khi mũi bị che;
    `evaluateAimFrame()` kiểm tra thứ tự 3 mốc, span vai–hông ≥ 0,20 khung, vai ngang ở góc chính diện và
    từng dải; `evaluateClientFrameQuality()` thêm `issue: "aim_frame_off"` ở ưu tiên 5 (sau cross-view,
    trước nhoè/motion) nên mất điều kiện là đếm ngược dừng như các cổng cũ.
  - `frontend/components/shop/PoseGuide.tsx`: vẽ 3 dải ĐẦU/VAI/HÔNG + 3 điểm mốc lấy từ landmark thật;
    bỏ 3 vạch Vai/Eo/Cạp quần và nhãn cũ (trùng nhãn với khung ngắm).
  - `frontend/components/shop/CaptureSession.tsx` truyền `qualityEval?.aim`; `frontend/app/capture-flow.css`
    thêm `.capture-aim-*`: vàng khi mốc nằm trong dải, cam nhấp nháy khi lệch.
- **Ngưỡng dải** (chỉ là khung ngắm, **không phải số đo**): `upper_body` đầu 0,04–0,26 · vai 0,20–0,50 ·
  hông 0,46–0,90; `full_body` 0,02–0,16 · 0,14–0,34 · 0,38–0,66; trục x 0,18–0,82 cho cả ba.
- **Kiểm chứng thật**: `node verification/scripts/test_capture_quality.cjs` → **24/24** (thêm 8 check U1);
  `npm run typecheck` sạch; `node verification/scripts/test_capture_session_e2e.cjs` → **8/8** kịch bản
  Chromium, 0 page error; ảnh `output/runs/run-20261014-v2/capture-e2e/03-front-countdown-window.png` thấy
  3 dải + 3 mốc vàng; `pytest backend/tests -q` → **236 passed**.
- **Sửa kèm (không liên quan U1)**: 2 assertion `countdownDurationMs = 5000` trong `test_capture_quality.cjs`
  đã cũ từ commit đổi 5 s → 2 s (bộ test đỏ sẵn trước U1) — cập nhật theo giá trị thật 2000 và mốc thời gian;
  `fetchFitMap()` từ chối payload thiếu `regions/overall/warnings` (trước đó `FitMapPanel` ném lỗi render,
  làm sập trang kết quả khi `/api/fit-map` trả body lạ — lộ ra ở một lần chạy E2E).
- **Giới hạn**: khung ngắm không đo gì và không thay `/api/capture-check`; khi backend từ chối, response trả
  `landmarks: []` nên 3 điểm mốc biến mất (chỉ còn 3 dải) — người dùng vẫn đọc thông báo lỗi của backend;
  đỉnh đầu là **ước lượng** từ mũi/vai, không phải landmark MediaPipe; ngưỡng dải mới kiểm bằng landmark
  tổng hợp + Chromium, **chưa thử trên người thật**.
- **Còn lại**: U2, U5, A2b/A2c, C2/C3, K1 như mục 0.7.

### 0.6. Giảm AI xuống 1 lượt + sửa rộng vai thiếu 10 cm (2026-11-01)
- **AI còn 1 lượt gọi/scan**: `ai_scan/config.py` → `DEFAULT_ENSEMBLE_SIZE = 1`, `DEFAULT_TEMPERATURE = 0.0`.
  Lý do: người dùng chỉ có hạn mức miễn phí (20 request/ngày) và muốn ít phụ thuộc AI; temperature 0 để 2 lần
  quét cùng ảnh ra cùng số. `MORPH_AI_ENSEMBLE` vẫn nâng lên tới 5 nếu cần. Docstring `service.py` đã viết lại.
- **Rộng vai thiếu ~10 cm — tìm ra nguyên nhân**: MediaPipe landmark 11/12 là **tâm khớp vai**, không phải mỏm
  cùng vai. Đo trên P01b: landmark **28,0 cm**, silhouette tại hàng vai **38,2 cm**, tape **~40 cm**.
  Sửa (`torso_mask.shoulder_span`): lấy bề rộng run chứa tâm thân tại hàng vai, chỉ fallback về landmark khi hàng
  đó không dùng được (không có run, hoặc tỉ lệ ngoài 0,16–0,32 H). Nguồn được ghi vào
  `profile["shoulder_width_source"]` = `silhouette` / `landmark`.
  Đo lại P01b: **28,0 → 38,4 cm**, source `silhouette`.
- Test: 3 test mới trong `test_torso_mask.py` (ưu tiên silhouette, fallback landmark, từ chối hàng quá rộng).
  Tổng **220 passed**.
- `backend/.env` (gitignored) đổi `MORPH_AI_MODEL=gemini-flash-latest` vì key mới không còn dùng được
  `gemini-2.5-flash` (404 "no longer available to new users"). Model mới vẫn hay trả 503 với request có ảnh +
  structured output — đây là lý do AI mode chập chờn, không phải lỗi code.
- Còn lại: eo +23,9 cm (depth gần phẳng, mốc eo), và `fuse_geometric` vẫn trộn 0,7 AI / 0,3 hình học — nên tắt
  trộn khi chỉ có 1 lượt AI, vì hình học là nguồn sai số đã biết.

### 0.5. Bỏ hệ số lõm cứng + không trả số hình học thay AI (2026-11-01)
- **Bối cảnh**: người dùng đo thật thấy ngực 91 cm bị đọc thành 101 cm (**+10 cm**); v1 (1 lượt AI) thì
  "đúng trong 1–2 cm". Đo lại trên P01b cho thấy sai số ngực tách thành 2 phần:
  ellipse 83,1 cm (+3,1 so tape 80) và **hệ số lõm cứng +8,07% thêm 6,7 cm** → 89,8 (+9,8).
  Hơn 2/3 sai số là do hằng số tự bịa trong code, không phải do đường viền.
- **Sửa 1** (`backend/app/measurements.py`): `ANATOMICAL_SECTION_FACTORS` = **1,0** cho cả 3 vòng, thêm
  `SECTION_FACTORS_CALIBRATED = False`. Chỉ bật lại khi có hệ số fit từ ≥8 người đo tape.
  Đo lại P01b ngay sau sửa (deterministic, không gọi AI): ngực **89,8 → 83,1** (+9,8 → **+3,1**),
  hông **100,5 → 94,6** (+8,5 → **+2,6**), eo 86,6 → 83,9 (**+23,9**, vẫn hỏng — nguyên nhân khác: depth phẳng).
- **Sửa 2** (`backend/app/ai_scan/service.py`): thêm `ai_supported(state)`. Khi cả 3 lượt AI lỗi, pipeline cũ vẫn
  trả `completed` với số của MediaPipe (đã quan sát: 89,8/86,6/100,5 với 3 member `error`, confidence 0,5).
  Nay `run_ai_scan` **raise `AiScanUnavailable`** kèm lỗi model thật, không đội lốt kết quả AI.
- Test: `backend/tests/test_ai_scan_fallback.py` (5 test) + cập nhật `test_photo_measurements.py`:
  mặc định k=1,0 thì `target_cm == ellipse_cm`, khoảng cách ellipse ↔ mặt cắt mesh 0,5–12 cm, và khi
  monkeypatch hệ số đã fit thì calibration đóng được khoảng cách đó. Tổng **217 passed**.
- **Chặn còn lại**: thí nghiệm A–E (`scripts/eval/ab_ai_v1_v2.py`) chưa chạy được vì key mới chỉ dùng được
  `gemini-3.8-flash`, model này trả **503 UNAVAILABLE** cho mọi request có ảnh (đã thử ảnh gốc và ảnh 512px);
  `gemini-2.5-flash` báo 404 "no longer available to new users"; key cũ hết quota 20 lượt/ngày (reset ~14 h).
- Việc tiếp theo: (1) chạy A–E khi có model vision hoạt động; (2) xử lý eo +23,9 cm (depth gần phẳng, mốc eo).

### 0.4. Việc tiếp theo (theo thứ tự)
1. Chạy AI thật trên 2 ảnh P01b (cần người dùng đồng ý gửi ảnh lên Gemini) → con số AI đầu tiên so với tape.
2. Khám depth gần phẳng (nguyên nhân sai số eo) trước khi sửa bất cứ hệ số nào.
3. Đưa landmark/pixel đã neo vào prompt + tách lớp "VLM gán nhãn hàng, code đo pixel".
4. Hiện `details[].confidence`, `ensemble`, `geometric_check` lên UI (hiện chỉ có type, chưa render).
5. Hiệu chuẩn bias (`C3`) **bị chặn**: cần 30–50 người đo thước dây. Không viết thêm code quanh chỗ này.

---

## 1. Trạng thái hệ thống hiện tại

### 1.1. Các phân hệ đã hoàn thiện và hoạt động ổn định
1. **Storefront & Catalog 162 sản phẩm**:
   - Đầy đủ 162 sản phẩm thời trang trên **5 danh mục** (Áo thun 34 — gồm 2 mẫu có số đo may công bố; các danh mục còn lại 32), có biến thể màu sắc, tồn kho theo size và bảng thông số `size_chart` riêng.
   - Giao diện Luxury Editorial (**Warm Ivory & Champagne Gold**) trên cửa hàng, kết hợp **Dark Measurement Workspace** (`#141312`) cho khu vực quét 3D và phân tích số đo.
2. **Luồng Quét 3D Camera-Only & Tự động chụp 2 góc**:
   - Chỉ sử dụng Webcam trực tiếp (không có nút tải ảnh tĩnh, không hiển thị mannequin mẫu trước khi quét).
   - Mặc định ở chế độ **Quét Thân Trên (`upper_body`)** phù hợp góc webcam laptop/PC; hỗ trợ chuyển sang **Quét Toàn Thân (`full_body`)**.
   - Tự động nhận diện tư thế qua MediaPipe, hướng dẫn căn khung trực tiếp trên video và đếm ngược chụp góc Chính diện $\rightarrow$ Nghiêng 90°.
3. **Pipeline Tối ưu hóa 3D Body Scan 3 Tầng (Vừa triển khai)**:
   - **Tầng 1 ([`backend/app/reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py) — `estimate_upper_body_height`)**: Kết hợp đa mỏ neo Đỉnh đầu $\rightarrow$ Vai (`0.195 H`) và Vai $\rightarrow$ Hông (`0.290 H`) bằng hàm Huber/Tanh giới hạn biên độ, giảm sai số `obs.height` từ $\pm 10.34\%$ xuống $\le \pm 1.20\%$.
   - **Tầng 2 ([`backend/app/camera_fusion.py`](file:///d:/MORPH-AI/backend/app/camera_fusion.py) & [`backend/app/reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py))**: Đồng bộ mốc giải phẫu `aligned_torso_landmarks` và dùng chung chiều cao tham chiếu `fuse_camera_scale` giữa 2 góc chụp, triệt tiêu hoàn toàn hiện tượng méo tỷ lệ $D/W$ (`0.00%` sai lệch) khi mốc hông góc nghiêng 90° bị trôi.
   - **Tầng 3 ([`backend/app/measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py))**: Bù trừ độ lõm giải phẫu mặt cắt ngang (`ANATOMICAL_SECTION_FACTORS`: Ngực $+8.07\%$, Eo $+3.21\%$, Hông $+6.23\%$) và khớp lưới PCHIP 4 vòng bảo toàn đồng thời chu vi (`0.00 cm` sai số khớp lưới) lẫn tỷ lệ $D/W$, với thời gian xử lý lõi chỉ `~9.67 ms` (`< 15 ms`).
4. **Minh bạch nguồn số đo & Gợi ý kích cỡ**:
   - Phân biệt rõ 5 nguồn `source`: `photo_estimate`, `photo_with_prior`, `template_model`, `user_input`, `unavailable`.
   - Trong chế độ `upper_body`, số đo phần dưới (`hip_cm`, `inseam_cm`, `thigh_cm`, `calf_cm`) không được ước lượng từ ảnh; hệ thống gắn nhãn `template_model` hoặc `unavailable` và cho phép người dùng nhập tay vào **Hồ sơ số đo (`BodyProfile`)** để tính size quần/váy chính xác.
5. **Xác thực, Lịch sử Hình thể & Đặt hàng nguyên tử**:
   - Xác thực qua session token ngẫu nhiên 256-bit lưu trong cookie `morph_session` (`HttpOnly`, `SameSite=Lax`, băm `SHA-256` trong DB), có khóa tạm thời 5 phút khi đăng nhập sai quá 5 lần.
   - Biểu đồ tiến trình số đo [`BodyChart.tsx`](file:///d:/MORPH-AI/frontend/components/shop/BodyChart.tsx) hỗ trợ trục thời gian tuyến tính, gom cụm điểm gần nhau (`< 16px`) và ngắt đoạn (`broken path`) với các chỉ số không hợp lệ để theo dõi (`valid_for_tracking === false`).
   - Đặt hàng [`POST /api/orders`](file:///d:/MORPH-AI/backend/app/orders.py) trừ kho nguyên tử (`BEGIN IMMEDIATE;`), hỗ trợ `Idempotency-Key` chống trùng đơn và bảo vệ trang chi tiết đơn khách bằng `order_token`.

---

## 2. Trạng thái Nghiệm thu Nâng cấp Scan (`run-20261014-v2`)

Xem báo cáo nghiệm thu chi tiết tại [**`SCAN_PRODUCT_READINESS.md`**](file:///d:/MORPH-AI/SCAN_PRODUCT_READINESS.md) và thư mục bằng chứng [`output/runs/run-20261014-v2/`](file:///d:/MORPH-AI/output/runs/run-20261014-v2/):

- **Phân loại rõ 4 trạng thái nghiệm thu**:
  1. **Implementation & Security Verification**: **PASSED** (`pytest` Backend `N = 107` tests; Unit Quality `N = 16` checks; Browser E2E `CaptureSession` `N = 8` kịch bản DOM/Network trên Chromium; TypeScript `0` lỗi).
  2. **Synthetic / Geometric Validation**: **PASSED (Trong phạm vi Hình học Tổng hợp)** (`N_cal = 12` subjects / `36` scans, `N_eval = 10` held-out subjects / `30` scans, LOSO-CV `N = 13` archetypes, `N = 10` kịch bản nhiễu/từ chối, `N = 160` sản phẩm catalog).
  3. **API Lifecycle & Bounded Concurrent Load Test**: **EXECUTED (Trong phạm vi Local Single-Worker CPU)** (Tách riêng In-Process `reconstruct()` Cold/Warm start với Full HTTP Lifecycle + Browser WebGL Render; chạy tải đồng thời `Concurrency = 1, 2, 4, 10` với `MAX_ACTIVE_JOBS = 8`; đo tách biệt `OS Working Set RSS` `279–309 MB` với `Python Heap tracemalloc` `71–93 MB`).
  4. **Real-Human Anthropometric Accuracy**: **CHƯA XÁC NHẬN / CHƯA NGHIỆM THU (`MISSING_EMPIRICAL_COHORT`, `N_human = 0`)** — Chỉ được kết luận Product-Ready về độ chính xác nhân trắc học sau khi có tập dữ liệu người thật có đồng ý sử dụng vượt qua các cổng mục tiêu tại [`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md).

### Các hạng mục kỹ thuật đã hoàn tất:
1. **Bảo vệ `guest_token` & chống rò rỉ token ([`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py), [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py))**:
   - Bắt buộc đối chiếu `guest_token` qua `secrets.compare_digest` trên 6 endpoints phiên khách (`403 Forbidden` khi thiếu/sai token); xóa `job.guest_token = None` sau khi user claim scan (`POST /api/user/scans/save`).
2. **Lọc nguồn `VALID_SIZING_SOURCES` đồng bộ giữa RAM và SQLite ([`backend/app/sizing.py`](file:///d:/MORPH-AI/backend/app/sizing.py), [`backend/app/main.py`](file:///d:/MORPH-AI/backend/app/main.py), [`backend/app/history.py`](file:///d:/MORPH-AI/backend/app/history.py))**:
   - Loại bỏ `template_model` và `unavailable` khi đọc từ `body_measurements`, đảm bảo scan `upper_body` luôn trả về `insufficient_measurements` (`missing = ["hip_cm"]`) cho `78/160` sản phẩm quần/chân váy cần vòng mông.
3. **Kiểm soát chất lượng Camera, Chọn Best-Frame & Kiểm thử Hành vi Trình duyệt ([`frontend/lib/captureQuality.ts`](file:///d:/MORPH-AI/frontend/lib/captureQuality.ts), [`CaptureSession.tsx`](file:///d:/MORPH-AI/frontend/components/shop/CaptureSession.tsx), [`test_capture_session_e2e.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_session_e2e.cjs))**:
   - Kiểm chứng thực tế trên trình duyệt Chromium (`8/8` kịch bản): hủy đếm ngược khi mất điều kiện, chọn đúng frame có `frameQualityScore` cao nhất trong cửa sổ `1600ms` (kiểm tra bằng giải mã pixel JPEG từ `POST /api/scans`), chuyển `front → turn → side`, chặn lệch khoảng cách đứng `> 18%`, đổi thiết bị camera, mất kết nối giữa chừng (`onended`), đóng phiên và retry (`0` track bị rò rỉ).
4. **Chuẩn hóa Provenance từng Metric & Kiểm định lưới `.glb` ([`backend/app/report.py`](file:///d:/MORPH-AI/backend/app/report.py), [`backend/app/measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py))**:
   - Bổ sung `observed_region`, `valid_for_sizing`, `valid_for_tracking`, `quality_warnings`, `engine_version`, `uncertainty_cm: None` và hàm `validate_glb_mesh()`.
5. **Quản lý Hàng đợi (`MAX_ACTIVE_JOBS = 8`), Timeout (`120s`), TTL (`MAX_STORED_JOBS = 50`) & Sửa lỗi Wishlist/Escape**.

---

## 3. Tài liệu & Bộ Harness Kiểm Định Hiện Có

- [**`SCAN_PRODUCT_READINESS.md`**](file:///d:/MORPH-AI/SCAN_PRODUCT_READINESS.md): Báo cáo nghiệm thu tổng hợp, ma trận trạng thái, kết quả E2E/Load/Validation và các cổng gating trước khi mở Pilot.
- [**`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`**](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md): Đối chiếu vị trí đo ISO 7250-1:2017 / ISO 8559-1:2017 với mốc MediaPipe (bao gồm độ chệch mốc vai `11–12` so với *Acromion*), các ngưỡng mục tiêu đề xuất cho Pilot (*Proposed Pilot Target Thresholds*), và phương pháp hiệu chuẩn khoảng dự đoán **Split Conformal Prediction / Empirical Residual Quantiles**.
- **Bộ script kiểm định trong `verification/scripts/`**:
  - [`test_capture_session_e2e.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_session_e2e.cjs) (Browser E2E cho `CaptureSession`)
  - [`test_capture_quality.cjs`](file:///d:/MORPH-AI/verification/scripts/test_capture_quality.cjs) (Unit test logic chất lượng khung hình & hình học)
  - [`benchmark_scan_api_and_load.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_api_and_load.py) (Benchmark tách biệt `reconstruct()`, toàn trình API, WebGL render, tải đồng thời & bộ nhớ RSS/Heap)
  - [`evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py) & [`benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py) (Harness kiểm định nhân trắc học & khoảng dự đoán Split Conformal).

---

## 4. Giới hạn kỹ thuật còn lại (Không được tuyên bố vượt phạm vi)

1. **Chưa có tập dữ liệu kiểm định trên người thật (`N_human = 0`)**: Độ chính xác nhân trắc học trên cơ thể người thật chưa được xác nhận; `uncertainty_cm` giữ giá trị `None`.
2. **Chưa kiểm chứng tự động trên phần cứng camera vật lý đa thiết bị**: Bài test trình duyệt dùng `canvas.captureStream(30)` xác định; các yếu tố ISP auto-exposure, rolling shutter blur trong phòng tối, méo quang học góc rộng và lỗi driver USB/OS cần kiểm thử thực địa.
3. **Độ chệch mốc vai MediaPipe `11–12` vs *Acromion* (`~2.4–4.4 cm`), độ nhạy trang phục rộng (`+8.7..+9.1 cm` khi phình `+6 px`), và độ nhạy chiều cao tự nhập (`±2.2..±3.0 cm` khi lệch `±5 cm`)**.
4. **Kiến trúc `ThreadPoolExecutor(max_workers=1)` & in-memory `jobs`**: Dưới tải đồng thời `C >= 4`, thời gian chờ hàng đợi `queue_wait_ms P95` tăng lên `12.39s – 20.90s`; vượt quá `MAX_ACTIVE_JOBS = 8` trả về `HTTP 429`.

---

## 5. Công việc đề xuất tiếp theo (Next Steps)

1. **Thu thập & Kiểm định Tập dữ liệu Người thật có Đồng ý (`N >= 35` người)**:
   - Thực hiện đo thước dây (2 người đo $\times$ 2 lần) theo [`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](file:///d:/MORPH-AI/docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md), nạp vào `verification/datasets/real_human_pilot/` và chạy [`evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py) để hiệu chuẩn khoảng dự đoán Split Conformal thực nghiệm.
2. **Kiểm thử Thực địa Camera Phần cứng**:
   - Đo kiểm trên các dòng webcam laptop (720p/1080p) và điện thoại thực tế dưới nhiều mức ánh sáng (`150–500 lux`).
3. **Tăng cường cấu hình Production**:
   - Bật `MORPH_COOKIE_SECURE=1` khi chạy HTTPS; chuyển lưu trữ trạng thái job/rate-limit sang SQLite/Redis nếu mở rộng nhiều worker process.

---

## 6. Tính năng thử nghiệm AI Vision Scan (19/10/2026)

Đã bổ sung một nhánh quét **thử nghiệm, độc lập** dùng Google Gemini qua **LangChain + LangGraph**, không thay đổi pipeline 3D mặc định.

- **Backend mới**: `backend/app/ai_scan/` (`config.py`, `prompts.py`, `schemas.py`, `graph.py`, `service.py`, `router.py`).
  - `GET /api/ai-scan/health` và `POST /api/ai-scan/analyze`.
  - LangGraph 3 bước: `analyze` (Gemini structured output) → `validate` (loại giá trị bất khả thi, ép `hip_cm = null` ở `upper_body`) → `finalize` (provenance `ai_vision_estimate`).
  - Ảnh chỉ xử lý trong bộ nhớ, không ghi đĩa, không lưu job/DB.
- **Frontend mới**: `frontend/lib/useAiScan.ts`, `frontend/components/ai-scan/AiScanResult.tsx`, `frontend/components/ai-scan/AiPhotoUpload.tsx`, `frontend/components/shop/PoseGuide.tsx`.
  - `/scan` mặc định mở **AI Vision · Beta**; vẫn giữ nút chuyển **Quét 3D**.
  - Chụp 2 ảnh bằng camera → tự phân tích; hoặc **tải 2 ảnh** (chọn file/kéo-thả, JPG/PNG/WebP ≤ 10 MB) → tự phân tích khi đủ ảnh, chiều cao hợp lệ và đã đồng ý.
  - Dùng chung `CaptureSession`, `computeClientSizeAdvice` và các class UI sẵn có.
  - Bổ sung **khung tư thế** (đầu/vai/eo/hông/bàn chân) trên preview camera, chuyển vàng khi tư thế/quality đạt.
- **Sửa file hiện có (chỉ bổ sung)**: `backend/app/main.py` (import + include router), `FitExperience.tsx`, `CaptureSession.tsx`, `capture-flow.css`.
- **Cấu hình**: `backend/requirements-ai.txt`, `backend/.env.example`; cần `GOOGLE_API_KEY` (hoặc `GEMINI_API_KEY`) trong `backend/.env`. Chưa có key thì health trả `ready:false`, UI báo chưa cấu hình và **không sinh kết quả giả**.
- **Kiểm thử**: `backend/tests/test_ai_scan.py` 8 tests pass; toàn bộ backend 115 tests pass; `npm run typecheck` pass; `test_capture_session_e2e.cjs` 8/8 scenarios pass (`pageErrors = 0`); đã gọi Gemini thật với 2 ảnh QA (HTTP 200) và chạy thử upload UI → tự phân tích → hiển thị số đo + gợi ý size.
- **Chưa xác nhận**: kết quả AI chưa có ground truth/kiểm định người thật (ảnh QA là mannequin tổng hợp). Không dùng cho may đo hoặc mục đích y tế.

Chi tiết đầy đủ: [`docs/AI_SCAN_FEATURE.md`](file:///d:/MORPH-AI/docs/AI_SCAN_FEATURE.md).

Nhật ký phiên triển khai (19/10/2026): [`docs/SESSION_AI_SCAN_2026-10-19.md`](file:///d:/MORPH-AI/docs/SESSION_AI_SCAN_2026-10-19.md).

---

## 7. Sửa lỗi vòng lặp render khi quét (19/10/2026)

- **Triệu chứng**: `Maximum update depth exceeded` tại `ScanContext.tsx` sau khi có job scan; countdown/scan bị kẹt do component re-render liên tục.
- **Nguyên nhân**: `FitExperience` đồng bộ job vào `ScanContext` trong `useEffect` với dependency là **toàn bộ object context** (`scanContext`). Object này được tạo mới mỗi lần provider render, nên effect chạy lại liên tục; `setJob` lại luôn tạo `adviceCache`/`guestTokens` mới, tạo vòng lặp setState.
- **Cách sửa**:
  - `FitExperience` chỉ phụ thuộc vào setter ổn định `scanContext.setJob`.
  - `ScanContext.setJob` trở thành idempotent: trả về cùng reference khi job không đổi, chỉ xóa `adviceCache` khi cache đang có dữ liệu, và không tạo object `guestTokens` mới nếu token đã tồn tại.
- **Kiểm chứng**: `verification/scripts/test_capture_session_e2e.cjs` chạy **8/8 browser scenarios PASSED**, `pageErrors = 0`, `consoleErrors = 0`; `npm run typecheck` pass; `test_capture_quality.cjs` **16/16**.

Nhật ký chi tiết toàn bộ phiên (dependency, tính năng, upload, bug fix, kiểm thử): [`docs/SESSION_AI_SCAN_2026-10-19.md`](file:///d:/MORPH-AI/docs/SESSION_AI_SCAN_2026-10-19.md).

---

## 8. Dáng nam/nữ & tỉ lệ giải phẫu cho mô hình 3D (21/10/2026)

- **Vấn đề**: lưới `hm08` là lưới trung tính; mọi số đo đều đổ vào cùng một hình dáng, độ sâu co giãn đối xứng nên tăng ngực là phình cả lưng, và bề rộng vai của mô hình không liên quan tới số đo vai đang báo cáo.
- **Thay đổi** (engine `mediapipe-two-photo-fit-v5`):
  - Thêm [`backend/app/anatomy.py`](file:///d:/MORPH-AI/backend/app/anatomy.py): `resolve_sex()`, `shape_sex()`, `depth_weights()` — prior tỷ lệ vai/hông/đùi, thể tích ngực và mông theo dáng, không phải nhân trắc học.
  - [`deform_template()`](file:///d:/MORPH-AI/backend/app/reconstruction.py#L319-L369) nhận `sex`, áp prior **trước** khi khớp đường viền; độ sâu chia trước/sau; cánh tay chỉ dịch một phần thay vì trôi theo thân.
  - `reconstruct()` nhận `sex` (`auto | female | male`), ghi `body_profile.sex` + `sex_source`, thêm cảnh báo minh bạch.
  - API `POST /api/scans` nhận form `sex` (mặc định `auto`); UI `/scan` có ô chọn **Dáng cơ thể** dùng chung `CustomSelect`; tiêu đề kết quả hiển thị dáng kèm nhãn "(tự động)".
- **Không đổi**: pipeline ước lượng số đo (Tier 1–3), `fit_measurement_targets` vẫn ép chu vi về `0.00 cm`, nhãn `source` và toàn bộ contract số đo giữ nguyên.
- **Kiểm chứng**: `pytest backend/tests` **123 passed** (thêm 8 test `test_anatomy.py`); `npm run typecheck` pass; `test_capture_session_e2e.cjs` 8/8 (xem `output/runs/run-20261014-v2/capture-e2e/report.json`).
- **Giới hạn**: khác biệt nam/nữ là prior dựng hình trên lưới trung tính, chưa phải mô hình thống kê học từ dân số thật; chưa kiểm định trên người thật.

---

## 9. Mốc xương, rộng vai, số đo AI mở rộng & 3D từ AI (21/10/2026)

Thực hiện trọn 5 bước đã thống nhất:

1. **Bước 0 — Baseline QA**: thêm [`verification/scripts/qa_export_avatars.py`](file:///d:/MORPH-AI/verification/scripts/qa_export_avatars.py) xuất **6 avatar** (3 archetype × nam/nữ) ra `output/runs/qa-avatars/*.glb` kèm `metrics.json` (vai, fit error, mesh validation). Dùng làm baseline so sánh mỗi lần đổi engine.
2. **Bước 1 — Giải phẫu**:
   - [`template_landmarks()`](file:///d:/MORPH-AI/backend/app/anatomy.py) đọc các nhóm `g joint-*` có sẵn trong `body-template.obj` → vai `0.805 H`, hông `0.534 H`, cổ `0.844 H`. `estimate_from_profiles()` nhận `shoulder_level/hip_level`, nên vòng đo đặt đúng mốc xương thay vì hằng số.
   - Rộng vai trở thành **width target** trong `fit_measurement_targets(..., width_targets=...)`, trộn 60% về số đo landmark (giới hạn hệ số `0.80–1.25`), không thêm dòng báo cáo.
3. **Bước 2 — Số đo AI mở rộng**: `VisionMeasurementEstimate` thêm `chest/waist/hip_width_cm` + `*_depth_cm` và `shape_confidence`; `validate` kiểm tra khoảng, tỷ lệ/chiều cao, ép hông `null` ở `upper_body`, và **cross-check** chu vi với `ellipse(W,D)×k` (lệch > 8% → cảnh báo, không sửa số). UI hiển thị thêm 6 dòng trong cùng lưới số đo.
4. **Bước 3 — 3D từ AI**: nút **Dựng mô hình 3D từ hai ảnh này** trong `AiScanResult` gọi lại `POST /api/scans` với đúng cặp ảnh AI (đã giữ trong `aiPairRef`). Mesh do MediaPipe dựng; số đo AI chỉ dùng cho size, hai nguồn không trộn.
5. **Bước 4 — Dọn nợ**: gộp `torso_profile` còn **một bản** ở [`camera_fusion.py`](file:///d:/MORPH-AI/backend/app/camera_fusion.py) (reconstruction import lại), bỏ import thừa; sửa tài liệu lệch code (đùi `0.405 H`, bắp chân `0.235 H`, cổ chân `0.065 H`; catalog **5 danh mục × 32**).

- **Kiểm chứng**: `pytest backend/tests` **126 passed** (10 test `test_anatomy.py`); `npm run typecheck` pass; `test_capture_session_e2e.cjs` 8/8; QA export 6/6 avatar `fit 0.00 cm`, `mesh_valid=True`.
- **Không đổi**: công thức ước lượng số đo, nhãn `source`, contract `/api/scans` (chỉ thêm form `sex`).
- **Giới hạn**: số đo ngang/sâu của AI vẫn là ước lượng thị giác chưa có ground truth; chưa kiểm định người thật.

### 9.1. Cấu hình `GOOGLE_API_KEY` không cần khởi động lại (21/10/2026)

- `backend/app/ai_scan/config.py` đọc lại `backend/.env` khi `mtime` thay đổi: thêm/rotate key có hiệu lực ở request kế tiếp; biến môi trường thật vẫn được ưu tiên hơn file.
- `/api/ai-scan/analyze` phân biệt lỗi xác thực: key sai/hết hạn trả `503` kèm hướng dẫn cập nhật key, không còn gộp vào `502` chung.
- `useAiScan` tự kiểm tra lại health mỗi 10 giây khi chưa sẵn sàng, nên mở trang trước khi bật backend vẫn dùng được sau đó.
- Kiểm chứng: `GET /api/ai-scan/health` → `ready:true`; `POST /api/ai-scan/analyze` với 2 ảnh QA → **HTTP 200**; upload UI → kết quả AI; nút **Dựng mô hình 3D từ hai ảnh này** → `POST /api/scans` 202 và hiện “Hình thể 3D của bạn”.

---

## 10. Triển khai mô hình nền Anny — engine `v6` (21/10/2026)

Thay lưới MakeHuman trung tính bằng **basis Anny** đã nướng sẵn, giữ nguyên toàn bộ tầng đo.

- **Vì sao nướng sẵn**: Anny (Apache-2.0, asset MPFB2 CC0) khởi tạo model mất **~3 phút / ~1 GB RAM** trên CPU và kéo theo `torch` + `warp-lang` (~1 GB đĩa). Backend chỉ đọc `backend/models/anny-bases.npz` (**1,9 MB**, 12 lưới giới × cân nặng × cơ) rồi nội suy tuyến tính; **không** import Anny/torch lúc chạy.
- **Sinh basis**: [`verification/scripts/build_anny_bases.py`](../verification/scripts/build_anny_bases.py) (`pip install -r backend/requirements-anny.txt`). Local changes: nữ ngực/mông/hông, nam V-shape + cơ vai. Metadata + giấy phép ở `backend/models/anny-bases.json`.
- **Nối vào pipeline** ([`backend/app/anny_body.py`](../backend/app/anny_body.py), [`reconstruction.py`](../backend/app/reconstruction.py)):
  - Frame chuẩn hoá: Y-up, chân `y=0`, mặt `+Z`, cao `1.0` → nhân chiều cao người dùng.
  - `weight` suy từ tỉ lệ eo/chiều cao (chỉ chọn vùng mô hình), `muscle=0.45`, giới từ `resolve_sex()`.
  - Sau đó vẫn chạy `fit_measurement_targets` (4 vòng PCHIP) + `smooth_avatar` như cũ → số đo không đổi.
  - Với Anny, **không** áp `width_targets` cho vai (mặt cắt mốc vai lẫn cánh tay A-pose); fallback MakeHuman giữ nguyên hành vi cũ.
- **Fallback**: thiếu `anny-bases.npz` → tự dùng `deform_template` như v5, kèm cảnh báo trong kết quả.
- **API**: `GET /api/health` thêm `body_model` (tên, license, lưới prior); `body_profile.body_model = "anny" | "template"`.
- **Kiểm chứng**: `pytest backend/tests` **135 passed** (thêm 7 test `test_anny_body.py`); QA 6 avatar `fit 0.00 cm`, `mesh_valid=True`, watertight 13.718 đỉnh/27.420 mặt; scan thật với 2 ảnh QA → `engine v6`, `body_model=anny`, `fit_status=matched` (chest 80,4 / waist 78,0 / hip 101,6 cm).
- **Hạn chế còn lại**:
  - Vòng "mông" đang rơi vào **0,50 H** (hàng cuối của profile), tức vùng trên đùi, nên hip rộng nhưng thấp; đây là hành vi có từ trước, cần một thay đổi riêng cho định nghĩa mốc hông.
  - Khác biệt nam/nữ là prior dựng hình, chưa kiểm định dân số; đầu/tay/chân vẫn là mô hình, không phải bản sao người dùng.
  - Chưa có số đo may (flat) cho sản phẩm nên chưa làm heatmap chật/rộng; kế hoạch ở tài liệu nghiên cứu.
- **Tài liệu nghiên cứu & lộ trình thử đồ**: [`docs/BODY_MODEL_AND_FIT_RESEARCH.md`](BODY_MODEL_AND_FIT_RESEARCH.md).

---

## 11. Bản đồ độ vừa theo vùng — GĐ0 (21/10/2026)

- **Mục tiêu**: trả lời "size này chật/rộng ở đâu" ngay trên mô hình 3D, trước khi có số đo may thật.
- **Backend** [`backend/app/fitmap.py`](../backend/app/fitmap.py):
  - `POST /api/fit-map` nhận `{ product_slug|product_id, size, measurements }` (không cần đăng nhập, không lưu DB).
  - Với mỗi vùng (`chest_cm`, `waist_cm`, `hip_cm` theo loại trang phục), lấy khoảng số đo cơ thể của size, ước lượng chu vi áo = trung điểm khoảng + ease theo nhãn `fit` (slim 4, regular 8, oversized 14 cm), rồi tính `ease_cm = chu vi áo − chu vi cơ thể` và `clearance_cm = ease/2π`.
  - Ngưỡng: woven (tight <0, snug <2, regular ≤10, loose >10 cm); dệt kim có spandex/elastane/co giãn được nới ngưỡng chật xuống −5 cm.
  - Trả `confidence: "estimated_from_size_chart"`, `verdict`, `color`, `band` (dải chiều cao chuẩn hoá) và cảnh báo cố định.
- **Frontend**:
  - [`frontend/lib/fitMap.ts`](../frontend/lib/fitMap.ts) gọi API.
  - [`frontend/components/shop/FitMapPanel.tsx`](../frontend/components/shop/FitMapPanel.tsx): chọn size, hiện từng vùng với cơ thể / khoảng size / chu vi áo ước tính / khe hở, thanh màu và chú thích.
  - [`ScanResult.tsx`](../frontend/components/shop/ScanResult.tsx) tải bản đồ khi có sản phẩm + size gợi ý; nút **Độ vừa** bật/tắt tô màu.
  - [`BodyViewer.tsx`](../frontend/components/BodyViewer.tsx) nhận `fitBands` và tô màu theo dải chiều cao (vertex colors), giữ nguyên chế độ khối/điểm/khung lưới.
  - CSS mới trong [`frontend/app/scan-result.css`](../frontend/app/scan-result.css).
- **Kiểm chứng**: `pytest backend/tests` **144 passed** (thêm 9 test `test_fitmap.py`); `npm run typecheck` pass; gọi thật `POST /api/fit-map` với số đo scan QA (chest 80,4 / waist 78,0) → size M trả `Rộng` ở cả hai vùng, `confidence=estimated_from_size_chart`; dựng thử UI bằng Playwright (`output/fitmap-preview.png`, `output/fit3d-preview.png`), **0 page error**, dải màu ngực/eo/mông hiển thị đúng trên mô hình.
- **Giới hạn**:
  - Bảng size là **khoảng số đo cơ thể**, không có số đo may (flat) hay thông số vải; ease theo nhãn fit là giả định, chưa hiệu chỉnh bằng dữ liệu trả hàng.
  - Chưa mô phỏng vải, đường may, độ rơi; chưa có thử đồ 2D.
  - Màu trên mô hình là dải chiều cao, không phải từng đỉnh theo khoảng cách áo–cơ thể thật (sẽ làm ở GĐ2 khi có số đo may).

---

## 12. Sửa số đo sau khi quét + 2 áo thun có số đo may (21/10/2026)

### 12.1. Người dùng sửa số đo và mô hình 3D được dựng lại

- **Lưu ngữ cảnh dựng hình**: `reconstruct()` ghi `body_profile.fitting` gồm profile rộng/sâu từ ảnh, giới, chiều cao, basis Anny (weight/muscle), các target chu vi và mốc xương. `process()` chép vào `Job.fitting`, nên **không cần ảnh gốc** để dựng lại.
- **`PATCH /api/scans/{key}/measurements`** (`MeasurementPatch`: `height_cm`, `chest_cm`, `waist_cm`, `hip_cm`, đều tuỳ chọn):
  - Giữ nguyên tỷ lệ W/D của ảnh: khi sửa một chu vi, `width_cm`/`depth_cm` của target được nhân cùng tỷ lệ.
  - Gọi [`refit_avatar()`](../backend/app/reconstruction.py) → dựng lại basis Anny ở chiều cao mới → `fit_measurement_targets` + `smooth_avatar` → ghi đè GLB → `revision += 1`.
  - Các dòng đã sửa đổi nguồn thành `user_input`, `observed_region = user_reported`, cảnh báo "Số đo bạn nhập lại sau khi quét…". Các dòng khác giữ nguyên nguồn ảnh.
  - `legacy` guard: thiếu token → 403; chưa hoàn tất scan → 409; không có thay đổi → 400; giá trị ngoài khoảng → 422; lỗi hình học → 400/500 có kiểm soát.
- **Frontend** ([`ScanResult.tsx`](../frontend/components/shop/ScanResult.tsx)): nút **Sửa số đo** mở form 4 ô (chiều cao/ngực/eo/mông), chỉ gửi các giá trị thay đổi; thành công thì `setJob(updated)`, gọi `onRetry()` để nạp lại tư vấn size, và URL GLB thêm `&v={revision}` để phá cache.
- **Kiểm chứng thật**: scan QA (ngực 80,4 / eo 78,0 / hông 101,6) → PATCH `chest_cm=90`, `height_cm=175` → `revision=1`, ngực báo 90,0 với nguồn `user_input`, cả 3 vòng khớp `0.00 cm`, chiều cao mesh `1.75 m`.

### 12.2. Hai áo thun có số đo may công bố

| Sản phẩm | Nguồn số đo | Spec dùng cho fit map |
| :--- | :--- | :--- |
| `ao-thun-heavy-cotton-regular` — Áo thun Heavy Cotton Regular | [Gildan 5000 spec sheet](https://www.ssactivewear.com/ShopNow/ItemSpecSheet.aspx?ID=16&ColorID=32126&LanguageCode=en) | Vòng ngực áo = 2 × rộng trải phẳng: S 91,4 · M 101,6 · L 111,8 · XL 121,9 cm; kèm dài áo, dài tay |
| `ao-thun-oversized-supima` — Áo thun Oversized Supima | [Uniqlo Unisex Supima Cotton Oversized T-Shirt](https://www.uniqlo.com/fr/en/products/E487898-000/00?colorDisplayCode=34&sizeDisplayCode=004) | Vòng ngực áo: S 122 · M 128 · L 136 · XL 144 cm; kèm dài áo, rộng vai, dài tay |

- Dữ liệu lưu trong `size_charts.table_json` dưới khoá `garment_specs` + `garment_source` (không cần migration mới); `db._reconstruct_product()` đưa `garment_specs`/`garment_source` ra API.
- `compute_fit_map()` dùng **số đo may** cho đúng vùng có spec (`basis = "garment_flat_spec"`, `confidence = "published_garment_spec"`), vùng không có spec vẫn ước lượng từ khoảng cơ thể. Cảnh báo nói rõ đây là số công bố, không phải đo lại sản phẩm.
- [`SizeChartModal`](../frontend/components/shop/SizeChartModal.tsx) hiển thị thêm bảng **Số đo may (trải phẳng)** kèm nguồn.
- Hệ quả dữ liệu: catalog 162 sản phẩm (thêm 2), 29 bảng size.

### 12.3. Kiểm chứng & giới hạn

- `pytest backend/tests` **148 passed** (thêm `test_refit.py` 3 test, `test_fitmap.py` +1 test spec); `npm run typecheck` pass; preview Playwright 0 page error (`output/scan-edit-preview.png`, `output/sizechart-spec.png`).
- Gọi thật `POST /api/fit-map` với áo Gildan size M, ngực 94 cm → áo 101,6 cm, ease 7,6 cm, "Vừa", `basis=garment_flat_spec`.
- **Giới hạn**: chỉ sửa được chiều cao/ngực/eo/mông (không sửa vai/tay); bản đã lưu trong hồ sơ không tự cập nhật sau khi sửa (cần lưu lại); số đo may là số công bố, chưa đo lại lô hàng; size chart cơ thể đi kèm 2 áo là suy ra từ spec, không phải bảng size gốc của hãng.
### 12.4. Sự cố native MediaPipe khi quét thật (21/10/2026)

- **Hiện tượng**: backend thoát đột ngột (exit 1) ngay sau một `POST /api/scans`, log TFLite: `image_frame.cc:415 Check failed: 1 == ChannelSize() (1 vs. 4)`. Đây là abort native, không bắt được bằng `try/except`.
- **Giảm thiểu**: `PoseLandmarkerOptions.num_poses` hạ từ `2` xuống `1` (UI vốn chỉ cho một người; tránh nhánh segmentation nhiều pose), và `observe()` chuẩn hoá ảnh về RGB uint8 contiguous (ảnh xám/RGBA được chuyển, layout sai bị từ chối bằng `InvalidPhoto` thay vì đưa vào MediaPipe).
- **Kiểm chứng**: sau restart, quét full_body + 3 lần upper_body liên tiếp đều `completed`, cùng PID backend, không còn crash.
- **Đánh đổi**: detector chỉ trả 1 pose nên không còn phát hiện "nhiều người trong khung" bằng số pose; khung hình nhiều người sẽ lấy người nổi bật nhất.

---

## 13. Các vòng phụ ăn theo 3 vòng chính (23/10/2026)

- **Vấn đề**: mô hình chỉ phản ứng ở ngực/eo/mông; các vòng cổ/đùi/bắp chân/cổ chân đứng yên vì phép khớp chu vi chỉ áp dụng quanh 3 mốc chính.
- **Cách làm** ([`backend/app/proportions.py`](../backend/app/proportions.py)):
  - Mỗi vòng phụ có một **hệ số tỷ lệ** với vòng dẫn: cổ `0.35 ×` thay đổi tương đối của ngực; đùi `0.60 ×`, bắp chân `0.35 ×`, cổ chân `0.15 ×` thay đổi tương đối của hông. Hệ số bị chặn trong `0.80–1.30`.
  - Trước khi khớp 3 vòng chính, mô hình nền được phóng/thu các dải quanh mốc cổ (`0.855 H`), đùi (`0.405 H`), bắp chân (`0.235 H`), cổ chân (`0.065 H`), mỗi dải rộng `±4.5% H` với chuyển tiếp cosin. Đùi/bắp chân/cổ chân được scale quanh **tâm từng chân** để không làm lệch hai chân.
  - Sau đó `fit_measurement_targets` vẫn khớp lại ngực/eo/mông chính xác (`0.00 cm`).
  - Số đo trong báo cáo được tính từ chính lưới sau khi scale, nên **con số và hình dạng luôn khớp nhau**.
  - Cùng logic áp dụng cho [`refit_avatar()`](../backend/app/reconstruction.py) khi người dùng sửa số đo.
- **Ví dụ thật** (scan QA 172 cm): ngực 80,4 / hông 101,6 → cổ 38,0 / đùi 48,5 / bắp chân 35,4 / cổ chân 23,5. Sửa ngực **95**, hông **112** → cổ **40,2** / đùi **51,8** / bắp chân **36,6** / cổ chân **23,8**; ba vòng chính vẫn đúng 95,0 / 78,0 / 112,0.
- **Minh bạch**: đây là **hệ số dựng hình**, không phải hằng số nhân trắc học; các vòng phụ vẫn mang nguồn `template_model` và cảnh báo mới trong `measurement_details` nói rõ "suy từ vòng chính theo hệ số tỷ lệ", không dùng để chọn size.
- **Kiểm chứng**: `pytest backend/tests` **152 passed** (thêm 4 test `test_proportions.py`: hệ số, clamp, scale đúng từng vòng, không đổi 3 vòng chính).
- **Giới hạn**: chưa có vòng tay (bắp tay/cẳng tay) vì cần tách cụm chi trên khỏi thân; hệ số chưa hiệu chỉnh bằng dữ liệu người thật.

---

## 14. Bước 8 — regression/version/archetype (24/10/2026)

- **Trạng thái**: `ENGINE = mediapipe-two-photo-fit-v7` (đổi ở Bước 2); basis Anny **v2-weak**
  (`anny-bases.npz`, fallback `anny-bases-v1.*`). Bước 7 (đồng bộ định nghĩa scan ↔ mesh) chưa làm.
- **Đã chạy thật**:
  - `pytest backend/tests -q`: **161 passed**.
  - `npm run typecheck`: **PASS**.
  - `python tools/diag/analyze.py --check`: **25 passed, 11 failed** — baseline S1 vẫn dưới
    ngưỡng B2–B4; đây là FAIL của ngưỡng cũ, không phải test fail.
- **3 case K3** (fit / d2 eo `.60` / d2 ngực `.72` / d2 cổ `.855`):
  - nam TB: `0.34` / `7.178` / `4.030` / `8.427`
  - nữ gầy: `0.02` / `6.819` / `3.164` / **`32.886`**
  - nam béo: `0.35` / `7.268` / `5.931` / `9.908`
- **Render**: `output/runs/qa-2026-10-24/{case}-{front,side}.png`.
- **18 archetype** (2 giới × 3 dạng × 3 chiều cao): **17/18 fit matched + valid**, 1 lỗi dựng
  `male-obese-short` 167 cm (hệ số vượt 1.40); fit error cao nhất 0.36 cm.
  - Ca xấu: `female-slim-average` và `female-average-average` có d2 eo ~`24`; nữ neck
    `27.6–35.8`; `male-average-short` eo `11.6`/cổ `11.9`; `male-slim-short` eo `11.0`/cổ `13.4`.
  - Dữ liệu: `output/runs/qa-2026-10-24/archetypes.json`.
- **Không hứa độ chính xác**: số đo vẫn là ước lượng từ ảnh, chưa validate thước dây; 3 case K3
  không đại diện toàn bộ không gian; các ca nữ neck/eo cao cho thấy gờ nền vẫn còn.
- Chi tiết đầy đủ: [`docs/fix/S8.md`](fix/S8.md).


