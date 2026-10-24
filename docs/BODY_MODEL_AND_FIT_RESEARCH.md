# Nghiên cứu: 2 ảnh webcam → mô hình 3D cơ thể → thử đồ + bản đồ nhiệt chật/rộng

> Trạng thái: **đã triển khai bước 1 (mô hình nền Anny, engine v6)**; phần thử đồ/heatmap còn là đề xuất.
> Ngày: 2026-10-21. Cập nhật triển khai: xem [`HANDOFF.md`](HANDOFF.md) §10.
> Phạm vi: thay lớp dựng hình 3D hiện tại (MakeHuman `hm08` + kéo giãn lát cắt) bằng một
> phương án có cơ sở hơn, và bổ sung năng lực thử đồ + heatmap độ vừa.
> Tài liệu liên quan: [`HANDOFF.md`](HANDOFF.md), [`ARCHITECTURE.md`](ARCHITECTURE.md),
> [`SCAN_QUALITY.md`](SCAN_QUALITY.md), [`ANTHROPOMETRIC_VALIDATION_PROTOCOL.md`](ANTHROPOMETRIC_VALIDATION_PROTOCOL.md).

---

## 0. Tóm tắt điều hành

| Câu hỏi | Kết luận |
|---|---|
| Có nên tiếp tục MakeHuman morph target? | **Không.** Đó vẫn là kéo giãn một hình nộm trung tính; không có shape space theo giới/trọng lượng/cơ, nên không thể ra cơ thể nam/nữ thuyết phục. |
| Thay bằng gì? | **Anny** (NAVER Labs Europe, Apache 2.0, dựa trên chính asset MakeHuman/MPFB2 CC0, 13.380 đỉnh, khác biệt hoá được, có tham số hình thái diễn giải được: giới, tuổi, cân nặng, cơ, chiều cao, tỉ lệ). |
| Vì sao không dùng SMPL-X / SAM 3D Body? | SMPL-X **phi thương mại**. SAM 3D Body + MHR tốt nhưng là mạng 840M tham số — máy hiện tại **không có GPU**, chạy CPU không khả thi cho web. MHR để dành làm tuỳ chọn khi có GPU/cloud. |
| Làm sao ra hình người dùng? | Giữ nguyên tầng đo hiện có, **tối ưu tham số Anny** để khớp số đo + biên dạng 2 ảnh (analysis-by-synthesis), không cần GPU. |
| Thử đồ thế nào? | **Không mô phỏng vải toàn bộ** ở giai đoạn đầu. Dựng "vỏ áo" tham số từ thông số may → tính **khoảng hở (clearance) từng đỉnh** giữa vỏ và cơ thể → tô màu = heatmap chật/rộng. |
| Có cần may đo thật / cloth sim? | Chỉ khi có bộ thông số may thật cho sản phẩm. 160 sản phẩm hiện chỉ có **bảng size theo số đo cơ thể**, chưa có số đo may (flat) → phải bổ sung dữ liệu, hoặc chấp nhận ước lượng có nhãn rõ. |
| Thời gian | ~6–9 tuần cho 1 dev: 1 tuần quick-win heatmap theo vùng, 3 tuần Anny, 2–3 tuần vỏ áo + clearance. |

> **Cập nhật sau khi đo thực tế**: Anny khởi tạo mất **~3 phút và ~1 GB RAM** trên CPU (chỉ lần đầu,
> sau đó cache còn ~0,6 s nhưng vẫn cần torch + warp-lang ~1 GB đĩa). Vì vậy bản triển khai **nướng
> sẵn 12 lưới nền** (giới × cân nặng × cơ) thành `backend/models/anny-bases.npz` 1,9 MB và chỉ nội
> suy ở runtime — backend không import torch. Đổi lại, không gian phenotype bị rời rạc hoá theo lưới;
> nếu sau này cần điều khiển mịn hơn (tuổi, tỉ lệ, ngực), tăng số điểm lưới hoặc chuyển sang runtime
> Anny khi có GPU/RAM dư.

---

## 1. Ràng buộc thực tế của dự án (đã kiểm chứng trong repo)

| Ràng buộc | Hiện trạng |
|---|---|
| Thiết bị | Backend chạy CPU; **không có `nvidia-smi`**, `.venv` **không cài torch**. Mọi phương án nơ-ron nặng phải tính đến CPU hoặc GPU ngoài. |
| Đầu vào | 2 ảnh webcam (chính diện + nghiêng 90°), MediaPipe Pose + Segmentation. Không có ảnh lưng, không có đa góc. |
| Tầng đo | 3 tầng hiện có (`estimate_upper_body_height` → `camera_fusion` → `ANATOMICAL_SECTION_FACTORS` + `fit_measurement_targets`) đang cho `fit_status = matched`, sai số 0.00 cm. **Không được phá.** |
| Dựng hình | `deform_template()` kéo giãn lưới `backend/models/body-template.obj` theo profile ngang; khác biệt nam/nữ hiện chỉ nằm ở hệ số ngang. |
| Dữ liệu sản phẩm | `size_charts` là **khoảng số đo cơ thể** (`measurement_basis = body_cm`), ví dụ size M ngực 90–98 cm. **Không có** số đo may (dài áo, rộng vai may, dài tay, vòng ngực áo…). |
| Giấy phép | Sản phẩm hướng thương mại → chỉ dùng thư viện Apache/MIT/CC0/BSD. |
| Trung thực | Không được tuyên bố độ chính xác lâm sàng, `uncertainty_cm` vẫn `None`, mọi con số phải có nguồn. |

---

## 2. Tách bài toán thành 3 lớp độc lập

```
(A) HÌNH HỌC CƠ THỂ        (B) HÌNH HỌC TRANG PHỤC        (C) ÁNH XẠ ĐỘ VỪA
2 ảnh + số đo  ──────►  mesh cơ thể  ──────►  vỏ áo/quần  ──────►  trường khoảng hở
   (Anny)                 (13k đỉnh)            (tham số may)         → heatmap + size
```

Điểm mấu chốt: **(C) không phụ thuộc (A) làm bằng gì**. Có thể làm heatmap theo vùng ngay trên
mô hình hiện tại trước khi thay (A), và vẫn giữ nguyên khi thay (A) sau. Đây là cách chia để
giảm rủi ro và có kết quả nhìn thấy sớm.

---

## 3. Lớp A — lấy hình học cơ thể

### 3.1. So sánh phương án

| Phương án | Giấy phép | Chạy CPU? | Chất lượng hình thái | Công sức | Kết luận |
|---|---|---|---|---|---|
| **Hiện tại**: MakeHuman `hm08` + kéo lát cắt | CC0 | ✅ | Kém: hình nộm, không ngực/mông/cơ, nam/nữ chỉ khác hệ số ngang | 0 | Giữ làm fallback |
| **Anny** (NAVER, 2025–2026) | Code **Apache 2.0**, asset MPFB2 **CC0** | ✅ PyTorch CPU (cần `torch>=2.0`, `warp-lang`, Python ≥ 3.10) | Tốt: shape space diễn giải được (giới, tuổi, cân nặng, cơ, chiều cao, tỉ lệ), hiệu chỉnh theo WHO; fit scan thật 2,4 mm | 2–3 tuần | ⭐ **Chọn** |
| **MHR** (Meta, 2025) | **Apache 2.0** (code + asset) | ✅ (LOD 1, `pymomentum-cpu`) | Rất tốt: 45 tham số identity, LOD 0–6 | 2–3 tuần | Dự phòng; ít diễn giải hơn Anny |
| **SAM 3D Body** (Meta, 2025) | **SAM License** (miễn phí, không phải open-source, có điều kiện) | ❌ thực tế cần GPU (DINOv3-H 840M) | SOTA ảnh đơn | 3–4 tuần + GPU | Chỉ khi có GPU/cloud |
| **Multi-HMR + checkpoint Anny** | Checkpoint có license riêng — **phải kiểm tra trước khi thương mại** | ❌ ViT-L, chậm trên CPU | Tốt, ra trực tiếp tham số Anny | 3–4 tuần | Không dùng lúc này |
| **SMPL-X** | **Phi thương mại** | ✅ | Rất tốt | — | ❌ Loại vì giấy phép |
| **Carve silhouette 2 ảnh** (không template) | — | ✅ | Kém: 2 góc không đủ, mất lõm, dính tay–thân | 1–2 tuần | ❌ Không dùng một mình |
| **Thuê API** (3DLOOK, Bold Metrics, Meshcapade) | Thương mại, dữ liệu người dùng ra ngoài | — | Tốt | thấp | ❌ Trái định hướng local |

### 3.2. Vì sao Anny

1. **Cùng gốc MakeHuman**: lưới nền 13.380 đỉnh / 13.378 mặt tứ giác (topology `anny` mặc định
   được tam giác hoá và bỏ đỉnh rời). Cùng họ topology đang dùng nên logic cắt lát, vòng đo,
   `report.py` giữ nguyên; mốc khớp (vai/hông/cổ) lấy từ **rig** thay vì nhóm `g joint-*` trong
   file OBJ hiện tại.
2. **Có shape space thật**: phenotype trong [0,1] điều khiển blendshape dựng sẵn (giới, tuổi,
   cân nặng, cơ, chiều cao, tỉ lệ, cùng các thay đổi cục bộ như bụng, ngực). Đây chính là thứ
   `shape_sex()` đang cố mô phỏng bằng tay và thất bại.
3. **Khác biệt hoá được** → có thể *tối ưu ngược* từ số đo, không cần train.
4. **Giấy phép sạch**: Apache 2.0 + CC0. Lưu ý: **không dùng topology `smplx`** của Anny
   (phần đó phi thương mại).
5. **Không cần GPU**: sinh lưới chỉ là vài phép biến đổi blend shape trên 13k đỉnh (CPU); thời
   gian thực tế cần đo lại khi tích hợp.

Nhược điểm phải chấp nhận:
- Vẫn là mô hình tham số, **không phải bản sao chính xác** cơ thể người dùng; sai khác hình học
  cục bộ (nếp gấp, bất đối xứng, mỡ từng vùng) không biểu diễn được.
- Lần đầu khởi tạo phải parse asset và cache (vài phút) → phải build cache lúc cài đặt, không
  phải lúc người dùng bấm quét. Đặt `ANNY_CACHE_DIR` trong `backend/` và gitignore.
- Thêm phụ thuộc nặng vào backend: `torch>=2.0` + `warp-lang` (pip tự kéo theo), tải hàng trăm
  MB và chiếm khoảng 1 GB đĩa; cần đo lại thời gian import/khởi động.

### 3.3. Cách fit Anny vào dữ liệu hiện có (không cần GPU)

Giữ nguyên tầng đo; chỉ thay bước dựng lưới:

```
đo hiện có (chest/waist/hip/shoulder/height + W/D từ silhouette)
        │
        ▼
khởi tạo phenotype: gender ← lựa chọn/auto, height ← height_cm,
                    weight/muscle ← BMI ước lượng từ chu vi
        │
        ▼
lặp (scipy least_squares / Adam, 100–300 vòng):
   sinh lưới Anny (CPU, pose A-pose cố định)
   tính chu vi ngực/eo/hông bằng đúng hàm cắt lát đang dùng
   tính bề rộng vai, chiều cao, tỉ lệ W/D từ silhouette
   loss = Σ wᵢ · ((giá trị_mesh − giá_trị_đo)/giá_trị_đo)²  + λ‖θ−θ₀‖²
        │
        ▼
lưới cuối → chuẩn hoá chiều cao, đặt bàn chân y=0 → xuất GLB
```

- **Ràng buộc cứng**: chiều cao sai ≤ 1,5 cm; chu vi ngực/eo/hông sai ≤ 1,0 cm; chân ở `y=0`.
- **Pose cố định** (A-pose) để không phải giải bài toán pose từ 2 ảnh; chỉ giải hình thái.
- **Bất định**: báo cáo khoảng tin cậy theo độ nhạy của loss với từng tham số; vẫn giữ
  `uncertainty_cm = None` cho tới khi có validate thật.
- Thời gian mục tiêu trên CPU: **< 3 s/lần dựng** (hiện tại 2,99 s) — đo lại sau khi tích hợp;
  nếu vượt, cache lưới theo bộ số đo.

**Vì sao tối ưu thay vì hồi quy học sâu**: với 2 ảnh và CPU, analysis-by-synthesis cho kết quả
sát số đo hơn (ta tối ưu trực tiếp đại lượng cần đúng), không cần tải checkpoint lớn, không
phụ thuộc license checkpoint.

### 3.4. "Không dùng mô hình tham số" — các phương án phi mô hình và vì sao chưa chọn

| Phương án | Cần gì | Vấn đề với dự án |
|---|---|---|
| **Photogrammetry / multi-view stereo** (chụp 20–40 ảnh hoặc video vòng quanh) | Người dùng đi vòng quanh, ánh sáng đều, nền trơn; GPU để tái tạo | Đổi hoàn toàn trải nghiệm webcam 2 ảnh; lưới ra không watertight, không landmark, không topology thống nhất → cloth sim và đo chu vi đều khó |
| **Monocular depth + fusion** (Depth Anything / MoGe trên 2 ảnh) | Model depth (CPU chậm), cân chỉnh tỉ lệ | 2 ảnh vẫn thiếu mặt sau; depth sai ở tay–thân; bề mặt nhiễu, cần lưới hoá lại |
| **Generative 3D từ 1 ảnh** (image-to-3D) | GPU, model lớn | Sinh hình "giống" chứ không đúng số đo; không đảm bảo nhân trắc học; license phức tạp |
| **Gaussian splatting / NeRF** | Video nhiều góc + GPU | Chỉ để hiển thị, không có bề mặt để đo hay mặc áo; không phù hợp mục tiêu fit |
| **Máy quét 3D chuyên dụng** (Size Stream, Fit3D…) | Phần cứng, địa điểm | Ngoài phạm vi web |

Điểm cần phân biệt: vấn đề không phải "dùng lưới", mà là **dùng lưới nào**. Thử đồ + đo chu vi +
heatmap đều cần: topology nhất quán, landmark giải phẫu, lưới kín, đơn vị thật. Một scan thô từ
2 ảnh không cho bất kỳ thứ nào trong số đó. Vì vậy hướng đúng là **mô hình tham số có shape space
tốt** (Anny), không phải bỏ mô hình tham số.

Nếu sau này muốn tiến gần "bản sao chính xác", lộ trình hợp lý là: giữ Anny làm **prior**, rồi
tinh chỉnh cục bộ bằng silhouette + depth từ video nhiều góc (khi có GPU) — tức là
"template + scan refinement", không phải scan thuần.

---

## 4. Lớp B — hình học trang phục

### 4.1. Bốn phương án

| # | Cách làm | Cần gì | Chất lượng thị giác | Heatmap | Công sức |
|---|---|---|---|---|---|
| 1 | **Ease theo vùng**, không có lưới áo | Bảng size hiện có + quy ước ease theo `fit` | Không có (chỉ tô màu trên cơ thể) | Theo vùng, thô | 1 tuần |
| 2 | **Vỏ áo tham số** (offset surface) từ cơ thể + thông số may | Thêm số đo may cho sản phẩm | Trung bình: giống mannequin mặc áo ôm, không nếp gấp | Từng đỉnh, tốt | 2–3 tuần |
| 3 | **Pattern + cloth sim** (GarmentCode, MIT) | Pattern thật + solver (Warp/Newton, GPU) | Cao | Từng đỉnh + lực căng | 6–10 tuần, nặng |
| 4 | **2D diffusion try-on** (IDM-VTON, OOTDiffusion, FitDiT…) | GPU + ảnh sản phẩm sạch | Rất cao (ảnh thật) | Không có | 2–3 tuần + GPU |

### 4.2. Khuyến nghị: **1 → 2**, tuỳ chọn 4

- **Bước 1 (quick win)**: dùng bảng size hiện có. Mỗi size là một khoảng số đo cơ thể; hiệu số
  giữa cận của khoảng và số đo người dùng cho biết người dùng nằm ở đâu trong size (sát cận dưới
  = chật, cận trên = rộng). Cộng với nhãn `fit` (slim/regular/oversized) và `material`
  (có elastane/spandex hay không) để suy ra **ease ước lượng theo vùng**. Tô màu dải trên mô
  hình, kèm nhãn "ước lượng từ bảng size, chưa phải số đo may".
- **Bước 2**: thêm bảng `garment_specs` (số đo may) cho từng sản phẩm × size (vòng ngực áo, dài
  áo, rộng vai may, dài tay, vòng eo quần, vòng mông quần, dài ống, inseam). Từ đó dựng vỏ áo:
  - Lấy vùng cơ thể bị áo che (theo chiều cao + mặt cắt).
  - Với mỗi vòng ngang, bán kính vỏ = bán kính cơ thể + ease(vùng) (ease lấy từ số đo may, chia
    đều theo góc, có trọng số trước/sau để mô phỏng áo rộng phía trước hoặc sau).
  - Nối các vòng thành lưới tam giác, bo gấu/cổ/tay.
  - Không mô phỏng rơi vải; đây là "áo căng trên cơ thể", đúng bản chất bài toán độ vừa.
- **Bước 4 (tuỳ chọn)**: chỉ để "nhìn đẹp", chạy ngoài luồng, không dùng cho kết luận fit.

### 4.3. Vì sao không làm cloth sim ngay

- Không có pattern thật của 160 sản phẩm; pattern hoá từ ảnh là bài toán riêng.
- Solver cần GPU hoặc rất chậm trên CPU; mỗi lần đổi size phải mô phỏng lại.
- Kết quả sim phụ thuộc thông số vải (khối lượng, độ cứng, ma sát) mà catalog không có.
- Giá trị cho người dùng chủ yếu là **chật ở đâu**, không phải nếp gấp đẹp.

---

## 5. Lớp C — định nghĩa heatmap chật/rộng

### 5.1. Trường khoảng hở (clearance field)

Với lưới cơ thể `B` và lưới vỏ áo `G`:

```
e(v) = signed_distance(v, G)      với mọi đỉnh v của B (dương = ngoài áo)
```

- `e < 0` → cơ thể xuyên qua áo: **không mặc được** (đỏ đậm).
- Dùng `trimesh.proximity.signed_distance` (KD-tree) — 13k đỉnh, CPU, ~0,1 s.

### 5.2. Quy đổi theo vùng (bắt buộc hiển thị kèm)

Ngoài màu từng đỉnh, mỗi vùng sinh một dòng số:

| Vùng | Công thức | Ý nghĩa |
|---|---|---|
| Ngực | `(C_áo − C_cơ thể) / C_cơ thể` | % dư vải; âm = cần giãn |
| Eo | như trên | |
| Hông | như trên | |
| Bắp tay | chu vi ống tay vs chu vi tay | |
| Đùi | chu vi ống quần vs chu vi đùi | |
| Dài | dài áo may − (chiều cao cơ thể × tỉ lệ mong muốn) | cảnh báo dài/ngắn |

### 5.3. Ngưỡng màu (đề xuất ban đầu, sẽ hiệu chỉnh)

| Khoảng hở | Màu | Nhãn |
|---|---|---|
| `e < 0` | đỏ đậm | Không mặc được |
| `0 – 1 cm` | đỏ | Chật |
| `1 – 3 cm` | cam | Sát |
| `3 – 6 cm` | xanh lá | Vừa |
| `> 6 cm` | xanh dương | Rộng |

Ngưỡng phải khác nhau cho áo thun dệt kim (co giãn 15–25%) và sơ mi dệt thoi (co giãn ~0–2%).
Chất liệu đọc từ trường `material` của sản phẩm: có `spandex/elastane` → nới ngưỡng chật.

### 5.4. Trung thực

- Heatmap là **ước lượng hình học**, không phải cảm giác mặc thật (vải, đường may, cơ thể chuyển
  động đều không mô phỏng).
- Nếu chưa có số đo may thật: gắn nhãn rõ "ước lượng từ bảng size" và không hiển thị chữ số cm
  cho người dùng, chỉ hiển thị mức (chật/vừa/rộng).
- Không dùng heatmap để khẳng định "chắc chắn vừa".

---

## 6. Kiến trúc đề xuất

```
backend/app/
  body_model/            # mới
    anny_adapter.py      # sinh lưới từ phenotype, cache, xuất GLB
    fit_shape.py         # tối ưu phenotype theo số đo + silhouette
  garment/
    specs.py             # schema số đo may (per product × size)
    shell.py             # dựng vỏ áo từ cơ thể + specs
    clearance.py         # signed distance, gộp vùng, phân loại
    router.py            # GET /products/{slug}/fit?size=M&scan_id=...
  main.py                # thêm endpoint, giữ nguyên /scan
frontend/
  components/shop/FitMap.tsx      # lưới màu + legend + tooltip vùng
  components/shop/GarmentPreview.tsx  # vỏ áo bán trong suốt
```

- **Không đụng** `measurements.py`, `camera_fusion.py`, `report.py` ở giai đoạn 1–2.
- Dữ liệu: bảng `garment_specs(product_id, size, key, value_cm, source)`; `source` theo đúng
  quy ước hiện có (`user_input | photo_estimate | template_model | unavailable`).
- API mới trả về: `ease_by_region`, `verdict` (tight/fitted/regular/loose), `mesh_ref` (GLB vỏ áo),
  `warnings[]`, `confidence: "estimated" | "measured"`.

---

## 7. Lộ trình

| Giai đoạn | Nội dung | Thời lượng | Nghiệm thu |
|---|---|---|---|
| **GĐ0** (1 tuần) | Ease theo vùng từ bảng size; heatmap dải màu trên mô hình hiện tại; nhãn "ước lượng" | 1 tuần | Bấm size M trên 5 sản phẩm → thấy vùng chật/rộng + giải thích; không đổi số đo |
| **GĐ1** (2–3 tuần) | Tích hợp Anny: adapter + fit phenotype; thay `deform_template`; giữ nguyên báo cáo/vòng đo | 2–3 tuần | Cùng bộ số đo → lưới nam/nữ khác nhau rõ; fit_status vẫn `matched`; < 3 s |
| **GĐ2** (2–3 tuần) | Vỏ áo tham số + clearance từng đỉnh + UI thử đồ | 2–3 tuần | 10 sản phẩm có specs; heatmap khớp trực giác; có legend |
| **GĐ3** (tuỳ chọn) | 2D try-on hoặc cloth sim | 2–4 tuần | Chỉ khi có GPU/pattern |

> **Đã xong GĐ0 (21/10/2026)**: ease theo vùng từ bảng size + tô màu 3D (`POST /api/fit-map`,
> `FitMapPanel`, `BodyViewer.fitBands`). Xem [`HANDOFF.md`](HANDOFF.md) §11.

**Rủi ro chính**

| Rủi ro | Giảm thiểu |
|---|---|
| Anny/PyTorch làm nặng backend, khởi tạo chậm | Cache asset lúc cài; lazy import; giữ MakeHuman làm fallback |
| Fit không hội tụ với số đo mâu thuẫn | Loss có trọng số + regularisation; báo cáo phần dư thay vì ép |
| Không có số đo may → heatmap vô nghĩa | GĐ0 chỉ hiển thị mức, không hiển thị cm; ưu tiên nhập specs cho 10 sản phẩm chủ lực |
| Người dùng hiểu nhầm là đo chính xác | Nhãn nguồn + cảnh báo cố định trong UI |

---

## 8. Việc **không** nên làm

- Dùng SMPL/SMPL-X cho sản phẩm thương mại.
- Hứa "mô phỏng chính xác" khi chưa có số đo may và chưa validate.
- Cloth sim cho 160 sản phẩm khi chưa có pattern.
- Tăng số đo giả để heatmap "đẹp" hơn.

---

## 9. Tài liệu tham khảo

- Anny — code/giấy phép: <https://github.com/naver/anny>; bài báo: <https://arxiv.org/abs/2511.03589>
- MHR (Apache 2.0): <https://github.com/facebookresearch/mhr>
- SAM 3D Body (SAM License): <https://github.com/facebookresearch/sam-3d-body>
- GarmentCode (MIT): <https://github.com/maria-korosteleva/GarmentCode>
- EASE — điều khiển ease cục bộ trên bề mặt cơ thể, đánh giá fit bằng khoảng hở: <https://www.sciencedirect.com/science/article/abs/pii/S0097849326001159>
- Đo khoảng cách có dấu garment–avatar: <https://arxiv.org/html/2102.05462v1>
- SMPL-Anthropometry (tham khảo cách đo chu vi trên lưới): <https://github.com/DavidBoja/SMPL-Anthropometry>
- Bối cảnh thương mại (số liệu do nhà cung cấp công bố, cần thận trọng): <https://www.size.ly/blog/virtual-fitting-rooms-for-ecommerce>
