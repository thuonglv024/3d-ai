# K3 — Chẩn đoán gập ghềnh trên mesh dựng theo pipeline hiện tại

> Thí nghiệm độc lập trong `tools/diag/`, không sửa code gốc.
> Script: [`build_and_scan.py`](../../tools/diag/build_and_scan.py), [`analyze.py`](../../tools/diag/analyze.py), [`ablate.py`](../../tools/diag/ablate.py).
> Kết quả: `tools/diag/out/` (3 GLB, CSV mặt cắt, JSON đạo hàm bậc hai, `summary.json`, `ablation.json`).

## 0. Cách làm

- Dựng 3 mesh bằng đúng chuỗi hàm production dùng khi refit:
  `anny_body.build()` → `proportions.ring_scales()` + `apply_rings()` →
  `fit_measurement_targets()` → `smooth_avatar()` → GLB.
  Vào qua `refit_avatar()` — `backend/app/reconstruction.py:400-475`.
- Mỗi mesh: cắt mặt phẳng ngang mỗi **2 cm** từ gót tới đầu; tại mỗi độ cao lấy **tổng chu vi
  tất cả vòng kín** (cm) và **số vòng** (`tools/diag/build_and_scan.py::cross_section`).
- Đạo hàm bậc hai rời rạc: `d2 = P[i+1] − 2P[i] + P[i−1]` (cm trên bình phương bước 2 cm),
  chỉ tính khi 3 lát liên tiếp có cùng số vòng (tránh nhảy do chân/tay tách–nhập).
- Quy đổi `z/H` để so giữa 3 chiều cao; cửa sổ ±3 cm quanh từng mốc pipeline.
- Lưu ý: “chu vi” ở đây là **tổng mọi vòng kín**, không phải `closed_torso_section()` (vòng lớn
  nhất) mà pipeline dùng để fit. Số vòng được ghi lại để bỏ qua các lát có topology đổi
  (chân/tay tách–nhập), vì các bước nhảy đó là giải phẫu chứ không phải bề mặt gập ghềnh.

## 1. Ba bộ số đo và kết quả fit

| Case | Giới | H (cm) | Ngực / Eo / Mông (cm) | weight/muscle prior | Fit |
|---|---|---:|---|---|---|
| `a_male_average` | nam | 175 | 96 / 82 / 98 | 0.50 / 0.45 | `matched`, 0.00 cm |
| `b_female_slim` | nữ | 162 | 80 / 64 / 88 | 0.30 / 0.35 | `matched`, 0.00 cm |
| `c_male_obese` | nam | 172 | 120 / 110 / 118 | 0.70 / 0.45 | `matched`, 0.00 cm |

Mesh: `tools/diag/out/{case}.glb`; profile: `{case}.profile.json`.
Lưu ý: case béo dùng eo 110 thay vì 115 vì 115 vượt giới hạn scale `1.40` của
`fit_measurement_targets` (`backend/app/measurements.py:243-244`) và pipeline từ chối dựng.

## 2. Đỉnh gập ghềnh lớn nhất (top 6 mỗi case)

`P` = chu vi lát cắt (cm); `d2` = đạo hàm bậc hai (cm); `%` = `|d2|/P`.

| Case | z (cm) | z/H | P | d2 | % | Vùng |
|---|---:|---:|---:|---:|---:|---|
| a | 4 | 0.023 | 89.3 | **+47.08** | 52.8 | bàn chân |
| a | 150 | 0.857 | 36.2 | **+14.78** | 40.8 | cổ/vai |
| a | 84 | 0.480 | 102.5 | +10.19 | 9.9 | hông |
| a | 172 | 0.983 | 45.1 | −8.75 | 19.4 | đầu |
| a | 144 | 0.823 | 83.5 | −8.40 | 10.1 | vai |
| a | 148 | 0.846 | 43.7 | +8.36 | 19.1 | cổ |
| b | 4 | 0.025 | 89.3 | **+56.80** | 63.6 | bàn chân |
| b | 138 | 0.852 | 36.8 | **+31.19** | 84.7 | cổ |
| b | 126 | 0.778 | 116.5 | +15.84 | 13.6 | ngực trên/vai |
| b | 90 | 0.556 | 104.8 | +14.58 | 13.9 | hông (7 vòng) |
| b | 136 | 0.840 | 70.0 | −13.77 | 19.7 | vai–cổ |
| b | 134 | 0.827 | 89.5 | −9.63 | 10.8 | vai |
| c | 4 | 0.023 | 87.3 | **+45.57** | 52.2 | bàn chân |
| c | 100 | 0.581 | 186.0 | **−27.58** | 14.8 | eo (3 vòng) |
| c | 144 | 0.837 | 59.0 | +8.11 | 13.7 | cổ |
| c | 6 | 0.035 | 68.0 | +7.72 | 11.4 | bàn chân |
| c | 146 | 0.849 | 45.0 | +7.60 | 16.9 | cổ |
| c | 102 | 0.593 | 168.5 | +7.39 | 4.4 | eo |

## 3. Mức gập theo vùng (max |d2| trong vùng, cm)

| Vùng (z/H) | a nam TB | b nữ gầy | c nam béo |
|---|---:|---:|---:|
| bàn chân (0–0.06) | 47.08 | 56.80 | 45.57 |
| chân (0.06–0.40) | 2.19 | 5.64 | 1.95 |
| hông/đùi (0.40–0.56) | 10.19 | 14.58 | 4.01 |
| eo (0.56–0.66) | 8.12 | 6.81 | **27.58** |
| ngực (0.66–0.80) | 5.17 | **15.84** | 5.48 |
| vai/cổ (0.80–0.88) | 14.78 | **31.19** | 8.11 |
| đầu (0.88–1.0) | 8.75 | 5.39 | 5.40 |

Trung vị `|d2|` toàn thân: a = 1.14 cm, b = 0.93 cm, c = 1.01 cm.

## 4. Đối chiếu với mốc của từng bước pipeline

Giá trị là `max |d2|` trong ±3 cm quanh mốc; ngoặc là tỷ lệ so với trung vị.

| Mốc (z/H) | Bước liên quan | a | b | c |
|---|---|---:|---:|---:|
| 0.50 — hông | `fit_measurement_targets` | 1.85 (1.6×) | 2.19 (2.4×) | 2.05 (2.0×) |
| 0.60 — eo | `fit_measurement_targets` | 8.12 (7.1×) | 6.81 (7.3×) | 7.39 (7.3×) |
| 0.72 — ngực | `fit_measurement_targets` | 3.61 (3.2×) | 3.08 (3.3×) | 5.48 (5.4×) |
| 0.805 — vai | Anny local change | 5.08 (4.5×) | 3.90 (4.2×) | 4.68 (4.6×) |
| 0.855 — cổ | `proportions` ring | **14.78 (13×)** | **31.19 (33×)** | 7.60 (7.5×) |
| 0.955 — đầu | lát cắt báo cáo | 4.16 (3.7×) | 2.77 (3.0×) | 3.02 (3.0×) |
| 0.405 — đùi | `proportions` ring | 0.31 (0.3×) | 0.65 (0.7×) | 1.01 (1.0×) |
| 0.235 — bắp chân | `proportions` ring | 1.55 (1.4×) | 0.71 (0.8×) | 1.17 (1.2×) |
| 0.065 — cổ chân | `proportions` ring | 3.75 (3.3×) | 7.32 (7.9×) | 3.56 (3.5×) |

## 5. Ablation: bump đến từ đâu? (case nam trung bình)

Dựng thêm 3 biến thể: base Anny, base + proportions, base + proportions + fit; so với full
(smooth + refit). Cùng thang đo:

| Mốc | base | +proportions | +fit | full (smooth+refit) |
|---|---:|---:|---:|---:|
| hông 0.50 | 1.77 | 1.77 | 2.13 | 1.85 |
| eo 0.60 | **8.58** | **8.58** | 8.46 | 8.12 |
| ngực 0.72 | 3.23 | 3.23 | 3.68 | 3.61 |
| vai 0.805 | 5.62 | 5.06 | 4.88 | 5.08 |
| cổ 0.855 | 8.57 | 8.53 | 8.56 | **14.78** |
| đầu 0.955 | 4.21 | 4.21 | 4.21 | 4.16 |
| đùi 0.405 | 0.13 | 0.64 | 0.31 | 0.31 |
| bắp chân 0.235 | 1.63 | 1.86 | 1.86 | 1.55 |
| cổ chân 0.065 | 3.77 | 3.83 | 3.83 | 3.75 |

## 6. Kết luận

1. **Gập lớn nhất là bàn chân** (`z ≈ 4–8 cm`, `d2` 45–57 cm, 52–64%): do hình học bàn chân và
   việc hai bàn chân tách thành 2 vòng, **không liên quan modifier** nào.
2. **Eo (0.56–0.66 H)**: có đỉnh ở cả 3 case, mạnh nhất ở nam béo (`27.6 cm` tại `0.581 H`).
   Ablation nam trung bình cho thấy **đỉnh đã có trong lưới nền Anny** (8.58 cm), fit không tạo thêm
   (8.46 cm). Vậy đây chủ yếu là hình dáng eo của base; với nam béo, mục tiêu eo +36% so với base
   có thể làm đỉnh mạnh hơn, nhưng chưa tách được hoàn toàn nếu không ablation case béo.
3. **Cổ/vai (0.82–0.86 H)**: nữ gầy có đỉnh rất lớn (`31.2 cm`, 85% P). Ablation cho thấy
   base 8.57 → proportions 8.53 → fit 8.56, nhưng **full 14.78**: bước **smooth_avatar
   (Laplacian + refit)** làm đỉnh cổ tăng gần gấp đôi. Đây là tương quan rõ nhất với một bước
   pipeline, không phải với `proportions`.
4. **Ngực (0.70–0.78 H)**: đỉnh nhỏ ở nam (`3–5 cm`), lớn hơn ở nữ gầy (`15.8 cm` tại `0.778 H`);
   base đã có 3.23, fit thêm ~0.45 → chủ yếu là hình dáng ngực/vai của base và local changes
   (`breast-*`, `pectoral`), không phải fit.
5. **Hông (0.48–0.56 H)**: đỉnh 2–15 cm; nữ gầy có `14.6 cm` tại `0.556 H` với 7 vòng
   (tay/thân tạo nhiều vòng), nên một phần là topology tay–thân chứ không phải bề mặt hông.
6. **Band `proportions` ở đùi/bắp chân không tạo bậc rõ**: `d2` ≤ 1.9 cm, ≤ 1.4× trung vị.
   Cổ chân có 3.5–7.3 cm nhưng nằm sát bàn chân nên bị nhiễu topology, không kết luận từ band.
7. **Đầu (0.955 H)** có đỉnh 3–5 cm do hình khối sọ/mặt của base, không phải modifier.

**Tương quan modifier:**

- `fit_measurement_targets` (mốc 0.50/0.60/0.72) **trùng vị trí** với các đỉnh eo/ngực/hông,
  nhưng ablation cho thấy đóng góp của fit nhỏ so với base (trừ khi target lệch mạnh như case béo).
- `proportions.apply_rings` (0.855/0.405/0.235/0.065) chỉ tạo thay đổi nhỏ ở đùi/bắp chân/cổ chân;
  không phải nguyên nhân đỉnh cổ.
- `smooth_avatar` là bước duy nhất làm đỉnh cổ tăng mạnh (8.6 → 14.8 cm) ở case nam trung bình.
- Local changes của Anny (ngực/mông/vai) đã nằm trong base, nên mọi đỉnh ở eo/ngực/đầu/bàn chân
  vẫn còn khi chỉ đo base.

## 7. File sinh ra

| File | Nội dung |
|---|---|
| `tools/diag/out/a_male_average.glb`, `b_female_slim.glb`, `c_male_obese.glb` | 3 mesh pipeline hiện tại |
| `tools/diag/out/*_sections.csv` | chu vi + số vòng từng 2 cm |
| `tools/diag/out/*_d2.json` | `d2`, `%`, số vòng từng lát |
| `tools/diag/out/summary.json` | top đỉnh mỗi case |
| `tools/diag/out/ablation.json` | so base/+prop/+fit/full |
