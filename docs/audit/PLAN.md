# PLAN — Sửa lỗi “phình theo từng vòng”

> Căn cứ: chỉ 4 tài liệu [`K0_map.md`](K0_map.md), [`K1_apply.md`](K1_apply.md),
> [`K2_measure.md`](K2_measure.md), [`K3_bump.md`](K3_bump.md). Không đọc lại code.
> Định nghĩa lỗi: mô hình có các “gờ/bậc” ngang đúng tại các vòng số đo
> (ngực/eo/mông) hoặc tại các dải phụ (cổ/đùi/bắp chân/cổ chân), nhìn như từng vòng bị phình.

---

## 1. Nguyên nhân gốc rễ — xếp hạng theo khả năng

| Hạng | Nguyên nhân | Bằng chứng từ K0–K3 | Khả năng |
|---:|---|---|---|
| 1 | **Fit từng vòng bằng PCHIP**: mỗi vòng được scale riêng, nội suy giữa các mốc, lặp 4 lần; đạo hàm bậc hai đổi dấu tại đúng mốc | K1 §4 (4 vòng lặp, không dừng theo sai số); K2 §3 (target elip vs polygon); K3 §4: đỉnh tại `0.50/0.60/0.72 H`; K3 §5: fit thêm 0,4–0,5 cm `d2` ở ngực/hông | **Cao** |
| 2 | **Mốc hông quá thấp (~0.50 H)**: hông lấy max tới fraction `1.12`, rơi xuống trên đùi thay vì mốc xương `0.534 H` | K2 §1.2; K3 §4: đỉnh hông ở `0.48–0.56 H`, nữ gầy 14,6 cm | **Cao** |
| 3 | **Hình dáng base Anny + local changes** đã có gờ ở eo/cổ/bàn chân; fit không tạo ra các gờ này | K3 §5: base đã có eo 8,58 cm, cổ 8,57 cm; fit gần như không đổi; K3 §6 | **Cao** (góp phần, không phải “theo vòng”) |
| 4 | **Band `proportions`** (cổ/đùi/bắp chân/cổ chân) scale theo cửa sổ cosin, mỗi bên chân một tâm, có thể tạo shelf ở biên dải | K1 §1.3; K3 §5: +prop làm đùi 0,13→0,64, bắp chân 1,63→1,86; K3 §6 nói nhỏ nhưng không bằng 0 | **Trung bình** |
| 5 | **Smooth + refit**: Laplacian có volume constraint rồi fit lại; làm đỉnh cổ tăng gần gấp đôi | K3 §5: cổ 8,56 → **14,78** khi full; K3 §6 | **Trung bình** (chủ yếu ở cổ/vai) |
| 6 | **Sai định nghĩa target**: target là elip + hệ số giải phẫu, mesh đo bằng polygon; ép polygon bằng elip có thể làm phình cục bộ, nhất là khi `aspect_corr` lệch | K2 §1, §3; K1 §4 | **Trung bình** |
| 7 | **Hằng số `0.29` ở `upper_body`** thay vì span thật `0.271`, đặt vòng hông lệch | K1 §3.3 | **Thấp–Trung bình** (chỉ upper_body) |
| 8 | **Độ phân giải lưới + lấy mẫu 2 cm** làm gờ trông sắc hơn; không phải nguyên nhân gốc | K3 §0, §7 (giới hạn đo) | **Thấp** |

**Kết luận ngắn:** lỗi là hệ quả của **mô hình biến dạng theo vòng** (ring-wise scaling), không phải
một lỗi đơn lẻ. Hai yếu tố trực tiếp tạo “phình đúng vòng” là fit PCHIP từng mốc và mốc hông bị hạ
xuống đùi; base Anny và smoothing làm gờ rõ hơn ở eo/cổ.

---

## 2. Nguyên tắc sửa

1. **Không phá số đo**: ngực/eo/mông vẫn khớp target (sai số ≤ 0,5 cm); chiều cao, chân `y=0`,
   `mesh_validation.valid` vẫn đạt.
2. **Không đổi API** ở các bước đầu; nếu đổi định nghĩa số đo phải tăng `engine_version` và
   ghi rõ trong `measurement_details`/tài liệu.
3. **Mỗi bước tối đa 3 file**, có số đo trước/sau trên đúng 3 case K3 và render QA.
4. **Rollback được**: giữ nhánh/commit riêng từng bước; asset `.npz` đánh version.

---

## 3. Kế hoạch sửa từng bước

### Bước 1 — Chốt baseline và ngưỡng nghiệm thu (không sửa production)

- **File (3):** `tools/diag/build_and_scan.py`, `tools/diag/analyze.py`, `tools/diag/thresholds.json`.
- **Việc làm:** đóng băng số liệu 3 case (đã có), thêm ngưỡng máy đọc được:
  `max|d2|` tại `.50/.60/.72/.855`, `max_fit_error_cm`, chiều cao, số vòng.
- **Nghiệm thu:** chạy lại 2 lần cho cùng kết quả (sai khác <0,01 cm); lưu `baseline.json`.
- **Rollback:** chỉ là tool, không ảnh hưởng app.

### Bước 2 — Đưa mốc hông về đúng giải phẫu

- **File (3):** `backend/app/measurements.py`, `backend/app/reconstruction.py`,
  `backend/tests/test_photo_measurements.py`.
- **Thay đổi đề xuất:**
  - Giới hạn candidate hông trong khoảng ~`0.95–1.02` fraction, hoặc lấy max trong cửa sổ
    `hip_level ± 0.03 H`, thay vì tới `1.12` (K2 §1.2).
  - Bỏ hằng số `0.29` ở `upper_body`, dùng `shoulder_level/hip_level` thật (K1 §3.3).
- **Nghiệm thu:**
  - `level` của hông nằm trong `[0.52, 0.545] H` cho cả 3 case;
  - `max|d2|` vùng `0.45–0.52 H` giảm ≥ 25% so với baseline;
  - ngực/eo/eo không lệch quá 0,5 cm; fit `≤ 0,5 cm`; `mesh_validation.valid = true`;
  - test cũ pass, thêm test khẳng định mốc hông.
- **Rủi ro:** số đo hông thay đổi (thường giảm 2–5 cm) → phải tăng engine version, ghi rõ.

### Bước 3 — Fit mượt toàn cục thay vì từng vòng

- **File (3):** `backend/app/measurements.py`, `backend/app/reconstruction.py`,
  `backend/tests/test_measurements.py`.
- **Thay đổi đề xuất:** thay PCHIP knots cứng ở 3 mốc bằng trường scale mượt toàn thân
  (RBF/Gaussian theo chiều cao hoặc polynomial bậc thấp có ràng buộc), hoặc tăng vùng chuyển tiếp
  quanh mỗi mốc; giữ nguyên vòng lặp fit nhưng giới hạn biến thiên giữa 2 vòng liên tiếp.
- **Nghiệm thu:**
  - `max|d2|` tại `.60` và `.72` ở case nam béo giảm ≥ 30% (từ 27,6 và 5,5 cm);
  - case nam trung bình không tệ hơn baseline quá 10%;
  - chu vi vẫn khớp `≤ 0,5 cm`, không tạo đỉnh mới > baseline ở cổ/đầu;
  - thời gian dựng không tăng quá 30%.
- **Rollback:** giữ hàm cũ sau flag `fit_mode="pchip"|"smooth"`.

### Bước 4 — Sửa smoothing gây bậc ở cổ/vai

- **File (3):** `backend/app/reconstruction.py`, `backend/app/measurements.py`,
  `backend/tests/test_reconstruction.py`.
- **Thay đổi đề xuất:** thay Laplacian volume-constraint hiện tại bằng Taubin/Laplacian có ràng buộc
  vùng (không kéo cổ), hoặc giảm biên độ và bỏ refit toàn phần; kiểm tra lại chu vi sau smooth.
- **Nghiệm thu:**
  - `max|d2|` vùng `0.82–0.86 H` của case nam trung bình ≤ 10 cm (hiện 14,8) và không tăng so với
    base quá 20%;
  - `max_fit_error_cm ≤ 0,5`; chiều cao sai ≤ 0,015 m; chân `y=0`;
  - không tạo đỉnh mới > baseline ở eo/ngực.
- **Rủi ro:** giảm smoothing làm lộ gờ khác; cần so render 3 case.

### Bước 5 — Làm mượt các band phụ (proportions)

- **File (3):** `backend/app/proportions.py`, `backend/app/reconstruction.py`,
  `backend/tests/test_proportions.py`.
- **Thay đổi đề xuất:** mở rộng cửa sổ chuyển tiếp, dùng một trường scale liên tục thay vì 4 dải
  rời; với chân, dùng cùng một tâm/scale cho cả hai bên thay vì scale từng bên.
- **Nghiệm thu:**
  - `max|d2|` tại `.405/.235` không tăng quá 10% so với base;
  - các vòng cổ/đùi/bắp chân/cổ chân vẫn thay đổi đúng hệ số (sai ≤ 0,5 cm so với kỳ vọng);
  - không có seam nhìn thấy trên render 3 case.
- **Rollback:** giữ `apply_rings` cũ sau flag.

### Bước 6 — Xử lý base Anny/local changes (nếu bước 3–5 chưa đủ)

- **File (3):** `verification/scripts/build_anny_bases.py`, `backend/app/anny_body.py`,
  `backend/models/anny-bases.npz` (asset version mới).
- **Thay đổi đề xuất:** giảm/loại local change gây gờ (breast/buttocks/hip), hoặc tăng mật độ lưới
  bằng subdivision trước khi nướng; giữ nguyên chân `y=0`, cao 1.
- **Nghiệm thu:**
  - `d2` nền ở eo/cổ giảm ≥ 20% so với base cũ;
  - 6 avatar QA nhìn không mất giải phẫu; fit 3 case vẫn `≤ 0,5 cm`;
  - dung lượng `.npz` không tăng quá 2×.
- **Rủi ro:** đổi toàn bộ avatar, phải re-baseline QA và kiểm tra giấy phép asset.

### Bước 7 — Đồng bộ định nghĩa đo scan ↔ mesh

- **File (3):** `backend/app/measurements.py`, `backend/app/report.py`,
  `backend/tests/test_photo_measurements.py`.
- **Thay đổi đề xuất:** bỏ hệ số elip `k` tuỳ ý; hiệu chỉnh target bằng chính mặt cắt polygon của
  base (hoặc báo cáo cả `model_cm` cạnh `value_cm`); ghi rõ nguồn/định nghĩa.
- **Nghiệm thu:**
  - chênh lệch target và `model_cm` ≤ 1 cm trên 3 case;
  - số đo hiển thị không đổi quá 1 cm so với baseline (trừ khi có quyết định đổi định nghĩa);
  - API/`measurement_details` vẫn giữ 5 nhãn nguồn.

### Bước 8 — Regression, version, tài liệu

- **File (3):** `backend/tests/test_refit.py`, `backend/app/reconstruction.py` (bump version),
  `docs/HANDOFF.md`.
- **Việc làm:** chạy toàn bộ test + 3 case + render; tăng `ENGINE` lên v7 nếu đổi định nghĩa;
  ghi kết quả thật, không hứa độ chính xác.
- **Nghiệm thu:** toàn bộ test pass; 3 case đạt ngưỡng bước 2–7; `npm run typecheck` pass;
  ảnh render trước/sau lưu `output/runs/qa-...`.

---

## 4. Thứ tự & ước lượng

| Thứ tự | Bước | Ước lượng | Phụ thuộc |
|---:|---|---:|---|
| 1 | Baseline/thresholds | 0,5 ngày | — |
| 2 | Mốc hông | 1–2 ngày | B1 |
| 3 | Fit mượt | 2–3 ngày | B2 |
| 4 | Smoothing | 1–2 ngày | B3 |
| 5 | Band proportions | 1–2 ngày | B4 |
| 6 | Base Anny | 2–4 ngày | B3–B5 |
| 7 | Đồng bộ định nghĩa | 2–3 ngày | B2–B4 |
| 8 | Regression/version | 1 ngày | tất cả |

Tổng: **~2–3 tuần** cho 1 dev, chưa tính validate người thật.

---

## 5. Rủi ro và giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| **Giấy phép model**: Anny Apache-2.0 + asset MPFB2 CC0; MakeHuman code AGPL nhưng asset CC0; SMPL/SMPL-X **phi thương mại**; MHR Apache-2.0; SAM 3D Body dùng SAM License (không phải open-source) | Cao nếu đổi model | Giữ Anny; lập manifest license; không đưa SMPL-X vào sản phẩm; rà `THIRD_PARTY_NOTICES` trước khi phát hành |
| **Mất tương thích số đo**: đổi mốc hông/định nghĩa làm số cũ và size advice lệch | Cao | Tăng `engine_version`; đánh dấu scan cũ; không trộn trong cùng biểu đồ; thông báo UI |
| **Vỡ API/history**: `body_scans`, `measurement_details`, so sánh scan | Trung bình | Giữ schema; thêm field; migration; test parity |
| **Smoothing làm sai chu vi** | Trung bình | Luôn refit và kiểm `max_fit_error_cm`; rollback nếu >0,5 |
| **Base mới làm mất giải phẫu/QA** | Trung bình | Giữ basis cũ làm fallback; so 6 avatar; version asset |
| **Quá khớp 3 case synthetic** | Cao | Thêm 10–20 archetype + validate người thật; dùng render và số đo thước dây |
| **Số đo hông giảm khi sửa mốc** | Cao | Truyền thông thay đổi; so sánh trước/sau; không tự chọn size gần nhất |
| **Hiệu năng CPU** (fit mượt, subdivision) | Trung bình | Đo thời gian; cache; giới hạn lưới |
| **Rủi ro pháp lý khi phân phối basis** | Trung bình | Giữ attribution/metadata; kiểm tra điều khoản Anny/MPFB2 |
| **Test/QA flaky** | Thấp | Chạy trên máy idle; lưu baseline JSON; so sánh số |

---

## 6. Quyết định cần chốt trước khi làm

1. **Có chấp nhận đổi số đo hông** (thường giảm 2–5 cm) để đúng giải phẫu không? Nếu không,
   chỉ sửa hình học mà giữ nguyên số báo cáo, và ghi rõ mô hình không khớp số.
2. **Ưu tiên “đẹp mắt” hay “đúng số”** khi hai mục tiêu xung đột? K3 cho thấy base đã có gờ;
   muốn hết hẳn có thể phải thay base/subdivision (B6).
3. **Có ngân sách validate người thật** (thước dây, 10–20 người) để biết sửa nào thực sự đúng?
4. **Có được phép tăng kích thước asset/kích thước lưới** (subdivision) không?

> Tất cả kết luận trên chỉ dựa trên 4 tài liệu audit; chưa đọc lại code và chưa chạy thêm thí nghiệm.
