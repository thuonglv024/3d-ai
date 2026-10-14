# Quy Trình Chuẩn Đo Nhân Trắc Học, Hiệu Chuẩn Khoảng Dự Đoán & Nghiệm Thu Thực Nghiệm Trên Người Thật (`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`)

> **Mục đích tài liệu**:  
> Thiết lập quy trình chuẩn hóa theo tiêu chuẩn quốc tế **ISO 7250-1:2017** (*Basic human body measurements for technological design — Part 1: Body measurement definitions and landmarks*) và **ISO 8559-1:2017** (*Size designation of clothes — Part 1: Anthropometric definitions for body measurement*) để:
> 1. Đối chiếu chính xác từng vị trí đo giữa định nghĩa giải phẫu học quốc tế và thuật toán thực tế trong [`backend/app/measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py) & [`backend/app/reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py).
> 2. Thu thập số đo thước dây trên người thật, kiểm soát sai số kỹ thuật của người đo (**TEM**), và chống rò rỉ dữ liệu theo cá thể (`subject_id`).
> 3. Thiết lập **Mục tiêu kỹ thuật đề xuất cho giai đoạn Pilot (Proposed Pilot Target Thresholds)** và phương pháp **Khoảng Dự Đoán Được Hiệu Chuẩn (Calibrated Prediction Intervals — Split Conformal Prediction & Empirical Residual Quantiles)** thay thế hoàn toàn giả định phân phối chuẩn tham số $\pm 1.96 \times \text{RMSE}$.
> 4. Tích hợp trực tiếp vào bộ kiểm định thực nghiệm [`verification/scripts/evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py) và [`verification/scripts/benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py).

---

## 1. Tuyên Bố Minh Bạch Về Trạng Thái Hiện Tại

Hiện tại, bộ máy dựng hình 3D của MORPH AI (`ENGINE = "mediapipe-two-photo-fit-v4"`) đã hoàn tất **Kiểm thử Hình học & Hệ thống (Synthetic / Geometric Verification)** nhưng **CHƯA có tập dữ liệu đo thước dây trên người thật (`REAL_HUMAN_DATASET_STATUS = "MISSING_EMPIRICAL_COHORT"`)**.  
- Trạng thái nghiệm thu độ chính xác trên người thật hiện tại: **`human_accuracy_validation_status = "NOT_ACCEPTED_NO_EMPIRICAL_DATASET"`** (*"CHƯA THỂ NGHIỆM THU ĐỘ CHÍNH XÁC TRÊN NGƯỜI THẬT — Human accuracy cannot be accepted yet because no consented real-human dataset is present"*).
- Cho đến khi hoàn tất giai đoạn thu thập và nghiệm thu theo tài liệu này:
  - Trường `uncertainty_cm` trong báo cáo số đo ([`backend/app/report.py`](file:///d:/MORPH-AI/backend/app/report.py)) bắt buộc giữ giá trị `null` (`None`).
  - Không được tuyên bố sai số tuyệt đối $\pm X\text{ cm}$ trên người thật trong giao diện người dùng hay tài liệu thương mại.

---

## 2. Đối Chiếu Định Nghĩa Vị Trí Đo: Tiêu Chuẩn Quốc Tế (ISO 7250-1:2017 / ISO 8559-1:2017) vs. Thuật Toán Trong Code

Dụng cụ bắt buộc khi đo Ground-Truth (`gt_cm`) trên người thật:
- **Thước dây nhân trắc không giãn** (Fiberglass hoặc thép mềm có vạch chia `1 mm`, chiều rộng bản thước $\le 7\text{ mm}$, kiểm chuẩn định kỳ với thước chuẩn kim loại).
- **Thước kẹp nhân trắc (Spreading Caliper / Anthropometer)** để đo khoảng cách thẳng giữa hai mỏm xương cùng vai (*Biacromial breadth*).
- **Thước đo chiều cao cố định (Stadiometer)** có thanh chặn đỉnh đầu vuông góc với tường.

### 2.1. Bảng đối chiếu chi tiết giữa chuẩn nhân trắc học và thuật toán hệ thống

| STT | Chỉ số (`metric_key`) | Chuẩn trích dẫn (`ISO 7250-1:2017` & `ISO 8559-1:2017`) | Định nghĩa giải phẫu & Cách đặt thước trên người thật | Cách tính thực tế trong [`measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py) & [`reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py) | Độ chệch cấu trúc (Algorithmic vs. Anatomical Gap) & Lưu ý đo kiểm |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `height_cm` | **ISO 7250-1:2017 Mục 6.1.1** (*Stature*)<br>**ISO 8559-1:2017 Mục 5.1.1** (*Stature / Body height*) | Khoảng cách thẳng đứng từ mặt sàn đến điểm cao nhất của hộp sọ (**Vertex**) khi đầu giữ chuẩn trên mặt phẳng **Frankfort** (mép dưới ổ mắt ngang với mép trên ống tai ngoài). Đi chân trần, hai gót chạm nhau, lưng/mông/gót chạm thước đo. | Người dùng **tự nhập** (`source = "user_input"`), không tự đo từ ảnh 2D thiếu chiều sâu. Dùng làm hệ số quy đổi toàn cục từ chiều cao pixel đồng bộ (`shared_height`) sang `cm` và scale trục $Y$ của lưới MakeHuman (`vertices *= height_cm / 100`). | Mọi sai số tự báo cáo chiều cao $\Delta H$ của người dùng sẽ gây trôi tuyến tính tỷ lệ thuận ($\approx \Delta H / H$) lên toàn bộ các chu vi và bề rộng ước lượng từ ảnh. Khi nghiệm thu Pilot, phải nhập đúng chiều cao đo bằng Stadiometer làm đầu vào chuẩn và kiểm thử riêng độ nhạy khi lệch $\pm 2\text{–}5\text{ cm}$. |
| 2 | `shoulder_width_cm` | **ISO 7250-1:2017 Mục 6.2.1** (*Biacromial breadth*)<br>**ISO 8559-1:2017 Mục 5.4.1** (*Shoulder width / Back shoulder width*)<br>**ISO 7250-1:2017 Mục 6.2.2** (*Bideltoid breadth*) | - **ISO 7250-1 (6.2.1)**: Khoảng cách thẳng (Euclidean 3D) giữa hai điểm ngoài cùng của mỏm cùng vai xương bả vai trái và phải (**Acromion**), đo bằng thước kẹp nhân trắc.<br>- **ISO 8559-1 (5.4.1)**: Khoảng cách đo qua bề mặt lưng hoặc ngang giữa hai mỏm *Acromion* khi hai vai thả lỏng tự nhiên. | Trong [`reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py#L373) & [`measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py#L47):<br>`front_shoulders = abs(frontal.points[11, 0] - frontal.points[12, 0]) / shared_height`<br>`shoulder_width_cm = round(shoulder_ratio * height_cm, 1)`.<br>Dựa hoàn toàn trên khoảng cách ngang Euclidean 2D giữa **MediaPipe Pose Landmarks `11` (Left Shoulder) và `12` (Right Shoulder)**. | **CẢNH BÁO ĐỘ CHỆCH MỐC (Landmark Offset Bias)**:<br>Mốc MediaPipe `11` và `12` là **tâm khớp vai 2D (glenohumeral joint centers) suy từ ảnh RGB**, vốn nằm **thấp hơn và dịch vào phía trong (medial)** so với điểm xương **Acromion** ngoài da (và càng hẹp hơn so với bề rộng cơ delta *Bideltoid* hay đường cong lưng). Do đó, khi đo kiểm trên người thật bắt buộc phải đo cả:<br>1. `shoulder_biacromial_gt_cm`: Thước kẹp thẳng ngang hai mỏm *Acromion* (chuẩn ISO 7250-1).<br>2. `shoulder_joint_gt_cm`: Khoảng cách ngang hai tâm khớp vai trước (tương ứng mốc MediaPipe `11–12`).<br>3. `shoulder_contour_gt_cm`: Thước dây qua mặt lưng (ISO 8559-1) để lượng hóa chính xác độ chệch mốc $\Delta_{\text{MP11-12 vs Acromion}}$. |
| 3 | `chest_cm` | **ISO 8559-1:2017 Mục 5.3.4** (*Chest girth / Bust girth*)<br>**ISO 7250-1:2017 Mục 6.4.6** (*Chest circumference*) | Thước dây đi ngang qua điểm nhô cao nhất của bầu ngực (**Thelion / Bustpoint**) hoặc mức xương ức giữa (**Mesosternale** — khoang liên sườn 4), vòng qua dưới hõm nách và phần dưới xương bả vai. Mặt phẳng thước dây **song song với mặt sàn**, đọc ở **cuối thì thở ra bình thường (End-tidal expiration)**. | Trong [`measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py#L46-L67):<br>Tìm mặt cắt ngang có chu vi **lớn nhất (`choice = "max"`)** trong dải tỷ lệ thân `fractions ∈ [0.30, 0.44]` tính từ vai xuống hông (tương ứng công thức ánh xạ `level = 0.805 - 0.290 * f ∈ [0.6774 * H, 0.7180 * H]`, nằm trong vùng giải phẫu ngực `~0.68 * H .. 0.79 * H` tính từ mặt đất trên lưới MakeHuman đã biến dạng). Chu vi elip 2D được nhân hệ số bù lõm `ANATOMICAL_SECTION_FACTORS["chest_cm"] ≈ 1.08074` (`+8.07%`) và khớp 4 vòng lặp trên lát cắt phẳng `closed_torso_section`. | Thuật toán tìm cực đại (`max`) của tích hợp bề rộng $\times$ độ sâu silhouette trong dải ngực và cắt phẳng ngang trên lưới 3D. Ở góc chính diện, nếu hai cánh tay không tách khỏi sườn tối thiểu `15°–25°`, bóng nách có thể sát nhập vào thân làm tăng bề rộng giả tạo; ở nữ giới hoặc người có cơ ngực/xương bả vai phát triển, cần kiểm tra độ khớp giữa mức cực đại silhouette và mức *Thelion/Mesosternale*. |
| 4 | `waist_cm` | **ISO 8559-1:2017 Mục 5.3.10** (*Waist girth / Natural waist*)<br>**ISO 7250-1:2017 Mục 6.4.7** (*Waist circumference*) | Chu vi ngang nhỏ nhất của phần thân tự nhiên nằm giữa bờ dưới xương sườn thứ 10 (**10th rib**) và bờ trên mào chậu (**Iliocristale**), thường cao hơn rốn `~2–3 cm`. Bụng thả lỏng tự nhiên, mặt phẳng thước dây song song với sàn. | Trong [`measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py#L46-L67):<br>Tìm mặt cắt ngang có chu vi **nhỏ nhất (`choice = "min"`)** trong dải tỷ lệ thân `fractions ∈ [0.52, 0.78]` (tương ứng mức chiều cao lưới `level = 0.805 - 0.290 * f ∈ [0.5788 * H, 0.6542 * H]` — nằm trong dải giải phẫu eo `0.56 * H .. 0.66 * H` tính từ sàn). Nhân hệ số bù lõm `ANATOMICAL_SECTION_FACTORS["waist_cm"] ≈ 1.03209` (`+3.21%`) và khớp trên lát cắt phẳng ngang của lưới MakeHuman. | Định nghĩa tìm cực tiểu (`min`) trong dải `0.56 * H .. 0.66 * H` tương thích trực tiếp với định nghĩa *Natural waist (smallest trunk girth)* của ISO 8559-1 Mục 5.3.10 trên người có thắt eo rõ. Tuy nhiên, với người có tỷ lệ eo/hông cao (`High-WHR / Plus`) hoặc mặc áo phông phồng ở vùng bụng, vị trí cực tiểu của bóng 2D có thể dịch chuyển dọc trục $Y$. |
| 5 | `hip_cm` | **ISO 8559-1:2017 Mục 5.3.13** (*Hip girth / Seat girth*)<br>**ISO 7250-1:2017 Mục 6.4.8** (*Hip circumference*) | Chu vi ngang lớn nhất vòng qua vùng nhô cao nhất của cơ mông phía sau (**Gluteal prominence / Buttock protrusion**) và ngang qua vùng xương mu phía trước, mặt phẳng thước dây song song với mặt sàn, hai bàn chân khép sát. | Trong [`measurements.py`](file:///d:/MORPH-AI/backend/app/measurements.py#L46-L67) & [`reconstruction.py`](file:///d:/MORPH-AI/backend/app/reconstruction.py#L383-L404):<br>Tìm mặt cắt ngang có chu vi **lớn nhất (`choice = "max"`)** trong dải `fractions ∈ [0.95, 1.12]` (tương ứng mức chiều cao lưới `level = 0.805 - 0.290 * f ∈ [0.4802 * H, 0.5295 * H]` — nằm trong dải `0.48 * H .. 0.54 * H` tính từ sàn), nhân hệ số `ANATOMICAL_SECTION_FACTORS["hip_cm"] ≈ 1.06234` (`+6.23%`).<br>**Khi `capture_mode == "upper_body"`**: khóa cứng `hip_cm = None` (`source = "template_model"`). | Định nghĩa tìm cực đại (`max`) trong dải `0.48 * H .. 0.54 * H` tương ứng trực tiếp với mức *Gluteal prominence* của ISO 8559-1 Mục 5.3.13 trong chế độ `full_body`. Trong chế độ `upper_body`, vùng mông nằm sát hoặc ngoài mép dưới khung hình nên hệ thống bắt buộc trả về `None` và chặn hoàn toàn khỏi thuật toán gợi ý size quần/váy. |

---

## 3. Quy Chuẩn Tư Thế, Trang Phục & Thiết Lập Camera Khi Chụp Đối Chứng

Để giảm thiểu nhiễu ngoại cảnh và tách bạch lỗi thuật toán khỏi lỗi vận hành người dùng, mỗi tình nguyện viên phải được chụp trong điều kiện chuẩn hóa:

### 3.1. Trang phục khi đo và chụp
1. **Lượt chụp Chuẩn (Baseline Tight-Fit — Bắt buộc cho tất cả tình nguyện viên)**:
   - Mặc đồ tập thể thao ôm sát cơ thể (áo thun ôm / tank-top mỏng và quần legging / quần short ôm sát, độ dày vải $< 1.5\text{ mm}$), màu sắc tương phản rõ với nền tường.
   - Tóc dài phải buộc gọn phía trên gáy để lộ rõ đường viền cổ và mỏm vai (`Acromion`).
2. **Lượt chụp Thực tế (Everyday Casual — Đánh giá độ nhạy trang phục)**:
   - Mặc áo phông thường ngày (regular-fit) hoặc áo sơ mi đóng thùng và quần dài ống đứng để định lượng độ phình silhouette do quần áo (`clothing inflation bias`) và kiểm định khoảng dự đoán bất đối xứng.

### 3.2. Tư thế cơ thể trong 2 khung hình
- **Góc Chính diện (`front`)**:
  - Đứng thẳng, mắt nhìn thẳng vào ống kính, hai bàn chân mở rộng bằng vai (`~15–20 cm`).
  - Hai cánh tay dang nhẹ tách khỏi sườn một góc **`15°–25°`** (tạo khe sáng rõ ràng giữa cánh tay và vùng eo/ngực để hàm `center_run_width` tách riêng thân người khỏi cánh tay).
- **Góc Nghiêng 90° (`side`)**:
  - Giữ nguyên vị trí bàn chân trên vạch đánh dấu sàn (không bước tiến/lùi so với camera để bảo toàn giả định `shared_height` của [`fuse_camera_scale`](file:///d:/MORPH-AI/backend/app/camera_fusion.py)).
  - Xoay toàn thân đúng **90°** sang bên phải hoặc trái; hai tay buông dọc theo thân (không che vùng ngực trước hoặc độ cong thắt lưng/mông phía sau), lưng giữ tự nhiên.

### 3.3. Thiết lập Camera / Webcam
| Chế độ chụp | Khoảng cách từ ống kính đến người | Chiều cao đặt tâm ống kính | Góc nghiêng máy (Pitch) | Ánh sáng & Phông nền |
| :--- | :--- | :--- | :--- | :--- |
| **`upper_body`** (Webcam Laptop/Desktop) | **`1.2 m – 1.8 m`** (thấy rõ từ trên đỉnh đầu `~10 cm` đến qua phần hông trên / cạp quần) | Ngang tầm **xương ức / ngực** (`1.15 m – 1.35 m` so với sàn) | `0° ± 3°` (Vuông góc mặt đất, tránh gập màn hình laptop ngửa lên trần) | Ánh sáng trắng khuếch tán đều từ phía trước (`≥ 300 lux`), tránh ngược sáng cửa sổ; nền tường phẳng, không có người thứ 2 trong khung. |
| **`full_body`** (Webcam rời / Camera cố định) | **`2.2 m – 3.0 m`** (thấy trọn vẹn từ đỉnh đầu đến dưới lòng bàn chân, cách mép ảnh `≥ 5%` chiều cao khung) | Ngang tầm **vùng eo / rốn** (`0.95 m – 1.10 m` so với sàn) | `0° ± 2°` (Tránh méo phối cảnh chân ngắn/đầu to) | Nền phẳng đồng màu từ tường xuống sàn, không bị bóng đổ đậm dưới bàn chân. |

---

## 4. Phương Pháp Đo Lặp (2 Người Đo $\times$ 2 Lần) & Kiểm Soát Sai Số TEM

Mỗi tình nguyện viên phải được đo bởi **2 kỹ thuật viên độc lập (Measurer A và Measurer B)**, mỗi kỹ thuật viên thực hiện **2 lượt đo không liên tiếp** (đo toàn bộ các chỉ số lượt 1 rồi mới quay lại đo lượt 2, không nhìn kết quả của nhau).

### 4.1. Công thức tính Technical Error of Measurement (TEM)
1. **Sai số nội bộ của từng người đo (Intra-observer TEM)** trên $N$ đối tượng:
   $$\text{TEM}_{\text{intra}} = \sqrt{\frac{\sum_{i=1}^{N} \left(M_{i,1} - M_{i,2}\right)^2}{2N}}$$
   trong đó $M_{i,1}, M_{i,2}$ là lần đo 1 và 2 của cùng một kỹ thuật viên trên đối tượng $i$.
2. **Sai số giữa hai người đo (Inter-observer TEM)**:
   $$\text{TEM}_{\text{inter}} = \sqrt{\frac{\sum_{i=1}^{N} \left(\bar{M}_{i,A} - \bar{M}_{i,B}\right)^2}{2N}}$$
   trong đó $\bar{M}_{i,A} = \frac{M_{i,A1} + M_{i,A2}}{2}$ và $\bar{M}_{i,B} = \frac{M_{i,B1} + M_{i,B2}}{2}$.
3. **Sai số tương đối (`%TEM`)**:
   $$\%\text{TEM} = \frac{\text{TEM}}{\text{Grand Mean}} \times 100\%$$

### 4.2. Ngưỡng kiểm soát chất lượng số đo Ground-Truth (`gt_cm`)
- Một bản ghi chỉ được chấp nhận làm Ground-Truth khi:
  - Chênh lệch giữa 2 người đo $|\bar{M}_{i,A} - \bar{M}_{i,B}| \le 0.5\text{ cm}$ đối với Chiều cao / Rộng vai, và $\le 0.8\text{ cm}$ đối với Vòng ngực / Vòng eo / Vòng mông (nếu vượt ngưỡng, bắt buộc đo lại lần 3 để xác minh).
  - Toàn tập dữ liệu đạt **$\text{TEM}_{\text{intra}} \le 0.4\text{ cm}$** và **$\text{TEM}_{\text{inter}} \le 0.6\text{ cm}$** (`%TEM < 1.0%`).
- Giá trị Ground-Truth cuối cùng của mỗi chỉ số trên đối tượng $i$ là trung bình cộng của 4 lần đo:
  $$y_i^{\text{GT}} = \frac{M_{i,A1} + M_{i,A2} + M_{i,B1} + M_{i,B2}}{4}$$

---

## 5. Quy Tắc Tách Biệt Tập Dữ Liệu Theo Cá Thể (`subject_id`) & Chống Data Leakage

Để đảm bảo tính khách quan khoa học và tương thích với hàm [`verify_subject_disjoint_split()`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py):

1. **Đơn vị phân chia là Cá thể (`subject_id`), tuyệt đối không chia theo cặp ảnh (`scan_id`)**:
   - Mọi lượt chụp của cùng một tình nguyện viên (dù khác ngày, khác trang phục hay khác chế độ `upper_body` / `full_body`) đều phải mang cùng một mã `subject_id` (ví dụ `SUBJ_VN_001`) và chỉ được phép thuộc **một** trong hai tập:
     - `calibration` ($D_{\text{cal}}$): Dùng để ước lượng độ chệch $\hat{\mu}_{\text{cal}}$, phân vị phần dư Conformal $\hat{q}_{1-\alpha}$, hoặc tinh chỉnh hệ số giải phẫu `ANATOMICAL_SECTION_FACTORS`.
     - `evaluation` ($D_{\text{eval}}$): Tập kiểm định độc lập (Held-out Evaluation Set), **không bao giờ** được dùng để chọn tham số, ước lượng phân vị hiệu chuẩn hay tinh chỉnh hằng số trong code.
   - Điều kiện bắt buộc:
     $$\text{set}(\text{calibration\_subjects}) \cap \text{set}(\text{evaluation\_subjects}) = \emptyset$$
2. **Phân tầng mẫu (Stratified Cohort Design — Tối thiểu $N \ge 35$ người cho Pilot)**:
   - **Tập Calibration ($N_{\text{cal}} \ge 15$ người)** và **Tập Evaluation ($N_{\text{eval}} \ge 20$ người)** phải được phân tầng cân bằng theo:
     - Giới tính (`sex`): Nam (`~50%`) và Nữ (`~50%`).
     - Nhóm tỷ lệ thân (`torso_ratio_group`): Lưng ngắn (`short_torso`, $r_{\text{torso}} \le 0.280$), Trung bình (`medium_torso`, $0.280 < r_{\text{torso}} < 0.300$), Lưng dài (`long_torso`, $r_{\text{torso}} \ge 0.300$).
     - Nhóm BMI / Hình thái (`body_size_tier`): Nhỏ/Mảnh (`petite_slim`, $\text{BMI} < 20.5$), Chuẩn/Thể thao (`standard_athletic`, $20.5 \le \text{BMI} < 25.0$), Đậm người/Ngoại cỡ (`broad_plus`, $\text{BMI} \ge 25.0$).
     - Chiều cao trải rộng từ `150 cm` đến `185 cm`.

---

## 6. Biểu Mẫu Đồng Ý Tham Gia (Informed Consent) & Bảo Mật Dữ Liệu Hình Thể

Trước khi chụp hoặc đo bất kỳ tình nguyện viên nào, bắt buộc tuân thủ quy tắc bảo mật dữ liệu sinh trắc/hình thể của dự án (`AGENTS.md` Rule #6):

1. **Nội dung cam kết trong Informed Consent**:
   - Giải thích rõ mục đích thu thập ảnh 2 góc và số đo thước dây để kiểm định độ chính xác gợi ý kích cỡ trang phục.
   - Quyền rút lui và yêu cầu xóa vĩnh viễn toàn bộ ảnh gốc cũng như mô hình `.glb` bất kỳ lúc nào theo mã `subject_id`.
   - Cam kết **không bao giờ commit ảnh người thật hoặc file `.glb` cá nhân lên Git repository** (thư mục `verification/datasets/real_human_pilot/` nằm ngoài phạm vi theo dõi của Git công khai).
2. **Các trường xác nhận bắt buộc trong metadata**:
   - `informed_consent_signed: true`
   - `consent_form_id`: Mã biên bản đồng ý đã ký
   - `anonymized_face`: Khuyến nghị làm mờ vùng mặt dưới mắt nếu không ảnh hưởng đến mốc mũi `points[0]` hoặc chỉ lưu trữ cục bộ được mã hóa.

---

## 7. Cấu Trúc Thư Mục & Schema Dữ Liệu (`manifest.json` & `measurements.csv`)

Khi dữ liệu thực nghiệm được thu thập, đặt tại `verification/datasets/real_human_pilot/` theo cấu trúc sau để các script [`evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py) và [`benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py) tự động phát hiện và kiểm định:

```
verification/datasets/real_human_pilot/
├── manifest.json
├── measurements.csv
└── images/
    ├── SUBJ_VN_001/
    │   ├── full_front.png
    │   ├── full_side.png
    │   ├── upper_front.png
    │   └── upper_side.png
    └── SUBJ_VN_002/
        └── ...
```

### 7.1. Định dạng `manifest.json`
```json
{
  "dataset_version": "1.1.0",
  "protocol_standard": "ISO-7250-1:2017 & ISO-8559-1:2017",
  "intra_tem_cm": { "chest_cm": 0.28, "waist_cm": 0.25, "hip_cm": 0.31, "shoulder_width_cm": 0.22 },
  "inter_tem_cm": { "chest_cm": 0.41, "waist_cm": 0.38, "hip_cm": 0.44, "shoulder_width_cm": 0.35 },
  "subjects": [
    {
      "subject_id": "SUBJ_VN_001",
      "split": "calibration",
      "informed_consent_signed": true,
      "consent_form_id": "CONSENT-2026-001",
      "sex": "female",
      "body_size_tier": "standard_athletic",
      "torso_ratio_group": "medium_torso",
      "attire": "tight_activewear",
      "camera_distance_m": 2.4,
      "ground_truth_cm": {
        "height_cm": 162.4,
        "chest_cm": 86.2,
        "waist_cm": 67.5,
        "hip_cm": 93.0,
        "shoulder_width_cm": 37.2,
        "shoulder_biacromial_gt_cm": 37.2,
        "shoulder_joint_gt_cm": 33.8
      },
      "captures": {
        "full_body": { "front": "images/SUBJ_VN_001/full_front.png", "side": "images/SUBJ_VN_001/full_side.png" },
        "upper_body": { "front": "images/SUBJ_VN_001/upper_front.png", "side": "images/SUBJ_VN_001/upper_side.png" }
      }
    }
  ]
}
```

### 7.2. Định dạng `measurements.csv`
```csv
subject_id,split,informed_consent_signed,sex,body_size_tier,torso_ratio_group,attire,height_cm,chest_a1,chest_a2,chest_b1,chest_b2,chest_gt_cm,waist_gt_cm,hip_gt_cm,shoulder_biacromial_gt_cm,shoulder_joint_gt_cm,upper_front_path,upper_side_path,full_front_path,full_side_path
SUBJ_VN_001,calibration,true,female,standard_athletic,medium_torso,tight_activewear,162.4,86.1,86.3,86.2,86.2,86.2,67.5,93.0,37.2,33.8,images/SUBJ_VN_001/upper_front.png,images/SUBJ_VN_001/upper_side.png,images/SUBJ_VN_001/full_front.png,images/SUBJ_VN_001/full_side.png
```

---

## 8. Mục Tiêu Đề Xuất Cho Pilot (Proposed Pilot Target Thresholds — Ready-to-Wear)

> [!IMPORTANT]  
> **Phân biệt rõ giữa Tiêu chuẩn Quốc tế và Mục tiêu Kỹ thuật Đề xuất Nội bộ**:  
> Các tiêu chuẩn **ISO 8559-1:2017** và **ISO 7250-1:2017** chỉ quy định **định nghĩa vị trí mốc giải phẫu và phương pháp đặt thước đo**, hoàn toàn **KHÔNG** quy định ngưỡng sai số cho hệ thống quét cơ thể 3D từ ảnh 2D.  
> Toàn bộ các con số trong bảng dưới đây (`MAE ≤ 2.5 cm`, `|Bias| ≤ 1.0 cm`, `P90 ≤ 4.0 cm`, `P95 ≤ 5.0 cm`, `Size Agreement ≥ 82%–85%`) là **Mục tiêu Kỹ thuật Đề xuất cho Pilot (Proposed Pilot Target Thresholds)** do đội ngũ kỹ thuật MORPH AI xây dựng dựa trên nửa bước nhảy giữa hai size liền kề trong bảng size may sẵn (`Ready-to-Wear grade interval = 4.0 cm – 8.0 cm`, bán kính nửa bậc size `±2.0 cm – ±4.0 cm`). Đây là **mục tiêu nghiệm thu nội bộ cần đạt tới**, không phải kết quả đã được chứng minh thực nghiệm ở thời điểm hiện tại.

Hệ thống hướng tới đạt các ngưỡng mục tiêu đề xuất sau trên **Tập Đánh Giá Độc Lập (`evaluation` split, $N_{\text{eval}} \ge 20$ người, trang phục ôm chuẩn)** trước khi gỡ cảnh báo `not_validated`:

| Nhóm Tiêu Chí | Chỉ Số Đánh Giá | Mục Tiêu Đề Xuất Pilot (`full_body`) | Mục Tiêu Đề Xuất Pilot (`upper_body`) | Cơ Sở Kỹ Thuật Đề Xuất (Nội Bộ) |
| :--- | :--- | :---: | :---: | :--- |
| **1. Sai số tuyệt đối trung bình (MAE)** | `chest_cm` (Vòng ngực) | **`≤ 2.5 cm`** *(Proposed Target)* | **`≤ 3.0 cm`** *(Proposed Target)* | Nhỏ hơn nửa bước nhảy size áo (`4.0 cm`). |
| | `waist_cm` (Vòng eo) | **`≤ 2.5 cm`** *(Proposed Target)* | **`≤ 3.0 cm`** *(Proposed Target)* | Đảm bảo phân biệt giữa các size S/M/L/XL và quần 28–34. |
| | `hip_cm` (Vòng mông) | **`≤ 2.5 cm`** *(Proposed Target)* | **`Blocked (None)`** | Chế độ `upper_body` bắt buộc khóa `hip_cm = None` (Coverage = `0%`). |
| | `shoulder_width_cm` (Rộng vai) | **`≤ 1.8 cm`** *(Proposed Target — sau hiệu chuẩn độ chệch mốc `11–12`)* | **`≤ 2.0 cm`** *(Proposed Target — sau hiệu chuẩn độ chệch mốc `11–12`)* | Đánh giá sau khi hiệu chuẩn độ chệch hệ thống giữa mốc MediaPipe `11–12` và mỏm *Acromion*. |
| **2. Độ chệch hệ thống (Signed Bias)** | $\|\text{Mean Signed Error}\|$ | **`≤ ±1.0 cm`** *(Proposed Target)* | **`≤ ±1.2 cm`** *(Proposed Target)* | Đảm bảo hệ thống không bị thiên lệch cộng/trừ một chiều sau hiệu chuẩn. |
| **3. Sai số phân vị cao (Tail Error)** | **P90 Absolute Error** | **`≤ 4.0 cm`** *(Proposed Target)* | **`≤ 4.5 cm`** *(Proposed Target)* | 90% người dùng không bị lệch quá 1 bậc size. |
| | **P95 Absolute Error** | **`≤ 5.0 cm`** *(Proposed Target)* | **`≤ 5.5 cm`** *(Proposed Target)* | Giới hạn sai số biên trên các dáng người đặc biệt. |
| **4. Độ lặp lại (Repeatability)** | **Within-Subject SD** (3 lần chụp liên tiếp) | **`≤ 0.8 cm`** *(Proposed Target)* | **`≤ 1.0 cm`** *(Proposed Target)* | Cùng một người đứng chụp lại 3 lần không bị nhảy size. |
| **5. An toàn kiểm soát đầu vào** | **True Rejection Rate** (Ảnh sai góc/thiếu sáng/mất mốc) | **`≥ 95.0%`** *(Proposed Target)* | **`≥ 95.0%`** *(Proposed Target)* | Từ chối sớm ảnh lỗi thay vì xuất số đo sai lệch. |
| **6. Độ chính xác gợi ý size (RTW Hit Rate)** | **Exact hoặc Adjacent Boundary Size Match** | **`≥ 85.0%`** *(Proposed Target)* | **`≥ 80.0% – 82.0%`** *(Proposed Target — chỉ tính áo `top`/`outerwear`)* | Tỷ lệ gợi ý trùng khớp với size người thật mặc vừa thực tế. |

---

## 9. Phương Pháp Hiệu Chuẩn Khoảng Dự Đoán Không Chắc Chắn (Calibrated Prediction Intervals — Split Conformal Prediction & Empirical Residual Quantiles)

### 9.1. Lý do bác bỏ công thức tham số $\pm 1.96 \times \text{RMSE}$

Trong các hệ thống đo cơ thể từ ảnh 2D, công thức khoảng tin cậy tham số cổ điển $\hat{y} \pm 1.96 \times \text{RMSE}$ **bị loại bỏ hoàn toàn** vì 3 lý do toán học và thực nghiệm:
1. **Vi phạm giả định phân phối chuẩn đối xứng tâm $0$ (Non-Gaussian & Right-Skewed Errors)**: Độ dày quần áo (`clothing inflation`), tóc hoặc góc tay hơi mở luôn làm bóng silhouette phình ra thay vì co lại, tạo ra phân phối phần dư lệch hẳn về một phía và có đuôi nặng (heavy tails).
2. **Phương sai không đồng nhất (Heteroscedasticity)**: Độ bất định ở chế độ `upper_body` (phải suy luận chiều cao qua đa mỏ neo sọ–vai–hông) lớn hơn chế độ `full_body`, và sai số trên nhóm ngoại cỡ (`broad_plus`) hoặc lưng dài/ngắn cực đoan khác với nhóm hình thể trung bình.
3. **Thiếu bảo chứng độ phủ hữu hạn mẫu (Lack of Finite-Sample Coverage Guarantee)**: Nhân $1.96 \times \text{RMSE}$ không đảm bảo tỷ lệ phần trăm số đo thực tế rơi vào trong khoảng dự đoán trên tập kiểm định độc lập khi cỡ mẫu Pilot vừa phải ($N_{\text{cal}} \approx 15\text{–}30$).

### 9.2. Công thức Khoảng Dự Đoán Split Conformal & Phân Vị Phần Dư Thực Nghiệm

Giả sử tập dữ liệu được chia tách nghiêm ngặt theo `subject_id` thành **Tập Hiệu Chuẩn** $D_{\text{cal}} = \{(x_i, y_i^{\text{GT}})\}_{i=1}^{n}$ ($n = |D_{\text{cal}}|$) và **Tập Kiểm Định Độc Lập** $D_{\text{eval}} = \{(x_j, y_j^{\text{GT}})\}_{j=1}^{m}$ ($m = |D_{\text{eval}}|$), với $\text{subjects}(D_{\text{cal}}) \cap \text{subjects}(D_{\text{eval}}) = \emptyset$.

Với từng cặp `(capture_mode, metric_key)` (và từng phân nhóm `subgroup`):
1. **Tính phần dư có dấu (Signed Residual) và khử chệch trên tập hiệu chuẩn $D_{\text{cal}}$**:
   $$r_i = y_i^{\text{GT}} - \hat{y}_i, \quad i = 1, \dots, n$$
   $$\hat{\mu}_{\text{cal}} = \frac{1}{n} \sum_{i=1}^{n} r_i, \qquad s_i = \left|y_i^{\text{GT}} - \left(\hat{y}_i + \hat{\mu}_{\text{cal}}\right)\right| = \left|r_i - \hat{\mu}_{\text{cal}}\right|$$
   trong đó $\hat{\mu}_{\text{cal}}$ là độ chệch hiệu chuẩn (`calibration_bias_correction_cm`) và $s_i$ là điểm bất tương hợp tuyệt đối sau khử chệch (*bias-corrected nonconformity score*).

2. **Khoảng Conformal Đối Xứng Có Khử Bias (Bias-Corrected Split Conformal Interval) ở mức tin cậy $1 - \alpha \in \{90\%, 95\%\}$**:
   - Mức phân vị hữu hạn mẫu (Finite-sample conformal quantile level):
     $$p_{\text{conf}}(n, \alpha) = \min\left(1.0,\; \frac{\lceil (n + 1)(1 - \alpha) \rceil}{n}\right)$$
   - Bán kính khoảng dự đoán hiệu chuẩn (`conformal_half_width_cm`):
     $$\hat{q}_{1-\alpha} = \text{Quantile}\left(\{s_1, \dots, s_n\};\; p_{\text{conf}}(n, \alpha)\right)$$
   - Khoảng dự đoán cho một cá thể mới $x$ trên tập đánh giá:
     $$C_{1-\alpha}^{\text{sym}}(x) = \left[\hat{y}(x) + \hat{\mu}_{\text{cal}} - \hat{q}_{1-\alpha},\; \hat{y}(x) + \hat{\mu}_{\text{cal}} + \hat{q}_{1-\alpha}\right]$$
   - Độ rộng toàn khoảng dự đoán: $\text{Width}_{1-\alpha}^{\text{sym}} = 2\hat{q}_{1-\alpha}$. Khi nghiệm thu xong trên tập người thật, giá trị $\hat{q}_{0.90}$ hoặc $\hat{q}_{0.95}$ (theo từng `capture_mode` và `metric_key`) chính là cơ sở thực nghiệm để gán cho trường `uncertainty_cm`.

3. **Khoảng Phân Vị Thực Nghiệm Bất Đối Xứng (Asymmetric Empirical Residual Quantile Interval $[\hat{q}_{\alpha/2}, \hat{q}_{1-\alpha/2}]$)**:
   - Để phản ánh trực tiếp độ lệch phải/trái do trang phục (`clothing inflation` khiến $\hat{y} > y^{\text{GT}} \Rightarrow r_i < 0$), lấy hai phân vị thực nghiệm của phần dư có dấu $r_i$ trên $D_{\text{cal}}$:
     $$\hat{q}_{\alpha/2}^{\text{raw}} = \text{Quantile}\left(\{r_1, \dots, r_n\};\; \frac{\alpha}{2}\right), \qquad \hat{q}_{1-\alpha/2}^{\text{raw}} = \text{Quantile}\left(\{r_1, \dots, r_n\};\; 1 - \frac{\alpha}{2}\right)$$
   - Khoảng dự đoán bất đối xứng cho cá thể mới $x$:
     $$C_{1-\alpha}^{\text{asym}}(x) = \left[\hat{y}(x) + \hat{q}_{\alpha/2}^{\text{raw}},\; \hat{y}(x) + \hat{q}_{1-\alpha/2}^{\text{raw}}\right]$$
     với độ rộng toàn khoảng $\text{Width}_{1-\alpha}^{\text{asym}} = \hat{q}_{1-\alpha/2}^{\text{raw}} - \hat{q}_{\alpha/2}^{\text{raw}}$.

### 9.3. Chỉ số Đánh Giá Khoảng Dự Đoán trên Tập Kiểm Định Độc Lập $D_{\text{eval}}$ & Phân Nhóm (Subgroup Breakdown)

Trên tập kiểm định độc lập $D_{\text{eval}}$, bắt buộc báo cáo đầy đủ:
1. **Độ phủ thực nghiệm (Empirical Coverage %)**:
   $$\text{Empirical Coverage}_{1-\alpha}(D_{\text{eval}}) = \frac{1}{|D_{\text{eval}}|} \sum_{j \in D_{\text{eval}}} \mathbb{I}\left(y_j^{\text{GT}} \in C_{1-\alpha}(x_j)\right) \times 100\%$$
   (So sánh trực tiếp với mức độ phủ mục tiêu $90.0\%$ khi $\alpha = 0.10$ và $95.0\%$ khi $\alpha = 0.05$).
2. **Độ rộng khoảng dự đoán (Mean / Median Interval Width in cm)**:
   - Báo cáo cả `half_width_cm` ($\pm \hat{q}_{1-\alpha}$) và `interval_width_cm` ($2\hat{q}_{1-\alpha}$ đối với Split Conformal; $\hat{q}_{1-\alpha/2}^{\text{raw}} - \hat{q}_{\alpha/2}^{\text{raw}}$ đối với Asymmetric Quantile).
3. **Phân rã theo từng nhóm dữ liệu độc lập (Subgroup Breakdown)**:
   - Theo **Chế độ chụp (`capture_mode`)**: `full_body` vs `upper_body`.
   - Theo **Chỉ số đo (`metric_key`)**: `chest_cm`, `waist_cm`, `hip_cm`, `shoulder_width_cm`.
   - Theo **Nhóm tỷ lệ thân (`torso_ratio_group`)**: `short_torso` ($r_{\text{torso}} \le 0.280$), `medium_torso` ($0.280 < r_{\text{torso}} < 0.300$), `long_torso` ($r_{\text{torso}} \ge 0.300$).
   - Theo **Nhóm kích thước cơ thể (`body_size_tier`)**: `petite_slim`, `standard_athletic`, `broad_plus`.
   - Theo **Điều kiện trang phục (`attire_condition`)**: `tight_fit_baseline` vs `casual_clothed_sensitivity`.

---

## 10. Quy Trình Thực Thi Harness Kiểm Định & Kết Luận Nghiệm Thu

Bộ công cụ đánh giá tự động được triển khai tại [`verification/scripts/evaluate_human_validation_cohort.py`](file:///d:/MORPH-AI/verification/scripts/evaluate_human_validation_cohort.py) và đồng bộ trong [`verification/scripts/benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py):

```powershell
D:\MORPH-AI\backend\.venv\Scripts\python.exe verification\scripts\evaluate_human_validation_cohort.py
D:\MORPH-AI\backend\.venv\Scripts\python.exe verification\scripts\benchmark_scan_product_readiness.py
```

- **Khi chưa có dữ liệu người thật trong `verification/datasets/real_human_pilot/`**:
  - Script tự động kiểm chứng thuật toán hiệu chuẩn khoảng dự đoán (Split Conformal + Asymmetric Empirical Quantile, Empirical Coverage, Interval Width và Subgroup Breakdown) trên **Tập Kiểm Thử Hình Học Phân Tách Theo Cá Thể (Synthetic Subject-Disjoint Cohort)**.
  - Đồng thời xuất kết luận bắt buộc trong báo cáo JSON và console:
    - `"REAL_HUMAN_DATASET_STATUS": "MISSING_EMPIRICAL_COHORT"`
    - `"human_accuracy_validation_status": "NOT_ACCEPTED_NO_EMPIRICAL_DATASET"`
    - `"conclusion": "CHƯA THỂ NGHIỆM THU ĐỘ CHÍNH XÁC TRÊN NGƯỜI THẬT (Human accuracy cannot be accepted yet because no consented real-human dataset is present)."`
