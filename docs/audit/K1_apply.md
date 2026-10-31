# K1 — Cách code hiện tại áp số đo lên mô hình

> Phạm vi: chỉ đọc các file trong mục "liên quan" của [`K0_map.md`](K0_map.md).
> Không sửa code. Mọi kết luận đều kèm `file:dòng`.

## Kết luận ngắn

Code **không dùng MakeHuman measure modifiers** (`measure-shoulder`, `measure-bust-circ`, …).
Nó dựng một lưới nền từ **macro phenotype của Anny** (đã nướng sẵn), rồi **biến dạng hình học
trực tiếp** để các vòng ngực/eo/mông khớp số đo. Các "modifier" thực sự được set chỉ là
**local changes** của Anny khi sinh basis (ngực, mông, hông, V-shape, cơ vai), không phải measure target.

---

## 1. Có dùng measure modifiers không?

**Không.** Không có `measure-*` nào trong mã dự án. Tìm trên `backend/app` và
`verification/scripts` với `measure-|measure_|modifier` → **không có kết quả**.

Thay vào đó:

- Số đo được áp bằng **cắt lát + scale hình học**: `closed_torso_section()` và
  `fit_measurement_targets()` — `backend/app/measurements.py:75`, `backend/app/measurements.py:212`.
- Lưới nền được sinh từ Anny với 2 nhóm tham số:
  - macro phenotype (mục 2),
  - local changes (bảng dưới).

### 1.1. Các local change được set (khi nướng basis, không phải runtime)

Nguồn: `verification/scripts/build_anny_bases.py:40-55`, truyền vào model tại dòng `120`.

| Giới | Local change | Giá trị |
|---|---|---:|
| female | `breast-volume-vert-up` | 0.70 |
| female | `breast-point-incr` | 0.20 |
| female | `buttocks-volume-incr` | 0.50 |
| female | `hip-scale-horiz-incr` | 0.40 |
| female | `hip-trans-out` | 0.15 |
| male | `torso-vshape-incr` | 0.50 |
| male | `torso-muscle-pectoral-incr` | 0.10 |
| male | `l-upperarm-shoulder-muscle-incr` | 0.35 |
| male | `r-upperarm-shoulder-muscle-incr` | 0.35 |
| male | `buttocks-volume-incr` | 0.05 |

Các label không tồn tại trong phiên bản Anny sẽ bị bỏ qua
(`build_anny_bases.py:110-115`).

### 1.2. Thứ tự gọi

Trong `build_anny_bases.py`:

1. Duyệt giới: `female` rồi `male` — dòng `111`.
2. Với mỗi giới, duyệt cân nặng `0.30 → 0.50 → 0.70` — dòng `116`.
3. Với mỗi cân nặng, duyệt cơ `0.35 → 0.60` — dòng `117`.
4. Tạo dict macro mặc định `0.5` cho **tất cả** phenotype — dòng `118`.
5. Ghi đè `gender`, `weight`, `muscle`, `height`, `age` — dòng `119`.
6. Gọi model **một lần** với `pose_parameters`, `phenotype_kwargs`, `local_changes_kwargs` — dòng `120`.
   Local changes đi theo thứ tự khai báo trong dict ở dòng `40-55`; bên trong Anny chúng được
   áp như các blend shape, không phải từng lệnh tuần tự.

Ở runtime **không gọi modifier nào**: `anny_body.build()` chỉ nội suy 12 lưới đã nướng
(`backend/app/anny_body.py:64-83`, `97-107`).

### 1.3. Cái gần nhất với "modifier" ở runtime

- `shape_sex()` nhân hệ số ngang theo chiều cao cho lưới MakeHuman fallback
  (`backend/app/anatomy.py:155-177`), dùng bảng `_LATERAL` ở `anatomy.py:25-34`:
  - female: `1.04 / 1.05` ở hông–eo, `0.95` ở vai, `0.97` ở ngực;
  - male: `0.96–0.97` ở hông, `1.05` ở vai, `1.02` ở ngực.
  - `_VOLUMES` hiện **rỗng** (`anatomy.py:36-40`) — không còn bump ngực/mông.
- `proportions.apply_rings()` scale cổ/đùi/bắp chân/cổ chân theo hệ số
  (`backend/app/proportions.py:17-25`, `78-104`), không phải measure modifier.

---

## 2. Có dùng macro modifiers không?

**Có, nhưng chỉ khi nướng basis.** Runtime chỉ dùng lại kết quả.

| Macro | Giá trị khi nướng | Ghi chú |
|---|---|---|
| `gender` | `0.0` (female) / `1.0` (male) | `build_anny_bases.py:119` |
| `weight` | `0.30 / 0.50 / 0.70` | `build_anny_bases.py:34`, `119` |
| `muscle` | `0.35 / 0.60` | `build_anny_bases.py:35`, `119` |
| `height` | luôn `0.50` | `build_anny_bases.py:119`; chiều cao thật được áp bằng scale lưới |
| `age` | luôn `0.50` | `build_anny_bases.py:119` |
| `proportions` | luôn `0.50` | không ghi đè, lấy mặc định ở dòng `118` |

Runtime:

- `phenotype_from_measurements()` chỉ chọn `weight` từ tỷ lệ eo/chiều cao
  (`anny_body.py:49-61`): `0.40 → 0.30`, `0.48 → 0.50`, `0.58 → 0.70`; `muscle` cố định `0.45`.
- `anny_body.build(sex, weight, muscle, height_cm)` nội suy basis theo `sex × weight × muscle`
  (`anny_body.py:97-107`).
- `height` phenotype không được dùng để thay đổi hình dáng; thay vào đó toàn bộ lưới
  nhân với `height_cm / 100` (`anny_body.py:101-102`).

---

## 3. Đơn vị đang dùng — có chỗ nào sai không?

### 3.1. Đơn vị từng tầng

| Tầng | Đơn vị | Bằng chứng |
|---|---|---|
| API đầu vào | cm (`height_cm` 100–230) | `main.py:276` |
| Số đo ước lượng | cm | `measurements.py:49-70` |
| Macro phenotype / local change | slider 0..1; code dùng local change 0.05–0.70 | `build_anny_bases.py:34-55`, `118-119` |
| Lưới basis | cao đúng `1.0`, chân `y=0` | `build_anny_bases.py:65-71`; `models/anny-bases.json` |
| Lưới runtime | **mét** | `anny_body.py:97-103` |
| Hàm fit | trong **mét** (`h = height_cm/100`), nhưng target/chu vi tính bằng **cm** | `measurements.py:220`, `235`, `271-274` |
| Báo cáo/API | cm | `report.py:74-108` |
| Vòng phụ | `height_m` khi scale, `y` chuẩn hoá | `reconstruction.py:537`; `proportions.py:45-59` |

### 3.2. Các điểm đổi đơn vị

- cm → mét để dựng lưới: `anny_body.py:101-102`.
- chu vi cm ↔ mét khi cắt lát:
  - `closed_torso_section()` trả `perimeter_cm` (`measurements.py:122`);
  - fit dùng `level * h` với `h = height_cm/100` (`measurements.py:227`, `235`, `271`);
  - hệ số ngang đổi ra mét: `width_cm / height_cm / 2 * h` (`measurements.py:263`) — rút gọn đúng bằng `width_cm / 200` mét.
- report dùng `h = height_cm / 100` (`report.py:74`) và nhân level chuẩn hoá với `h`.
- refit dùng `target["level"] * height_cm / 100` (`reconstruction.py:449`) và `height_cm / 100`
  cho `apply_rings` (`reconstruction.py:453`).
- fallback `deform_template`: chia `width_cm / height_cm` để chuẩn hoá (`reconstruction.py:336`),
  cuối cùng nhân `height_cm / 100` (`reconstruction.py:370`).

**Không phát hiện chỗ đổi đơn vị sai** trong chuỗi trên: đầu vào cm, lưới mét, chu vi cm,
các phép chia/nhân đều bù trừ đúng.

### 3.3. Hai điểm không phải lỗi đơn vị nhưng đáng lưu ý

1. **Hằng số mốc hông trong chế độ `upper_body`**: code dùng `0.805 - fractions*0.29`
   (`reconstruction.py:500`), trong khi mốc thật lấy từ lưới là vai `0.805`, hông `0.534`
   → khoảng `0.271` (`reconstruction.py:505-508`). Đây là **lệch hằng số mốc**, không phải cm/m;
   có thể làm vùng hông của template bị đặt hơi thấp.
2. **Chiều cao được áp bằng scale đều**, không qua phenotype `height`
   (`anny_body.py:101-102`). Vì vậy đầu/tay/chân cũng to lên theo chiều cao — là giả định dựng hình,
   không phải lỗi đơn vị.

---

## 4. Có vòng lặp "chỉnh → đo lại → chỉnh" không?

**Có, nhưng số vòng cố định, không dừng theo sai số.**

### 4.1. Vòng chính trong `fit_measurement_targets`

- Lặp **đúng 4 lần**: `for _ in range(4):` — `measurements.py:232`.
- Mỗi vòng:
  1. cắt lại mặt cắt hiện tại để đo `current` — `measurements.py:235`;
  2. tính hệ số `target/current` (và `aspect_corr` cho W/D) — `measurements.py:242-256`;
  3. dựng PCHIP scale theo chiều cao — `measurements.py:257-260`;
  4. ghi đè đỉnh — `measurements.py:261-268`.
- **Không có `break`/điều kiện hội tụ** trong vòng lặp.
- Sau khi hết 4 vòng mới đo lại và tính sai số — `measurements.py:269-274`.
- Điều kiện "đạt" chỉ dùng để **gắn nhãn**, không điều khiển vòng lặp:
  `fit_status = "matched" if max(errors) <= 1.5 else "approximate"` — `measurements.py:276`.
  Nếu vẫn > 1,5 cm, mô hình vẫn được xuất với nhãn `approximate`; không chỉnh tiếp.
- Nếu hệ số nằm ngoài `0.70–1.40`, code **ném lỗi** thay vì lặp — `measurements.py:243-244`.

### 4.2. Vòng phụ sau khi làm mượt

- `smooth_avatar()` chạy Laplacian 1 lượt rồi **gọi lại** `fit_measurement_targets()`
  — `reconstruction.py:377-397` (đặc biệt dòng `396`).
- Vì `fit_measurement_targets` lại lặp 4 vòng, một lần quét có **tối đa 4 + 4 = 8 lượt** chỉnh.
- `refit_avatar()` cũng gọi fit rồi smooth — `reconstruction.py:455-456` — nên cũng tối đa 8 lượt.

### 4.3. Chỗ không có vòng lặp

- `deform_template()` (fallback MakeHuman) chỉ nội suy PCHIP một lần — `reconstruction.py:324-374`.
- `proportions.apply_rings()` scale một lần — `proportions.py:78-104`.

---

## 5. Giới tính được truyền vào ở đâu và ảnh hưởng thế nào?

### 5.1. Đường đi

1. Form `sex` (`auto | female | male`) — `main.py:279`.
2. Lưu vào `Job.sex` — `main.py:321`.
3. Truyền vào worker — `main.py:325`.
4. `process(..., sex)` → `reconstruct(..., sex)` — `main.py:213`, `main.py:230`.
5. `reconstruct()` gọi `resolve_sex(sex, measurements, capture_mode)` — `reconstruction.py:509`.
6. `mesh_sex` được dùng:
   - `anny_body.build(mesh_sex, weight, muscle, height_cm)` — `reconstruction.py:521`;
   - fallback `deform_template(..., mesh_sex, ...)` — `reconstruction.py:524`;
   - ghi vào profile — `reconstruction.py:543-544`;
   - cảnh báo hiển thị — `reconstruction.py:589-592`.

### 5.2. Cách quyết định

`resolve_sex()` — `anatomy.py:48-81`:

- Nếu `sex` là `female`/`male`: dùng luôn, `source="user"` (`anatomy.py:55-56`).
- Nếu `auto`: chấm điểm theo tỷ lệ số đo:
  - `hip - chest` (`anatomy.py:64-65`),
  - `shoulder / hip` (`anatomy.py:66-68`),
  - `waist / hip` (`anatomy.py:69-71`),
  - khi không có hông hoặc `upper_body`: dùng `shoulder/chest`, `waist/chest` (`anatomy.py:73-79`).
- Điểm `>= 0` → female, ngược lại male; hòa điểm mặc định **female** (`anatomy.py:81`).

### 5.3. Ảnh hưởng thực tế

- **Chọn basis**: `anny_body._interp(sex, ...)` chỉ lấy các lưới có key giới tương ứng
  (`anny_body.py:64-69`). Basis nữ được nướng với `gender=0` + local changes ngực/mông/hông;
  basis nam với `gender=1` + V-shape/pectoral/shoulder muscle (`build_anny_bases.py:40-55`, `119`).
- **Fallback MakeHuman**: `shape_sex()` nhân hệ số ngang theo `_LATERAL` và (hiện đã tắt) volume
  (`anatomy.py:155-177`).
- **Số đo chính không đổi theo giới**: sau khi chọn lưới, `fit_measurement_targets()` vẫn ép
  ngực/eo/mông về đúng target (`reconstruction.py:538-539`). Giới chủ yếu đổi vai, độ sâu ngực,
  hông/đùi và phân bố mô, không đổi 3 chu vi báo cáo.
- **Refit**: `refit_avatar()` dùng `fitting["sex"]` đã lưu (`reconstruction.py:426`, `460`);
  `PATCH /api/scans/{id}/measurements` không có trường `sex`, nên **không đổi giới** sau khi quét.

---

## 6. Bảng phát hiện nhanh

| # | Phát hiện | Bằng chứng |
|---|---|---|
| 1 | Không dùng measure modifier nào | không có `measure-*` trong `backend/app`, `verification/scripts` |
| 2 | Chỉ dùng local changes Anny khi nướng basis | `build_anny_bases.py:40-55`, `120` |
| 3 | Macro dùng đủ 6 label nhưng phần lớn cố định 0.5 | `build_anny_bases.py:118-119` |
| 4 | Runtime chỉ nội suy basis, không gọi Anny | `anny_body.py:64-83`, `97-107` |
| 5 | Đơn vị: cm ở API/số đo, mét trong lưới/fit | `main.py:276`; `anny_body.py:101`; `measurements.py:220` |
| 6 | Không thấy đổi đơn vị sai | các điểm quy đổi ở mục 3.2 |
| 7 | Vòng lặp fit cố định 4 vòng, không dừng theo sai số | `measurements.py:232`, `276` |
| 8 | Smooth làm thêm 4 vòng nữa | `reconstruction.py:396` |
| 9 | Giới tính chỉ đổi lưới nền, không đổi 3 vòng chính | `reconstruction.py:509-538` |
| 10 | `upper_body` dùng hằng số hông `0.29` thay vì span thật `0.271` | `reconstruction.py:500` vs `505-508` |
