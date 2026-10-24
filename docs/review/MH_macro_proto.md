# MH_macro_proto — thử dùng macro MakeHuman làm base thay Anny

Phạm vi: chỉ đọc/viết trong `tools/diag/`, `tools/mh_proto/`; không sửa production, không commit.

## Phần A — chẩn đoán code hiện tại

### A1. `build_anny_bases.py` tạo base bằng tham số nào

- Macro (`phenotype_kwargs`): `gender 0/1`, `age 0.5`, `muscle 0.35|0.6`, `weight 0.3|0.5|0.7`, `height 0.5`, `proportions 0.5`.
- Local changes (không phải measure modifier): nữ `breast/buttocks/hip` yếu (0.05–0.15), nam `vshape/pectoral/shoulder/buttocks` yếu (0.02–0.25) — `build_anny_bases.py:40-55`.
- **Cùng topology**: nam và nữ đều `13.718` đỉnh, `27.420` mặt, `faces` giống hệt (dùng chung một `faces`).
  Chứng minh: `tools/mh_proto/inspect_anny.py` → 12 key đều `(13718,3)`; `faces=(27420,3)`.

### A2. Nơi phụ thuộc topology/landmark của Anny (file:dòng)

| Nơi | Phụ thuộc | file:dòng |
|---|---|---|
| Loader | key `sex|weight|muscle`, `faces` cố định | `backend/app/anny_body.py:37-46`, `97-107` |
| Vòng fit | 3 mốc `chest .72 / waist .60 / hip .5334` | `reconstruction.py::build_from_measurements` (vừa thêm); `proportions.RINGS` |
| Mốc vai/hông/cổ | `shoulder .805 / hip .534 / neck .855` | `reconstruction.py` (levels); `report.py` |
| Dải phụ | `.855/.405/.235/.065`, chân `x 0.02–0.17`, fade `.47` | `proportions.py:17-25`, `_leg_centres` |
| Báo cáo | vòng đầu `.955`, cổ `.855`, đùi `.405`, bắp `.235`, cổ chân `.065`, tâm chi `.055/.06` | `report.py:115-123` |
| Fallback MakeHuman | landmark từ `body-template.obj` (`joint-*`) | `anatomy.py:85-129`; `reconstruction.py` dùng mốc này cho cả Anny |

**Ước lượng ánh xạ lại nếu đổi base khác topology:** ~**6 file production** (`anny_body`, `measurements`, `reconstruction`, `proportions`, `report`, `anatomy`) + **4 file test** (proportions/photo_measurements/anny_body/refit) — chủ yếu là các hằng số mốc chiều cao, không phải chỉ số đỉnh cứng.

### A3. Giới tính đi qua đâu; hằng số dùng chung

- Chuỗi: `main.create_scan` `sex` → `Job.sex` → `process` → `reconstruct(sex)` → `resolve_sex` → `anny_body.build(sex,…)` → `_interp` chọn key theo `sex`.
- Fallback: `shape_sex()` trong `anatomy.py:155` (dùng `_LATERAL`, `_VOLUMES` đang rỗng).
- Hằng số dùng chung hai giới: `chest .72/waist .60/hip .5334`, `shoulder .805/hip .534/neck .855`, `RINGS`, `report` levels, `ANATOMICAL_SECTION_FACTORS`.

## Phần B — prototype

### B4. Môi trường

- **Không có** `bpy`, `mpfb`, `makehuman` (`find_spec == None`).
- **Có** `anny` (NAVER Labs Europe; asset MPFB2/MakeHuman CC0). `anny.Anny(local_changes="none")` = chỉ macro, `local_change_labels=0`.
- `phenotype_labels` = `gender, age, muscle, weight, height, proportions` — **không có chủng tộc/race**.
- Cần người dùng cung cấp nếu muốn MakeHuman thật: file `.obj`/target export từ MakeHuman + bảng ánh xạ macro (age→giá trị 0..1, race nếu có).

### B5. Bake (proxy macro-only qua Anny)

`tools/mh_proto/bake_macro.py` → `tools/mh_proto/out/{male,female}_macro.npy` + `faces.npy`.
Macro: `gender 0/1, age .5, muscle .6, weight .5, height .5, proportions .5`, `local_changes={}`.
Kết quả: cả hai `(13718,3)`, `faces (27420,3)` — vẫn là topology Anny.

### B6. So sánh macro vs Anny hiện tại (170 cm)

| Sex | Base | d2 .50 | .60 | .72 | .855 | vai/hông | eo/hông | đỉnh/mặt |
|---|---|---|---|---|---|---|---|---|
| nam | macro | 7.937 | 12.046 | 3.919 | 8.665 | 1.200 | .775 | 13718/27420 |
| nam | anny | 7.922 | 11.845 | 3.555 | 8.718 | 1.244 | .774 | 13718/27420 |
| nữ | macro | 1.664 | 0.888 | 4.247 | 24.072 | 1.520 | .866 | 13718/27420 |
| nữ | anny | 1.643 | 0.865 | 4.296 | 24.035 | 1.482 | .858 | 13718/27420 |

- `d2` gần như **bằng nhau**; macro **không ít gờ hơn** Anny (nam eo macro 12.05 vs Anny 11.85; nữ cổ ~24 cả hai).
- Tỉ lệ giải phẫu chênh lệch nhỏ, đều hợp lý.

### B7. Kết luận

1. **Không nên đổi base sang macro-only Anny**: gờ (`d2` eo/cổ) vẫn y nguyên vì nó nằm trong hình học nền MPFB2/MakeHuman, không phải do local changes hay `gender/weight`.
2. **Chi phí ánh xạ topology**: về vertex/face là **0** nếu vẫn dùng topology Anny (nhưng không có lợi); nếu dùng export MakeHuman thật (topology khác) thì phải ánh xạ lại ~6 file production + 4 file test.
3. **Khuyến nghị: DỪNG** với macro MakeHuman cho mục tiêu giảm gờ; muốn giảm gờ cần subdivision/retopology hoặc base khác (không nằm trong allowlist hiện tại).
