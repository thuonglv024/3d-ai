# BUG_3D_nav — “Chuyển sang mô hình 3D” nhảy về đầu

Chỉ chẩn đoán, không sửa code production, không commit. Nhánh hiện tại: `fix/step8` (commit `7415637`).

## 1. Các nút/handler liên quan tới “chuyển sang 3D”

| Nút | onClick/đích | Chuỗi |
|---|---|---|
| AiScanResult `Dựng mô hình 3D từ hai ảnh này` | `onBuild3D` | `FitExperience.tsx:235` → `s.scan(pair)` → `POST /api/scans` → poll → `ScanResult` (inline, không route) |
| AiScanResult `Quét 3D bằng camera` | `onSwitchTo3D` | `FitExperience.tsx:230` chỉ đổi `scanMode` về classic (đúng thiết kế) |
| Saved scan `Mở phòng thử 3D độc lập` | `<Link href="/scan">` | `account/body-profile/scans/[id]/page.tsx:384` → mở `/scan` (màn hình quét mới, không mang model) |
| Saved scan `Thử áp dụng số đo…` | `handleApplyScanToShopping` | `page.tsx:59-63` → `applySavedScanToSession` rồi `router.push("/#catalog")` → **trang chủ** |
| Home `Xem lại mô hình 3D của bạn` | `openScanForProduct` | `StorefrontHome.tsx:280-283` mở modal, không route |

## 2. Mọi chỗ có thể quay về “đầu”

- `router.push("/#catalog")` — `account/body-profile/scans/[id]/page.tsx:62` (apply số đo, **cố ý** về home).
- `Link href="/scan"` — `scans/[id]/page.tsx:384`: `/scan` luôn khởi tạo `FitExperience` rỗng, không có job → màn hình quét ban đầu (giống “về đầu”).
- **Không có route `failed`**: `FitExperience` chỉ có nhánh `ai.result` (218), `completed` (281), `busy` (303). Job `failed` rơi xuống **form quét ban đầu**.

## 3. Nghi vấn chính (file:dòng)

1. `frontend/components/shop/FitExperience.tsx:240-245`
```tsx
const ok = await s.scan(pair);
if (!ok) return;
ai.reset(); resetAiUpload(); setScanMode("classic");
```
→ chỉ kiểm tra POST thành công (202), không chờ job `completed`.

2. `frontend/lib/useBodyScan.ts:144-154`
```tsx
const r = await fetch("/api/scans", ...); // 202
...
setJob(data); return true;
```
→ `true` ngay khi backend **nhận** ảnh, chưa biết dựng hình có fail không.

3. `frontend/lib/useBodyScan.ts:97`
```tsx
if (data.status === "failed") setError(data.error || "Chưa dựng được hình...");
```
→ job `failed` được giữ, nhưng `FitExperience` không render nhánh failed.

4. `frontend/components/shop/FitExperience.tsx:281,303` — chỉ có `completed`/`busy`; không có `currentJob.status === "failed"`.

5. `frontend/lib/ScanContext.tsx:215-220` — poll 404 (backend restart) `setJobState(null)` + `jobError`; cũng rơi về form đầu.

→ Điều kiện kích hoạt: **POST thành công nhưng reconstruction thất bại** (hoặc backend restart giữa chừng). Người dùng thấy AI số đo biến mất, quay lại màn hình quét ban đầu.

## 4. Route màn hình 3D

Không có route riêng (`frontend/app`: chỉ `scan`, `products`, `account`, `orders`, ...). Màn hình 3D là `ScanResult` **inline** trong `FitExperience`. Do đó “đi tới màn hình 3D” phải giữ modal/job chứ không navigate. `/scan` không nhận `?scanId=`.

## 5. Backend endpoint dựng 3D

`tools/diag/check_3d_flow.py` (v7): `POST /api/scans` **202, 0.04s** → poll `completed` **1.13s** → `GET /api/scans/{id}/model` **200, 714.380 bytes, glTF**. Response đủ field so với `Job` TS (`useBodyScan.ts:38`): không thiếu field.
- **v7** = engine đang chạy.
- **v6**: `git log -S 'mediapipe-two-photo-fit-v6'` **không có commit**; `report.py:12` vẫn ghi v6 nhưng bị `reconstruction.py:32` ghi đè thành v7. Không thể runtime-test v6 trong repo hiện tại.

## 6. Log tạm (script chẩn đoán, không vào production)

- `tools/diag/check_3d_flow.py` — đo API scan→model, in status/time/field.
- `tools/diag/check_3d_nav.cjs [--abort-scan|--fail-job]` — log request/response, trạng thái modal.

Kết quả:
- `--abort-scan` (POST lỗi): `hasAiResult=true`, `errorVisible=true` → **không nhảy**.
- `--fail-job` (POST 202, poll trả `failed`): `state=initial-scan-form`, `hasAiResult=false`, `has3DResult=false` → **tái hiện đúng triệu chứng**.

## 7. Kết luận

- **Chắc chắn**: job `failed` sau 202 không có nhánh render → quay lại màn hình quét ban đầu. `--fail-job` tái hiện.
- **Nghi ngờ cao nhất**: nút “Dựng mô hình 3D” gọi `s.scan`; `onBuild3D` xóa AI result khi chỉ nhận 202; nếu backend báo `failed` (ảnh không nhận diện / hệ số >1.40 / backend restart), người dùng mất số đo và thấy màn hình đầu.
- **Nghi ngờ thấp**: `<Link href="/scan">` từ saved scan (mở phòng thử mới, không có model) và `router.push("/#catalog")` (apply số đo) — đây là hành vi thiết kế, không phải lỗi nút 3D.
- **Không phải**: nút thiếu `type="button"` (các nút đều có), `window.location`/reload (không tìm thấy), route guard redirect (không có guard cho `/scan`).

Cách kiểm chứng: chạy `node tools/diag/check_3d_nav.cjs --fail-job` trên `main` để xác nhận lỗi có từ trước (trước commit `7415637` còn nặng hơn: mất AI result ngay cả khi POST lỗi).
