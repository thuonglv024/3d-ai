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
