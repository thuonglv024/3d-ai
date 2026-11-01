"""Số đo tay từ mốc MediaPipe: dài tay, bắp tay, cẳng tay.

MediaPipe cho tâm khớp (vai 11, khuỷu 13, cổ tay 15) nên **dài tay** tính được
trực tiếp và đáng tin: đây là tổng hai đoạn thẳng trên ảnh nhân cm/px.

**Chu vi** thì không: mốc chỉ cho trục xương, không cho bề dày thịt. Chu vi được
tính từ bán kính mặt nạ cánh tay (capsule do `remove_arm_capsules` trả về) theo
tiết diện tròn: C = 2πr. Đó là mô hình, không phải phép đo trực tiếp, nên kết
quả phải mang nhãn `photo_estimate` và được kiểm với thước dây.

Kiểm trên P01b (tape: bắp tay 23 cm, cẳng tay 20 cm): bán kính capsule tương
ứng 3,66 cm và 3,18 cm. Nếu bán kính lệch quá 25%, hàm trả None thay vì một con
số vô nghĩa.
"""

from __future__ import annotations

import math
from typing import Sequence

# Bán kính hợp lệ cho cánh tay người lớn, tính bằng cm (bắp tay 20-45 cm chu vi).
MIN_LIMB_RADIUS_CM = 2.0
MAX_LIMB_RADIUS_CM = 8.0

MIN_ARM_LENGTH_CM = 40.0
MAX_ARM_LENGTH_CM = 90.0

POINT_SHOULDER = 11
POINT_ELBOW = 13
POINT_WRIST = 15


def arm_length_cm(points: Sequence[Sequence[float]], cm_per_px: float) -> float | None:
    """Vai → khuỷu → cổ tay, tính bằng cm.

    Chỉ dùng một bên (trái) vì ảnh chính diện có thể khuất bên kia; người dùng
    được yêu cầu đứng thẳng nên hai bên xấp xỉ nhau.
    """
    if cm_per_px <= 0:
        return None
    shoulder = points[POINT_SHOULDER]
    elbow = points[POINT_ELBOW]
    wrist = points[POINT_WRIST]
    upper = math.dist(shoulder, elbow)
    lower = math.dist(elbow, wrist)
    total = (upper + lower) * cm_per_px
    if not (MIN_ARM_LENGTH_CM <= total <= MAX_ARM_LENGTH_CM):
        return None
    return round(total, 1)


def limb_girth_cm(radius_px: float | None, cm_per_px: float) -> float | None:
    """Chu vi chi từ bán kính mặt nạ, theo tiết diện tròn C = 2πr."""
    if radius_px is None or radius_px <= 0 or cm_per_px <= 0:
        return None
    radius_cm = float(radius_px) * cm_per_px
    if not (MIN_LIMB_RADIUS_CM <= radius_cm <= MAX_LIMB_RADIUS_CM):
        return None
    return round(2 * math.pi * radius_cm, 1)


def arm_measurements(
    points: Sequence[Sequence[float]],
    cm_per_px: float,
    upper_radius_px: float | None,
    lower_radius_px: float | None,
) -> dict[str, float | None]:
    """Bộ ba số đo tay, mỗi số có thể None nếu không đủ tin cậy."""
    return {
        "arm_length_cm": arm_length_cm(points, cm_per_px),
        "bicep_cm": limb_girth_cm(upper_radius_px, cm_per_px),
        "forearm_cm": limb_girth_cm(lower_radius_px, cm_per_px),
    }


def _axis_frame(start, end):
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 0:
        return None
    return (dx / length, dy / length), (-dy / length, dx / length), length


def cross_section_width_px(mask, start, end, fractions=(0.4, 0.5, 0.6)) -> float | None:
    """Bề rộng mặt nạ cắt **vuông góc** với trục xương tại các mốc của đoạn.

    Cắt ngang hàng ảnh sẽ làm cánh tay nằm chéo bị rộng giả (1/cos góc); phép
    cắt vuông góc tránh lỗi đó. Trả trung vị của các mốc, None nếu không cắt được.
    """
    frame = _axis_frame(start, end)
    if frame is None:
        return None
    _axis, normal, _length = frame
    height, width = mask.shape
    widths: list[float] = []
    for fraction in fractions:
        cx = float(start[0]) + (float(end[0]) - float(start[0])) * fraction
        cy = float(start[1]) + (float(end[1]) - float(start[1])) * fraction
        if not (0 <= int(cy) < height and 0 <= int(cx) < width):
            continue
        if not mask[int(cy), int(cx)]:
            continue
        total = 0.0
        for direction in (1.0, -1.0):
            step = 0.0
            while step < 400.0:
                px = cx + direction * normal[0] * (step + 0.5)
                py = cy + direction * normal[1] * (step + 0.5)
                if not (0 <= int(py) < height and 0 <= int(px) < width) or not mask[int(py), int(px)]:
                    break
                step += 0.5
            total += step
        if total > 0:
            widths.append(total)
    if len(widths) < 2:
        return None
    return float(sorted(widths)[len(widths) // 2])


def limb_girth_from_mask(mask, start, end, cm_per_px: float) -> float | None:
    """Chu vi chi từ mặt cắt vuông góc: coi tiết diện tròn, C = π * bề rộng."""
    width_px = cross_section_width_px(mask, start, end)
    if width_px is None or cm_per_px <= 0:
        return None
    radius_cm = width_px * cm_per_px / 2.0
    if not (MIN_LIMB_RADIUS_CM <= radius_cm <= MAX_LIMB_RADIUS_CM):
        return None
    return round(2 * math.pi * radius_cm, 1)


def measure_arm_girths(
    mask,
    points: Sequence[Sequence[float]],
    visibility: Sequence[float],
    radii_px: dict[str, float] | None,
    cm_per_px: float,
) -> tuple[dict[str, float | None], dict]:
    """Bắp tay và cẳng tay từ biên dạng tay, chỉ khi tay đã tách khỏi thân.

    Điều kiện bật: ``radii_px`` không rỗng, tức ``remove_arm_capsules`` đã tách
    được ít nhất một bên tay khỏi thân. Chọn bên có tổng visibility ba mốc
    vai–khuỷu–cổ tay cao hơn, rồi cắt vuông góc trên **mask gốc** (mask đã tách
    tay không còn tay để cắt). Bán kính ngoài 2–8 cm trả None trong
    ``limb_girth_from_mask`` — đó là cổng hợp lệ, không phải hệ số hiệu chỉnh.

    Lưu ý: biên dạng gồm cả tay áo. Trên P01b (áo dài tay) cẳng tay ra 29,3 cm
    so tape 20 cm; số này chỉ nên đọc như "chu vi ngoài lớp áo".
    """
    empty = {"bicep_cm": None, "forearm_cm": None}
    if not radii_px:
        return empty, {"available": False, "reason": "không tách được tay khỏi thân"}
    left_visibility = float(sum(visibility[i] for i in (11, 13, 15)) / 3.0)
    right_visibility = float(sum(visibility[i] for i in (12, 14, 16)) / 3.0)
    order = ("left", "right") if left_visibility >= right_visibility else ("right", "left")
    side = next((name for name in order if name in radii_px), order[0])
    shoulder, elbow, wrist = (11, 13, 15) if side == "left" else (12, 14, 16)
    girths = {
        "bicep_cm": limb_girth_from_mask(mask, points[shoulder], points[elbow], cm_per_px),
        "forearm_cm": limb_girth_from_mask(mask, points[elbow], points[wrist], cm_per_px),
    }
    info = {
        "available": any(value is not None for value in girths.values()),
        "side": side,
        "mask": "frontal_raw_silhouette",
        "radii_px": {name: float(radii_px[name]) for name in radii_px},
    }
    return girths, info
