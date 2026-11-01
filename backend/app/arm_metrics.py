"""Số đo tay từ mốc MediaPipe: dài tay, bắp tay, cẳng tay.

MediaPipe cho tâm khớp (vai 11, khuỷu 13, cổ tay 15) nên **dài tay** tính được
trực tiếp và đáng tin: đây là tổng hai đoạn thẳng trên ảnh nhân cm/px.

**Chu vi** thì không: mốc chỉ cho trục xương, không cho bề dày thịt. Chu vi được
tính từ bán kính mặt nạ cánh tay (capsule do `remove_arm_capsules` trả về) theo
tiết diện tròn: C = 2πr. Đó là mô hình, không phải phép đo trực tiếp, nên kết
quả phải mang nhãn `photo_estimate` và được kiểm với thước dây.

Kiểm trên P01b (tape: bắp tay 23 cm, cẳng tay 20 cm): biên dạng đọc 29,3 cm cho
cẳng tay vì áo dài tay — đó là chu vi **ngoài lớp áo**, không phải cơ thể. Chưa có
bước trừ hao trang phục (C2), nên hai số này đang **tắt** (``ARM_GIRTHS_ENABLED``);
chỉ dài tay được báo.
"""

from __future__ import annotations

import math
from typing import Sequence

from .torso_mask import point_in_torso_run

# Bán kính hợp lệ cho cánh tay người lớn, tính bằng cm (bắp tay 20-45 cm chu vi).
MIN_LIMB_RADIUS_CM = 2.0
MAX_LIMB_RADIUS_CM = 8.0

MIN_ARM_LENGTH_CM = 40.0
MAX_ARM_LENGTH_CM = 90.0

# Chu vi bắp/cẳng tay từ biên dạng gồm cả lớp tay áo. Chưa có bước trừ hao trang
# phục (C2) nên không được báo như số đo cơ thể: P01b (áo dài tay) đọc 29,3 cm so
# tape 20 cm. Bật lại chỉ khi C2 có dữ liệu hiệu chuẩn.
ARM_GIRTHS_ENABLED = False

# Bề rộng mặt cắt hợp lệ của cánh tay người lớn: 4–16 cm (bán kính 2–8 cm).
MIN_ARM_WIDTH_CM = 2.0 * MIN_LIMB_RADIUS_CM
MAX_ARM_WIDTH_CM = 2.0 * MAX_LIMB_RADIUS_CM

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


def cross_section_touches_torso(
    mask,
    points,
    start,
    end,
    fractions=(0.4, 0.5, 0.6),
) -> bool:
    """True when the limb cut runs into the torso instead of a free arm.

    A perpendicular cut can look plausible in width while its row run is the one
    carrying the torso centre (arm pressed against the body). One unusable
    sample is enough: that side is not a free limb.
    """
    for fraction in fractions:
        cx = float(start[0]) + (float(end[0]) - float(start[0])) * fraction
        cy = float(start[1]) + (float(end[1]) - float(start[1])) * fraction
        if not (0 <= int(cy) < mask.shape[0] and 0 <= int(cx) < mask.shape[1]):
            continue
        if not mask[int(cy), int(cx)]:
            continue
        if point_in_torso_run(mask, points, cx, cy):
            return True
    return False


def _girth_if_separated(mask, points, start, end, cm_per_px, key, reasons):
    """One arm segment: girth only for a separated cut with a 4–16 cm width."""
    if cross_section_touches_torso(mask, points, start, end):
        reasons[key] = "mặt cắt chạm thân: tay sát thân hoặc tay áo dính vào thân"
        return None
    width_px = cross_section_width_px(mask, start, end)
    if width_px is None:
        reasons[key] = "không cắt được mặt cắt vuông góc trên biên dạng"
        return None
    width_cm = float(width_px) * cm_per_px
    if not (MIN_ARM_WIDTH_CM <= width_cm <= MAX_ARM_WIDTH_CM):
        reasons[key] = (
            f"bề rộng mặt cắt {width_cm:.1f} cm ngoài khoảng "
            f"{MIN_ARM_WIDTH_CM:.0f}–{MAX_ARM_WIDTH_CM:.0f} cm"
        )
        return None
    girth = limb_girth_from_mask(mask, start, end, cm_per_px)
    if girth is None:
        reasons[key] = "bán kính mặt cắt ngoài 2–8 cm"
    return girth


def measure_arm_girths(
    mask,
    points: Sequence[Sequence[float]],
    visibility: Sequence[float],
    radii_px: dict[str, float] | None,
    cm_per_px: float,
    enabled: bool | None = None,
) -> tuple[dict[str, float | None], dict]:
    """Bắp tay và cẳng tay từ biên dạng tay.

    Mặc định **tắt** (``ARM_GIRTHS_ENABLED = False``) vì biên dạng gồm cả tay áo
    và chưa có bước trừ hao trang phục (C2): trên P01b (áo dài tay) cẳng tay đọc
    29,3 cm so tape 20 cm. Khi bật (``enabled=True`` — dùng cho test, hoặc sau khi
    C2 có dữ liệu), chu vi chỉ được trả khi:

    * ``radii_px`` không rỗng — ``remove_arm_capsules`` đã tách được một bên tay;
    * mặt cắt vuông góc **không chạm thân** (run chứa xương không chứa tâm thân);
    * bề rộng mặt cắt trong **4–16 cm** (bán kính 2–8 cm).

    Đây là cổng hợp lệ, không phải hệ số hiệu chỉnh.
    """
    empty = {"bicep_cm": None, "forearm_cm": None}
    if enabled is None:
        enabled = ARM_GIRTHS_ENABLED
    if not enabled:
        reason = (
            "Chưa trừ hao lớp tay áo (C2): chu vi đọc trên biên dạng gồm cả tay áo nên "
            "không dùng làm số đo cơ thể; chỉ dài tay được báo."
        )
        return empty, {
            "available": False,
            "enabled": False,
            "reason": reason,
            "reasons": {"bicep_cm": reason, "forearm_cm": reason},
        }
    if not radii_px:
        reason = "không tách được tay khỏi thân"
        return empty, {
            "available": False,
            "enabled": True,
            "reason": reason,
            "reasons": {"bicep_cm": reason, "forearm_cm": reason},
        }
    left_visibility = float(sum(visibility[i] for i in (11, 13, 15)) / 3.0)
    right_visibility = float(sum(visibility[i] for i in (12, 14, 16)) / 3.0)
    order = ("left", "right") if left_visibility >= right_visibility else ("right", "left")
    side = next((name for name in order if name in radii_px), order[0])
    shoulder, elbow, wrist = (11, 13, 15) if side == "left" else (12, 14, 16)
    reasons: dict[str, str] = {}
    girths = {
        "bicep_cm": _girth_if_separated(
            mask, points, points[shoulder], points[elbow], cm_per_px, "bicep_cm", reasons
        ),
        "forearm_cm": _girth_if_separated(
            mask, points, points[elbow], points[wrist], cm_per_px, "forearm_cm", reasons
        ),
    }
    info = {
        "available": any(value is not None for value in girths.values()),
        "enabled": True,
        "side": side,
        "mask": "frontal_raw_silhouette",
        "radii_px": {name: float(radii_px[name]) for name in radii_px},
        "reasons": reasons,
    }
    if not info["available"]:
        info["reason"] = "; ".join(f"{key}: {text}" for key, text in reasons.items())
    return girths, info
