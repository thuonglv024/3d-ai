# MORPH Studio — Chất Lượng Dựng Hình 3D, Pipeline 3 Tầng & Ranh Giới Công Nghệ (`docs/SCAN_QUALITY.md`)

> **Ranh giới công nghệ bắt buộc**:  
> Bộ máy dựng hình sử dụng **MediaPipe Pose Landmarker + Segmentation trên CPU**, dựng nền cơ thể từ **basis Anny** (Apache-2.0, asset MakeHuman CC0) đã nướng sẵn trong `backend/models/anny-bases.npz`, rồi khớp số đo (`ENGINE = "mediapipe-two-photo-fit-v6"`). Khi thiếu basis, engine tự rơi về lưới MakeHuman cũ; runtime **không** import Anny/torch.\
> Hệ thống **không** sử dụng SAM 3D Body, MHR, SMPL, PIFuHD hay cảm biến chiều sâu LiDAR/RGB-D; **không** tái tạo khuôn mặt thật; và **chưa có kiểm chứng độ chính xác lâm sàng hoặc đối chứng thước dây trên người thật**. Không được tuyên bố kết quả là số đo may đo chính xác.

---

## 1. Kiến Trúc Pipeline 3 Tầng Tối Ưu Hóa (`v4`)

Hệ thống dựng hình 3D xử lý 2 khung hình webcam (**Chính diện** và **Nghiêng 90°**) qua 3 tầng toán học nối tiếp nhằm triệt tiêu sai số từ khâu đọc khung hình, ghép hai góc nhìn cho đến nội suy chu vi giải phẫu và khớp lưới `.glb`:

```
[2 Ảnh Webcam: Chính diện & Nghiêng 90°]
   │
   ▼  TẦNG 1: Observation & Multi-Anchor Prior (reconstruction.py -> observe, estimate_upper_body_height)
   │  • Chế độ full_body: obs.height = bottom - top (pixel toàn thân).
   │  • Chế độ upper_body: Hợp nhất mỏ neo Đỉnh đầu→Vai (0.195 H) và Vai→Hông (0.290 H)
   │    bằng hàm Huber/Tanh bị chặn biên, chống trôi mốc hông và chống lệch tỷ lệ lưng dài/ngắn.
   │
   ▼  TẦNG 2: Camera Scale Fusion & Landmark Alignment (camera_fusion.py -> aligned_torso_landmarks, fuse_camera_scale)
   │  • Lọc trọng số theo visibility cho góc nghiêng 90° để loại bỏ mốc vai/hông phía khuất bị trôi.
   │  • Đồng bộ mặt phẳng quét dọc (rows) và dùng chung chiều cao tham chiếu shared_height
   │    giữa 2 góc chụp từ cùng một webcam cố định, bảo toàn tuyệt đối tỷ lệ Độ sâu / Bề rộng (D/W).
   │
   ▼  TẦNG 3: Anatomical Cross-Section Calibration & Aspect-Preserving Fit (measurements.py)
   │  • Bù độ lõm giải phẫu (xương ức, bả vai, cột sống lưng, cơ mông) mà công thức elip tính thiếu:
   │    Ngực: k = 1.08074 (+8.07% / bù ~7.47%), Eo: k = 1.03209 (+3.21% / bù ~3.11%), Hông: k = 1.06234 (+6.23% / bù ~5.87%).
   │  • Biến dạng lưới bằng nội suy đơn điệu PCHIP + scale_lateral (tránh đảo đỉnh vùng nách)
   │    và khớp 4 vòng lặp giữ nguyên cả chu vi mục tiêu lẫn tỷ lệ D/W trên file .glb.
   ▼
[Mô hình 3D .GLB + 12 Dòng Số Đo Có Nhãn Nguồn + Tư Vấn Size]
```

### 1.1. Tầng 1 — Ước lượng chiều cao tham chiếu đa mỏ neo ([`backend/app/reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py#L90-L191))
- Trong chế độ `upper_body`, ảnh không có cẳng chân và bàn chân nên không thể dùng `bottom - top` làm chiều cao toàn thân.
- Thay vì chỉ dựa đơn thuần vào `torso / 0.290` (dễ bị lệch $\pm 10.34\%$ khi người dùng có lưng ngắn `r_torso = 0.26` hoặc lưng dài `r_torso = 0.32`), hàm [`estimate_upper_body_height()`](file:///d:/MORPH-AI/backend/app/reconstruction.py#L96-L122) kết hợp:
  - Mỏ neo sọ–vai: `HEAD_SHOULDER_RATIO = 0.195` (`shoulder_y - top_y`).
  - Mỏ neo mũi–vai phụ trợ: tỷ lệ `0.125` khi mốc mũi (`points[0]`) có `visibility >= 0.6`.
  - Mỏ neo vai–hông: `TORSO_RATIO = 0.290` (`hip_y - shoulder_y`).
- Hàm hợp nhất `fused_height = h_head * (1.0 + 0.014 * tanh((h_torso - h_head) / (0.08 * h_head)))` giữ sai số chiều cao tham chiếu trong biên độ **`≤ ±1.20%`** (và tự động fallback về `torso / 0.290` đối với ảnh giả lập cắt sát đỉnh đầu trong unit test cũ).

### 1.2. Tầng 2 — Đồng bộ tỷ lệ Camera & Căn chỉnh mốc 2 góc nhìn ([`backend/app/camera_fusion.py`](file:///d:/MORPH-AI/backend/app/camera_fusion.py))
- Khi xoay người 90° sang góc nghiêng (`lateral`), một bên vai/hông bị che khuất có `visibility` thấp và dễ bị trôi tọa độ dọc.
- [`aligned_torso_landmarks(obs, reference_obs)`](file:///d:/MORPH-AI/backend/app/camera_fusion.py#L23-L85) ưu tiên trọng số cho bên cơ thể hướng về phía camera và khóa khoảng cách dọc `hip[1] - shoulder[1]` theo `ref_torso` của ảnh chính diện khi chụp trên cùng độ phân giải camera cố định.
- [`fuse_camera_scale(frontal, lateral)`](file:///d:/MORPH-AI/backend/app/camera_fusion.py#L88-L110) thiết lập mẫu số quy đổi chung `shared_height`, đảm bảo:
  $$\frac{D_{\text{norm}}}{W_{\text{norm}}} = \frac{D_{\text{px}} / H_{\text{shared}}}{W_{\text{px}} / H_{\text{shared}}} = \frac{D_{\text{px}}}{W_{\text{px}}}$$
  giúp tỷ lệ Độ sâu / Bề rộng ($D/W$) không bị biến dạng (`0.00%` sai lệch) ngay cả khi mốc hông góc nghiêng bị trôi $\pm 10\%$.

### 1.3. Tầng 3 — Hiệu chuẩn lát cắt giải phẫu & Khớp lưới 3D ([`backend/app/measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py))
- Mặt cắt ngang cơ thể người tại ngực, eo và mông không phải hình elip lồi lý tưởng mà có các vùng lõm tự nhiên (xương ức, rãnh cột sống lưng, khe cơ ngực/mông). Công thức tích phân elip thuần [`ellipse_perimeter(w, d)`](file:///d:/MORPH-AI/backend/app/measurements.py#L27-L32) tính thiếu chu vi thực của lưới MakeHuman có cùng $(W, D)$ lần lượt là `-7.47%` (Ngực), `-3.11%` (Eo) và `-5.87%` (Mông).
- [`anatomical_perimeter(w, d, key)`](file:///d:/MORPH-AI/backend/app/measurements.py#L35-L40) và [`estimate_from_profiles()`](file:///d:/MORPH-AI/backend/app/measurements.py#L43-L68) nhân hệ số bù giải phẫu [`ANATOMICAL_SECTION_FACTORS`](file:///d:/MORPH-AI/backend/app/measurements.py#L20-L24) (`chest_cm: 1.08074`, `waist_cm: 1.03209`, `hip_cm: 1.06234`).
- [`fit_measurement_targets()`](file:///d:/MORPH-AI/backend/app/measurements.py#L212-L289) chạy 4 vòng lặp nội suy `PchipInterpolator`, tách hệ số tỷ lệ ngang `factor_x` và tỷ lệ sâu `factor_z` theo `aspect_corr = sqrt(target_ratio / cur_ratio)` để mô hình 3D `.glb` đạt đồng thời:
  1. Chu vi mặt cắt thực tế (`closed_torso_section`) khớp `target_cm` với sai số hội tụ `0.00 cm` (`< 1.5 cm`).
  2. Bảo toàn nguyên vẹn kích thước ngang $W$, độ sâu $D$ và tỷ lệ $D/W$ từ silhouette hai ảnh (không còn bị co hẹp `~5.2%` như phiên bản elip chưa hiệu chuẩn).

### 1.4. Dáng nam/nữ: basis Anny thay lưới trung tính ([`backend/app/anny_body.py`](backend/app/anny_body.py))
- [`backend/models/anny-bases.npz`](backend/models/anny-bases.npz) (1,9 MB) chứa **12 lưới nền** sinh sẵn từ **Anny 0.6.1** (NAVER Labs Europe, Apache-2.0; asset MPFB2/MakeHuman CC0) theo lưới **giới × cân nặng × cơ** (2 × 3 × 2). Frame giống engine: Y-up, chân ở `y=0`, mặt hướng `+Z`, cao `1.0`.
- Anny chỉ chạy **offline** ([`verification/scripts/build_anny_bases.py`](verification/scripts/build_anny_bases.py)): khởi tạo model tốn ~3 phút và ~1 GB RAM trên CPU. Runtime đọc basis 1,9 MB rồi nội suy tuyến tính, **không** import torch/Anny.
- Prior theo số đo: `weight` suy từ tỉ lệ eo/chiều cao (chỉ để chọn vùng mô hình, không phải đo mỡ cơ thể), `muscle` cố định `0.45`, giới lấy từ [`resolve_sex()`](backend/app/anatomy.py) như trước.
- Khác biệt nam/nữ đến từ phenotype `gender` cộng local changes của Anny: nữ có ngực/mông/hông rõ hơn, nam có V-shape vai–eo và cơ vai. Đây vẫn là **prior dựng hình**, không phải nhận diện giới tính.
- Chu vi ngực/eo/mông vẫn do [`fit_measurement_targets()`](backend/app/measurements.py) áp lại sau cùng, nên prior không ghi đè số đo (`fit 0.00 cm` trong QA).
- Cao độ vòng ngực/eo/mông lấy từ **mốc xương có sẵn trong lưới MakeHuman** ([`template_landmarks()`](backend/app/anatomy.py) đọc các nhóm `g joint-*`): vai `0.805 H`, hông `0.534 H`, cổ `0.844 H`.
- Rộng vai là **ràng buộc bề ngang** riêng, chỉ áp cho fallback MakeHuman. Với Anny, mặt cắt ngang đúng mốc vai bị lẫn cánh tay trong tư thế A-pose nên ép theo landmark sẽ bóp deltoid; vai giữ theo phenotype giới và độ rộng tự nhiên của mô hình.
- **Các vòng phụ ăn theo 3 vòng chính** ([`backend/app/proportions.py`](backend/app/proportions.py)): cổ `0.35×` thay đổi tương đối của ngực; đùi `0.60×`, bắp chân `0.35×`, cổ chân `0.15×` thay đổi tương đối của hông (chặn `0.80–1.30`). Lưới được scale theo dải `±4.5% H` quanh mốc `0.855 H / 0.405 H / 0.235 H / 0.065 H` trước khi khớp lại 3 vòng chính. Đây là **hệ số dựng hình**, không phải hằng số nhân trắc học.

---

## 2. Phân Biệt Nguồn Gốc 12 Chỉ Số Trong Báo Cáo (`backend/app/report.py`)

Báo cáo chi tiết (`body_profile.measurement_details`) luôn xuất đúng **12 dòng** với nhãn nguồn (`source`) minh bạch:

| STT | Mã chỉ số (`key`) | Tên hiển thị | Nguồn ở chế độ `full_body` | Nguồn ở chế độ `upper_body` | Ghi chú |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `height_cm` | Chiều cao | `user_input` | `user_input` | Do người dùng nhập (`100–230 cm`) |
| 2 | `chest_cm` | Vòng ngực | `photo_estimate` | `photo_with_prior` | Cắt mặt phẳng ngang mức ngực trên mesh đã fit |
| 3 | `waist_cm` | Vòng eo | `photo_estimate` | `photo_with_prior` | Cắt mặt phẳng ngang mức eo trên mesh đã fit |
| 4 | `hip_cm` | Vòng mông | `photo_estimate` | `template_model` | **Lưu ý**: `measurements.hip_cm` cấp cao nhất là `null` khi `upper_body` |
| 5 | `shoulder_width_cm` | Rộng vai | `photo_estimate` | `photo_with_prior` | Khoảng cách ngang hai mốc vai `11, 12` quy đổi ra cm |
| 6 | `head_cm` | Vòng đầu | `template_model` | `template_model` | Mặt cắt mô hình nền tại mức `0.955 H` |
| 7 | `neck_cm` | Vòng cổ | `template_model` | `template_model` | Mặt cắt mô hình nền tại mức `0.855 H` |
| 8 | `arm_length_cm` | Dài tay | `unavailable` (`null`) | `unavailable` (`null`) | Chưa đủ cơ sở đo tin cậy từ 2 ảnh |
| 9 | `inseam_cm` | Dài đũng quần | `unavailable` (`null`) | `unavailable` (`null`) | Chưa đủ cơ sở đo tin cậy từ 2 ảnh |
| 10 | `thigh_cm` | Vòng đùi trái | `template_model` | `template_model` | Mặt cắt chi dưới trên mô hình nền (`0.405 H`) |
| 11 | `calf_cm` | Vòng bắp chân trái | `template_model` | `template_model` | Mặt cắt chi dưới trên mô hình nền (`0.235 H`) |
| 12 | `ankle_cm` | Vòng cổ chân trái | `template_model` | `template_model` | Mặt cắt chi dưới trên mô hình nền (`0.065 H`) |

---

## 3. Kết Quả Benchmark Định Lượng (`verification/scripts/evaluate_3d_scan_accuracy.py`)

Chạy trực tiếp bằng lệnh:
```powershell
backend\.venv\Scripts\python.exe verification\scripts\evaluate_3d_scan_accuracy.py
```

### Tóm tắt kết quả Before (Legacy v1) vs After (3-Tier Optimized v2)
1. **Độ ổn định chiều cao tham chiếu `obs.height` (Tầng 1)**:
   - Khi tỷ lệ lưng `r_torso` biến thiên từ `0.260` (lưng ngắn) đến `0.320` (lưng dài):
   - **Before**: Sai số `obs.height` lên tới **`±10.34%`** (kéo theo vòng ngực lệch `+11.1 cm / -9.0 cm`).
   - **After**: Sai số `obs.height` được ghìm chặt ở mức **`≤ ±1.20%`** (vòng ngực chỉ lệch tối đa `±1.2 cm`, đạt tiêu chí `< ±1.5%`).
2. **Bảo toàn tỷ lệ Độ sâu / Bề rộng `D/W` trước nhiễu góc nghiêng 90° (Tầng 2)**:
   - Khi mốc hông góc nghiêng 90° bị trôi dọc `±10%` hoặc mốc hông khuất (`visibility = 0.20`) bị lệch `+55px`:
   - **Before**: Tỷ lệ $D/W$ bị méo từ **`-7.73%` đến `+10.52%`** (gây phình hoặc dẹt thân người).
   - **After**: Sai lệch tỷ lệ $D/W$ đạt **`0.00%` tuyệt đối**.
3. **Độ chính xác Chu vi Giải phẫu & Bảo toàn $(W, D)$ trên Lưới 3D (Tầng 3)**:
   - Trên mẫu chuẩn 170 cm: Sai lệch giữa chu vi ước lượng và chu vi mặt cắt lưới thực tế giảm từ **`-6.09 cm (-7.47%)`** ở Ngực, **`-2.45 cm (-3.11%)`** ở Eo, **`-5.84 cm (-5.87%)`** ở Mông xuống **`0.00 cm (0.00%)`**.
   - Trên cả 6 dáng người chuẩn (`Slim Petite`, `Standard Female`, `Athletic Male`, `Broad Male`, `Pear Lower-Body`, `High-WHR / Plus`): `max_fit_error_cm = 0.00 cm` (`fit_status: "matched"`), loại bỏ hoàn toàn hiện tượng mô hình 3D bị co hẹp ngang/sâu `~5.2%` của bản cũ.
4. **Hiệu năng thực thi (Latency)**:
   - Tổng thời gian thực thi toàn bộ Pipeline Toán học & Biến dạng 3 Tầng (Tầng 1 + Tầng 2 + Tầng 3 PCHIP `13,380` đỉnh): **`9.67 ms` median** (đạt mục tiêu `< 15 ms`).

---

## 4. Các Giới Hạn Phải Luôn Công Bố Minh Bạch

1. **Chưa có kiểm chứng trên người thật (Unvalidated on Human Subjects)**:
   - Các kiểm thử tự động hiện tại sử dụng hình nộm tổng hợp (`verification/scripts/qa/`) và 6 hồ sơ hình thái toán học để chứng minh tính đúng đắn hình học của phần mềm.
   - Hệ thống **chưa** được đánh giá sai số tuyệt đối (MAE) so với thước dây may đo trên tập mẫu người thật đa dạng về trang phục, ánh sáng và khoảng cách camera.
2. **Giới hạn của Silhouette 2D**:
   - Quần áo rộng thùng thình, tóc xõa che cổ/vai, tay áp sát thân hoặc góc đặt camera chúc/ngửa mạnh vẫn ảnh hưởng trực tiếp đến biên dạng tách nền của MediaPipe.
3. **Giới hạn khi tư vấn size**:
   - Hệ thống đối chiếu số đo cơ thể ước lượng (`body_cm`) với bảng khoảng số đo cơ thể của từng sản phẩm; không mô phỏng độ co giãn vật lý của chất liệu vải.
