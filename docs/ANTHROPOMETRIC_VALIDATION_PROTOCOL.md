# Quy Trình Chuẩn Đo Nhân Trắc Học & Nghiệm Thu Thực Nghiệm Trên Người Thật (`docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`)

> **Mục đích tài liệu**:  
> Thiết lập quy trình chuẩn hóa theo tiêu chuẩn quốc tế **ISO 7250-1** (Basic human body measurements for technological design) và **ISO 8559-1:2017** (Size designation of clothes — Part 1: Anthropometric definitions for body measurement) để thu thập số đo thước dây trên người thật, kiểm soát sai số người đo (**TEM**), chống rò rỉ dữ liệu theo cá thể (`subject_id`), và tích hợp trực tiếp vào bộ kiểm định [`verification/scripts/benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py).

---

## 1. Tuyên Bố Minh Bạch Về Trạng Thái Hiện Tại

Hiện tại, bộ máy dựng hình 3D của MORPH AI (`ENGINE = "mediapipe-two-photo-fit-v4"`) đã hoàn tất **Kiểm thử Hình học & Hệ thống (Synthetic / Geometric Verification)** nhưng **CHƯA có tập dữ liệu đo thước dây trên người thật (`REAL_HUMAN_DATASET_STATUS = "MISSING_EMPIRICAL_COHORT"`)**.  
- Cho đến khi hoàn tất giai đoạn thu thập và nghiệm thu theo tài liệu này:
  - Trường `uncertainty_cm` trong báo cáo số đo ([`backend/app/report.py`](file:///d:/MORPH-AI/backend/app/report.py)) bắt buộc giữ giá trị `null` (`None`).
  - Không được tuyên bố sai số tuyệt đối $\pm X\text{ cm}$ trên người thật trong giao diện người dùng hay tài liệu thương mại.

---

## 2. Định Nghĩa Mốc Giải Phẫu & Cách Đặt Thước Dây (ISO 8559-1 / ISO 7250-1)

Dụng cụ bắt buộc:
- **Thước dây nhân trắc không giãn** (Fiberglass hoặc thép mềm có vạch chia `1 mm`, chiều rộng bản thước $\le 7\text{ mm}$, kiểm chuẩn định kỳ với thước chuẩn kim loại).
- **Thước đo chiều cao cố định (Stadiometer)** có thanh chặn đỉnh đầu vuông góc với tường.

| STT | Chỉ số (`metric_key`) | Tên chuẩn ISO 8559-1 | Điểm mốc giải phẫu & Cách đặt thước | Điều kiện đọc số |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `height_cm` | **Stature** (Chiều cao đứng) | Khoảng cách thẳng đứng từ sàn nhà đến điểm cao nhất của hộp sọ (**Vertex**) khi đầu giữ ở mặt phẳng **Frankfort** (mé dưới ổ mắt ngang với mép trên ống tai ngoài). | Đi chân trần, hai gót chân chạm nhau, lưng/mông/chты chạm thước đo, hít nhẹ và giữ thẳng cột sống. Làm tròn `0.1 cm`. |
| 2 | `shoulder_width_cm` | **Biacromial Breadth** (Rộng hai mỏm cùng vai) | Khoảng cách ngang giữa hai điểm ngoài cùng của mỏm cùng vai trái và phải (**Acromion**), đo từ phía trước hoặc bằng thước kẹp nhân trắc (Anthropometer) / chiếu phẳng ngang. | Hai vai thả lỏng tự nhiên, không gồng hoặc rụt vai. Làm tròn `0.1 cm`. |
| 3 | `chest_cm` | **Chest / Bust Girth** (Vòng ngực) | Thước dây đi ngang qua điểm nhô cao nhất của ngực (**Thelion / Bustpoint** ở nữ) hoặc mức xương ức giữa (**Mesosternale** — khoang liên sườn thứ 4 ở nam), vòng qua dưới hõm nách và ngang qua phần dưới xương bả vai. | Mặt phẳng thước dây **song song tuyệt đối với mặt đất**. Đọc số ở **cuối thì thở ra bình thường (End-tidal expiration)**, thước ôm sát bề mặt nhưng không làm lún da/mô mềm. |
| 4 | `waist_cm` | **Natural Waist Girth** (Vòng eo tự nhiên) | Chu vi nhỏ nhất của phần thân trên, nằm giữa bờ dưới xương sườn thứ 10 và mào chậu (**Iliocristale**), thường cao hơn rốn `~2–3 cm`. | Bụng thả lỏng tự nhiên (không hóp bụng), mặt phẳng thước dây nằm ngang, đọc ở cuối thì thở ra bình thường. |
| 5 | `hip_cm` | **Hip / Seat Girth** (Vòng mông) | Chu vi ngang lớn nhất vòng qua điểm nhô cao nhất của cơ mông phía sau (**Gluteal prominence / Buttock protrusion**) và ngang qua xương mu phía trước. | Hai bàn chân khép sát nhau, cơ mông thả lỏng, kiểm tra thước dây nằm trên cùng một mặt phẳng ngang ở cả phía trước và phía sau. |

---

## 3. Quy Chuẩn Tư Thế, Trang Phục & Thiết Lập Camera Khi Chụp Đối Chứng

Để giảm thiểu nhiễu ngoại cảnh và tách bạch lỗi thuật toán khỏi lỗi vận hành người dùng, mỗi tình nguyện viên phải được chụp trong điều kiện chuẩn hóa:

### 3.1. Trang phục khi đo và chụp
1. **Lượt chụp Chuẩn (Baseline Tight-Fit — Bắt buộc cho tất cả tình nguyện viên)**:
   - Mặc đồ tập thể thao ôm sát cơ thể (áo thun ôm / tank-top mỏng và quần legging / quần short ôm sát, độ dày vải $< 1.5\text{ mm}$), màu sắc tương phản rõ với nền tường.
   - Tóc dài phải buộc gọn phía trên gáy để lộ rõ đường viền cổ và mỏm vai (`Acromion`).
2. **Lượt chụp Thực tế (Everyday Casual — Đánh giá độ nhạy trang phục)**:
   - Mặc áo phông thường ngày (regular-fit) hoặc áo sơ mi đóng thùng và quần dài ống đứng để định lượng độ phình silhouette do quần áo (`clothing inflation bias`).

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
     - `calibration`: Dùng để tinh chỉnh hệ số giải phẫu `ANATOMICAL_SECTION_FACTORS` hoặc bù trừ trang phục.
     - `evaluation`: Tập kiểm định độc lập (Held-out Evaluation Set), **không bao giờ** được dùng để chọn tham số hay tinh chỉnh hằng số trong code.
   - Điều kiện bắt buộc:
     $$\text{set}(\text{calibration\_subjects}) \cap \text{set}(\text{evaluation\_subjects}) = \emptyset$$
2. **Phân tầng mẫu (Stratified Cohort Design — Tối thiểu $N \ge 35$ người cho Pilot)**:
   - **Tập Calibration ($N_{\text{cal}} \ge 15$ người)** và **Tập Evaluation ($N_{\text{eval}} \ge 20$ người)** phải được phân tầng cân bằng theo:
     - Giới tính: Nam (`~50%`) và Nữ (`~50%`).
     - Nhóm BMI / Hình thái: Gầy (`BMI < 18.5`), Chuẩn (`18.5 ≤ BMI < 23.0`), Đậm người / Thể thao (`23.0 ≤ BMI < 27.5`), Ngoại cỡ (`BMI ≥ 27.5`).
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

Khi dữ liệu thực nghiệm được thu thập, đặt tại `verification/datasets/real_human_pilot/` theo cấu trúc sau để script [`benchmark_scan_product_readiness.py`](file:///d:/MORPH-AI/verification/scripts/benchmark_scan_product_readiness.py) tự động phát hiện và kiểm định:

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
  "dataset_version": "1.0.0",
  "protocol_standard": "ISO-8559-1:2017",
  "intra_tem_cm": { "chest_cm": 0.28, "waist_cm": 0.25, "hip_cm": 0.31, "shoulder_width_cm": 0.22 },
  "inter_tem_cm": { "chest_cm": 0.41, "waist_cm": 0.38, "hip_cm": 0.44, "shoulder_width_cm": 0.35 },
  "subjects": [
    {
      "subject_id": "SUBJ_VN_001",
      "split": "calibration",
      "informed_consent_signed": true,
      "consent_form_id": "CONSENT-2026-001",
      "sex": "female",
      "attire": "tight_activewear",
      "camera_distance_m": 2.4,
      "ground_truth_cm": {
        "height_cm": 162.4,
        "chest_cm": 86.2,
        "waist_cm": 67.5,
        "hip_cm": 93.0,
        "shoulder_width_cm": 37.2
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
subject_id,split,informed_consent_signed,sex,attire,height_cm,chest_a1,chest_a2,chest_b1,chest_b2,chest_gt_cm,waist_gt_cm,hip_gt_cm,shoulder_gt_cm,upper_front_path,upper_side_path,full_front_path,full_side_path
SUBJ_VN_001,calibration,true,female,tight_activewear,162.4,86.1,86.3,86.2,86.2,86.2,67.5,93.0,37.2,images/SUBJ_VN_001/upper_front.png,images/SUBJ_VN_001/upper_side.png,images/SUBJ_VN_001/full_front.png,images/SUBJ_VN_001/full_side.png
```

---

## 8. Ngưỡng Nghiệm Thu Sản Phẩm (Pilot Acceptance Thresholds — Ready-to-Wear)

Vì bước nhảy giữa hai size liền kề trong bảng size may sẵn (`Ready-to-Wear` trên 160 sản phẩm của MORPH AI) là **`4.0 cm – 8.0 cm`** đối với Vòng ngực/eo/mông (bán kính nửa khoảng size là `±2.0 cm – ±4.0 cm`), hệ thống phải đạt các ngưỡng sau trên **Tập Đánh Giá Độc Lập (`evaluation` split, $N \ge 20$ người, trang phục ôm chuẩn)** trước khi gỡ cảnh báo `not_validated`:

| Nhóm Tiêu Chí | Chỉ Số Đánh Giá | Ngưỡng Chấp Nhận Pilot (`full_body`) | Ngưỡng Chấp Nhận Pilot (`upper_body`) | Lý Do Kỹ Thuật / Thương Mại |
| :--- | :--- | :---: | :---: | :--- |
| **1. Sai số tuyệt đối trung bình (MAE)** | `chest_cm` (Vòng ngực) | **`≤ 2.5 cm`** | **`≤ 3.0 cm`** | Nhỏ hơn nửa bước nhảy size áo (`4.0 cm`). |
| | `waist_cm` (Vòng eo) | **`≤ 2.5 cm`** | **`≤ 3.0 cm`** | Đảm bảo phân biệt chính xác giữa các size S/M/L/XL và quần 28–34. |
| | `hip_cm` (Vòng mông) | **`≤ 2.5 cm`** | **`Blocked (None)`** | Chế độ `upper_body` bắt buộc khóa `hip_cm = None` (Coverage = `0%`). |
| | `shoulder_width_cm` (Rộng vai) | **`≤ 1.8 cm`** | **`≤ 2.0 cm`** | Phụ thuộc khoảng cách ngang hai mốc `11, 12`. |
| **2. Độ chệch hệ thống (Signed Bias)** | $\|\text{Mean Signed Error}\|$ | **`≤ ±1.0 cm`** | **`≤ ±1.2 cm`** | Đảm bảo hệ thống không bị thiên lệch cộng/trừ một chiều. |
| **3. Sai số phân vị cao (Tail Error)** | **P90 Absolute Error** | **`≤ 4.0 cm`** | **`≤ 4.5 cm`** | 90% người dùng không bị lệch quá 1 bậc size. |
| | **P95 Absolute Error** | **`≤ 5.0 cm`** | **`≤ 5.5 cm`** | Giới hạn sai số biên trên các dáng người đặc biệt. |
| **4. Độ lặp lại (Repeatability)** | **Within-Subject SD** (3 lần chụp liên tiếp) | **`≤ 0.8 cm`** | **`≤ 1.0 cm`** | Cùng một người đứng chụp lại 3 lần không bị nhảy size. |
| **5. An toàn kiểm soát đầu vào** | **True Rejection Rate** (Ảnh sai góc/thiếu sáng/mất mốc) | **`≥ 95.0%`** | **`≥ 95.0%`** | Từ chối sớm ảnh lỗi thay vì xuất số đo sai lệch. |
| **6. Độ chính xác gợi ý size (RTW Hit Rate)** | **Exact hoặc Adjacent Boundary Size Match** | **`≥ 85.0%`** | **`≥ 82.0%`** (chỉ tính áo `top`/`outerwear`) | Tỷ lệ gợi ý trùng khớp với size người thật mặc vừa thực tế. |
