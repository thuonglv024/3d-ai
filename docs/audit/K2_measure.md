# K2 — Đo số đo trên scan và trên mesh 3D

> Phạm vi: chỉ đọc các file trong mục “liên quan” của [`K0_map.md`](K0_map.md).
> Không sửa code. Mọi kết luận kèm `file:dòng`.

## Kết luận ngắn

- **Số đo từ scan** không phải chu vi của một lát cắt thật; nó là **chu vi elip xấp xỉ** dựng từ
  bề rộng silhouette (ảnh trước) và bề sâu silhouette (ảnh nghiêng), nhân thêm hệ số bù giải phẫu.
- **Trên mesh** có hàm đo thật: cắt mặt phẳng ngang ở một độ cao, lấy vòng kín lớn nhất và tính
  tổng độ dài các đoạn → chu vi polygon. Hàm này được dùng để **so với target** trong vòng lặp fit.
- Hai cách **không cùng định nghĩa**: một bên là elip + hệ số kinh nghiệm, một bên là polygon của
  lát cắt thật. Chúng chỉ được ép bằng nhau về mặt số học.
- Có 12 dòng số đo trong báo cáo; thiếu cân nặng, bắp tay, cẳng tay, cổ tay, dài chân/outseam,
  vòng đùi phải, vòng ngực dưới, v.v.

---

## 1. Số đo từ scan được tính thế nào?

### 1.1. Đầu vào silhouette

- 2 ảnh được MediaPipe tách mask; chiều rộng/depth được lấy theo **35 mốc chuẩn hoá**
  `fractions = 0.12 … 1.12` từ vai đến hông — `camera_fusion.py:201`.
- Mỗi mốc:
  - ảnh trước → `widths[]` = bề rộng foreground quanh tâm, đã loại cánh tay
    (`center_run_width`, `camera_fusion.py:19-38`), chia cho chiều cao tham chiếu
    (`camera_fusion.py:206-208`);
  - ảnh nghiêng → `depths[]` cùng cách, dùng chung `shared_height` (`camera_fusion.py:220-222`).
- Làm mượt Gaussian `sigma=1.4` — `camera_fusion.py:212`.
- Chế độ `upper_body` chỉ lấy tới fraction `0.78` (`camera_fusion.py:202`).

### 1.2. Từ silhouette ra chu vi: elip, không phải lát cắt

`estimate_from_profiles()` — `measurements.py:43-72`:

1. Với từng mốc: `base_circumferences = ellipse_perimeter(w, d) * height_cm` — `measurements.py:49`.
2. `ellipse_perimeter()` dùng công thức tích phân elip:
   `4a·E(e)` với `a = max(w,d)/2`, `b = min(w,d)/2` — `measurements.py:27-32`.
3. Chọn mốc đại diện:
   - ngực: **max** trong fraction `0.30–0.44`;
   - eo: **min** trong `0.52–0.78`;
   - hông: **max** trong `0.95–1.12`
   — `measurements.py:50-58`.
4. Nhân hệ số bù độ lõm giải phẫu — `measurements.py:20-24`, `59-60`:
   - ngực `1.08074` (+8,07%);
   - eo `1.03209` (+3,21%);
   - hông `1.06234` (+6,23%).
5. Quy đổi mốc fraction → độ cao chuẩn hoá:
   `level = shoulder_level - fraction × (shoulder_level - hip_level)` — `measurements.py:68`.
6. Lưu kèm `width_cm`, `depth_cm` tuyệt đối — `measurements.py:69-70`.

**Trả lời câu 1:** đây là **công thức xấp xỉ elip** trên bề rộng/sâu silhouette, có hiệu chỉnh
bằng hệ số giải phẫu. Không phải chu vi của lát cắt ngang thật, cũng không phải chu vi đo bằng
thước dây.

Hệ quả đáng lưu ý: vì hông lấy max tới fraction `1.12`, mốc hông có thể rơi xuống khoảng
`0.805 − 1.12 × 0.271 ≈ 0.50 H` — thấp hơn mốc xương hông `0.534 H`
(`measurements.py:50`, `68`; mốc xương ở `reconstruction.py:505-508`).

### 1.3. Riêng chiều cao và rộng vai

- `height_cm`: người dùng nhập (`main.py:276`), không đo từ ảnh.
- `shoulder_width_cm`: khoảng cách 2 landmark vai / chiều cao tham chiếu × `height_cm`
  (`measurements.py:51`; `reconstruction.py:486`). Đây là **bề rộng**, không phải chu vi.
- `upper_body`: các hàng silhouette > 0.78 được thay bằng bề rộng/depth của template
  (`reconstruction.py:496-503`), và `measurements.hip_cm` bị đặt `None`
  (`reconstruction.py:571-573`).

---

## 2. Có hàm đo trên mesh 3D để so với target không?

**Có.** Đó là `closed_torso_section()` — `measurements.py:75-123`.

Cách hoạt động:

1. Cắt mesh bằng mặt phẳng ngang `y = level_m`:
   `trimesh.intersections.mesh_plane(mesh, [0,1,0], [0, level_m, 0])` — `measurements.py:81`.
2. Nối các đoạn giao thành graph, tách thành các vòng kín — `measurements.py:82-112`.
3. Chọn **vòng có diện tích lớn nhất** (mặc định), hoặc vòng có tâm x gần `center_x_m` khi đo chi
   (`measurements.py:115-121`).
4. Chu vi = tổng khoảng cách các điểm × 100 → **cm** — `measurements.py:122`.

Đặc điểm:

- **Không dùng chỉ số đỉnh cố định.** Đây là lát cắt theo **độ cao**, lấy mọi giao điểm của mặt
  phẳng với tam giác.
- `center_x_m` cho phép đo riêng từng bên chi (đùi/bắp chân/cổ chân) — dùng ở
  `report.py:115-123`.
- Kết quả là **polygon perimeter** của lưới, phản ánh cả chỗ lõm, khác với elip.

### 2.1. Dùng để so với target

`fit_measurement_targets()` — `measurements.py:212-290`:

- Mỗi vòng lặp, tại `target["level"] * h` (mét), gọi `closed_torso_section()` để đo `current`
  — `measurements.py:235`.
- So `target_cm / current` để tính hệ số scale — `measurements.py:242-256`.
- Sau 4 vòng, đo lại và lưu `model_cm`, `fit_error_cm`, `points_m` — `measurements.py:269-274`.
- `fit_status` chỉ là nhãn: `matched` nếu sai số ≤ 1,5 cm — `measurements.py:276`.

Ngoài ra:

- `validate_glb_mesh()` kiểm tra các đường đo nằm trên bề mặt, khép kín, đúng vùng thân
  — `measurements.py:166-191`.
- `report.measurement_report()` dùng cùng hàm để đo các vòng phụ ở mốc cố định
  `0.955 / 0.855 / 0.405 / 0.235 / 0.065 H` — `report.py:113-126`.

**Trả lời câu 2:** có; đo bằng **lát cắt ngang theo độ cao**, không phải chỉ số đỉnh cố định.

---

## 3. Hai cách đo có cùng định nghĩa không?

**Không.** Cùng đơn vị cm và cùng độ cao danh nghĩa, nhưng khác định nghĩa hình học.

| Tiêu chí | Scan (target) | Mesh (`closed_torso_section`) |
|---|---|---|
| Đối tượng | Silhouette 2 ảnh | Lưới 3D đã dựng |
| Công thức | Chu vi **elip** `4aE(e)` + hệ số `k` | Tổng độ dài **polygon** của vòng giao |
| Độ lõm | Bù bằng hệ số kinh nghiệm `1.08/1.03/1.06` | Có sẵn trong hình học, không nhân `k` |
| Vị trí | `level = shoulder − fraction×(shoulder−hip)` | Cùng `level` đó, cắt mặt phẳng ngang |
| Đơn vị | cm | cm |
| Bề rộng/sâu | Từ silhouette, chuẩn hoá theo chiều cao | Lấy từ chính lát cắt |

Hệ quả:

- `fit_status = matched` chỉ nói **polygon trên mesh bằng số với elip ước lượng**, không nói mesh
  khớp cơ thể thật.
- Với ngực/eo/mông, báo cáo hiển thị **giá trị scan** (`measurements[...]`), không hiển thị
  `model_cm` — trừ hông trong `upper_body` (dùng `model_cm`, nguồn `template_model`)
  — `report.py:109-111`.
- **Rộng vai** chỉ có từ landmark ảnh, không có phép đo mesh tương ứng trong chế độ Anny
  (không có `width_targets`); fallback MakeHuman mới trộn 60% về landmark
  — `reconstruction.py:512-528`.
- **Các vòng phụ** (đầu/cổ/đùi/bắp chân/cổ chân) chỉ có trên mesh, không có phép đo từ ảnh
  — `report.py:113-126`; riêng cổ/đùi/bắp chân/cổ chân còn được scale theo hệ số
  `proportions.py:17-22`.

---

## 4. Số đo nào có, số đo nào thiếu?

### 4.1. Có trong báo cáo/API

| Số đo | Có? | Nguồn | Cách có |
|---|---|---|---|
| Chiều cao (`height_cm`) | ✅ | `user_input` | Người dùng nhập, `main.py:276` |
| Rộng vai (`shoulder_width_cm`) | ✅ | `photo_estimate` / `photo_with_prior` | Landmark vai / chiều cao × height, `measurements.py:51` |
| Vòng ngực (`chest_cm`) | ✅ | `photo_estimate` / `photo_with_prior` | Elip + k, `measurements.py:49-60` |
| Vòng eo (`waist_cm`) | ✅ | `photo_estimate` / `photo_with_prior` | Elip + k |
| Vòng hông (`hip_cm`) | ✅ full_body; ❌ upper_body | `photo_estimate`; `template_model`/`null` | Elip + k; upper_body lấy template rồi đặt null, `reconstruction.py:496-503`, `571-573` |
| Vòng đầu (`head_cm`) | ✅ | `template_model` | Lát cắt mesh `0.955 H`, `report.py:116` |
| Vòng cổ (`neck_cm`) | ✅ | `template_model` | Lát cắt mesh `0.855 H`, scale theo ngực, `proportions.py:18` |
| Vòng đùi trái (`thigh_cm`) | ✅ | `template_model` | Lát cắt mesh `0.405 H`, scale theo hông, `proportions.py:19` |
| Vòng bắp chân trái (`calf_cm`) | ✅ | `template_model` | Lát cắt mesh `0.235 H`, `proportions.py:20` |
| Vòng cổ chân trái (`ankle_cm`) | ✅ | `template_model` | Lát cắt mesh `0.065 H`, `proportions.py:21` |
| Dài tay (`arm_length_cm`) | ❌ | `unavailable` | Luôn `null`, `report.py:127` |
| Dài trong chân (`inseam_cm`) | ❌ | `unavailable` | Luôn `null`, `measurements.py:51`, `report.py:128` |

Nội bộ còn có **bề rộng và bề sâu** của ngực/eo/mông (`width_cm`, `depth_cm`) trong `targets`
— `measurements.py:69-70` — nhưng không phải dòng báo cáo cho người dùng.

### 4.2. Thiếu hoàn toàn

| Số đo | Trạng thái |
|---|---|
| Cân nặng, BMI, % mỡ | ❌ Không có ở bất kỳ đâu. `weight` trong Anny chỉ là **prior** suy từ eo/chiều cao (`anny_body.py:49-61`), không phải cân nặng người dùng |
| Vòng bắp tay / cẳng tay / cổ tay | ❌ Không có; không có vòng tay trong `proportions.py` |
| Vòng đùi phải | ❌ Chỉ đo bên trái (`report.py:118`) |
| Vòng ngực dưới, bán kính ngực, cup | ❌ Không có |
| Dài chân / outseam / chiều dài chân ngoài | ❌ Không có; chỉ có `inseam = null` |
| Đầu gối, bắp đùi giữa, chiều dài đùi | ❌ Không có |
| Dài thân / torso length | ❌ Không có |
| Độ dốc vai, độ dày ngực dạng dòng báo cáo | ❌ Không có (depth chỉ nội bộ trong `targets`) |
| Chiều dài bàn chân, chiều cao đầu | ❌ Không có |
| Chu vi cổ tay, mắt cá | ❌ Không có (chỉ cổ chân) |

### 4.3. Tóm tắt đúng 12 dòng báo cáo

1. `height_cm` — user input
2. `chest_cm` — ảnh (elip)
3. `waist_cm` — ảnh (elip)
4. `hip_cm` — ảnh full_body / null upper_body
5. `shoulder_width_cm` — landmark ảnh
6. `head_cm` — mesh
7. `neck_cm` — mesh + tỷ lệ
8. `arm_length_cm` — null
9. `inseam_cm` — null
10. `thigh_cm` — mesh + tỷ lệ
11. `calf_cm` — mesh + tỷ lệ
12. `ankle_cm` — mesh + tỷ lệ

Nguồn: `report.py:108-128`.

---

## 5. Bảng phát hiện nhanh

| # | Phát hiện | Bằng chứng |
|---|---|---|
| 1 | Scan dùng elip + hệ số giải phẫu, không phải lát cắt thật | `measurements.py:27-32`, `49-60` |
| 2 | 35 mốc silhouette 0.12–1.12, làm mượt Gaussian | `camera_fusion.py:201-212` |
| 3 | Mesh đo bằng mặt phẳng ngang, chọn vòng kín lớn nhất | `measurements.py:75-123` |
| 4 | Fit so target elip với polygon mesh, 4 vòng lặp | `measurements.py:232-276` |
| 5 | Hai định nghĩa khác nhau; `matched` chỉ là khớp số học | mục 3 |
| 6 | Hông có thể rơi xuống ~0.50 H do fraction 1.12 | `measurements.py:50`, `68` |
| 7 | Không có cân nặng, bắp tay, dài chân thật | mục 4.2 |
| 8 | `inseam`/`arm_length` luôn null | `measurements.py:51`, `report.py:127-128` |
