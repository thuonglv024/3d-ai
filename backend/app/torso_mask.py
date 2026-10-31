"""Silhouette helpers: remove arm capsules and flag merged arms / loose clothing.

The module works on a boolean person mask plus MediaPipe pose landmarks. It is
deliberately independent of the mesh: the caller decides which mask to use for
a width/depth row. Nothing here invents a measurement when the arm cannot be
separated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

LEFT = (11, 13, 15)   # shoulder, elbow, wrist
RIGHT = (12, 14, 16)


@dataclass
class ArmRemoval:
    mask: np.ndarray
    arm_mask: np.ndarray
    radius_px: dict[str, float]
    warnings: list[str]


def row_runs(mask: np.ndarray, y: float) -> list[tuple[int, int]]:
    """Foreground runs on one image row, as (start, end) half-open intervals."""
    row = mask[int(np.clip(round(y), 0, mask.shape[0] - 1))]
    padded = np.empty(len(row) + 2, dtype=bool)
    padded[0] = padded[-1] = False
    padded[1:-1] = row
    idx = np.flatnonzero(padded[1:] != padded[:-1])
    return [(int(a), int(b)) for a, b in zip(idx[0::2], idx[1::2])]


def _run_containing(runs: list[tuple[int, int]], x: float) -> tuple[int, int] | None:
    for run in runs:
        if run[0] <= x < run[1]:
            return run
    return None


def _torso_center_x(points: np.ndarray, y: float) -> float:
    shoulder = np.asarray(points[[11, 12]], dtype=float).mean(axis=0)
    hip = np.asarray(points[[23, 24]], dtype=float).mean(axis=0)
    t = (float(y) - shoulder[1]) / max(float(hip[1] - shoulder[1]), 1e-6)
    return float(shoulder[0] + t * (hip[0] - shoulder[0]))


def estimate_arm_radius(
    mask: np.ndarray,
    points: np.ndarray,
    visibility: np.ndarray,
    side: str,
    body_height_px: float,
) -> float | None:
    """Half-thickness of the forearm run, sampled outside the torso.

    Only rows where the forearm run is *separate* from the run containing the
    anatomical centre are used. In a true profile view the near arm overlaps the
    torso, so no separate run exists and the caller supplies a fallback radius.
    """
    shoulder_idx, elbow_idx, wrist_idx = LEFT if side == "left" else RIGHT
    shoulder, elbow, wrist = np.asarray(points[[shoulder_idx, elbow_idx, wrist_idx]], dtype=float)
    if not np.isfinite([shoulder, elbow, wrist]).all():
        return None
    if float(np.min(visibility[[shoulder_idx, elbow_idx, wrist_idx]])) < 0.45:
        return None
    if elbow[1] <= shoulder[1] + 0.03 * body_height_px:
        return None
    if wrist[1] <= shoulder[1] + 0.08 * body_height_px:
        return None
    if np.linalg.norm(wrist - elbow) < 0.04 * body_height_px:
        return None

    widths: list[float] = []
    for t in np.linspace(0.15, 0.90, 16):
        px, py = elbow + t * (wrist - elbow)
        if not (0 <= py < mask.shape[0] and 0 <= px < mask.shape[1]):
            continue
        runs = row_runs(mask, py)
        run = _run_containing(runs, px)
        if run is None:
            continue
        center = _torso_center_x(points, py)
        if run[0] <= center < run[1]:
            continue  # same run as the torso: not a separated arm sample
        widths.append(float(run[1] - run[0]))
    if len(widths) < 3:
        return None
    radius = float(np.median(widths)) / 2.0
    return float(np.clip(radius, 0.012 * body_height_px, 0.060 * body_height_px))


def _capsule_for_segment(
    shape: tuple[int, int],
    a: np.ndarray,
    b: np.ndarray,
    radius_a: float,
    radius_b: float,
) -> np.ndarray:
    capsule = np.zeros(shape, dtype=bool)
    pad = int(np.ceil(max(radius_a, radius_b))) + 2
    x0 = max(0, int(np.floor(min(a[0], b[0]))) - pad)
    x1 = min(shape[1] - 1, int(np.ceil(max(a[0], b[0]))) + pad)
    y0 = max(0, int(np.floor(min(a[1], b[1]))) - pad)
    y1 = min(shape[0] - 1, int(np.ceil(max(a[1], b[1]))) + pad)
    if x1 < x0 or y1 < y0:
        return capsule
    xs = np.arange(x0, x1 + 1)
    ys = np.arange(y0, y1 + 1)
    X, Y = np.meshgrid(xs, ys)
    ab = b - a
    denom = float(ab @ ab)
    if denom <= 1e-9:
        distance = np.hypot(X - a[0], Y - a[1])
        radius = radius_a
    else:
        t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / denom, 0.0, 1.0)
        closest_x = a[0] + t * ab[0]
        closest_y = a[1] + t * ab[1]
        distance = np.hypot(X - closest_x, Y - closest_y)
        radius = radius_a + t * (radius_b - radius_a)
    capsule[y0:y1 + 1, x0:x1 + 1] = distance <= radius
    return capsule


def build_arm_capsule(
    shape: tuple[int, int],
    points: np.ndarray,
    side: str,
    radius_px: float,
) -> np.ndarray:
    """Tapered capsule around shoulder -> elbow -> wrist."""
    shoulder_idx, elbow_idx, wrist_idx = LEFT if side == "left" else RIGHT
    shoulder, elbow, wrist = np.asarray(points[[shoulder_idx, elbow_idx, wrist_idx]], dtype=float)
    upper = _capsule_for_segment(shape, shoulder, elbow, radius_px * 1.15, radius_px)
    lower = _capsule_for_segment(shape, elbow, wrist, radius_px, radius_px * 0.80)
    return upper | lower


def remove_arm_capsules(
    mask: np.ndarray,
    points: np.ndarray,
    visibility: np.ndarray,
    body_height_px: float,
    fallback_radius_px: float | None = None,
    sides: tuple[str, ...] = ("left", "right"),
) -> ArmRemoval:
    """Remove both arm capsules from a copy of the mask.

    A capsule is skipped when it would delete more than 40% of the foreground:
    that usually means the arm overlaps the torso in a profile view and removing
    it would destroy the torso rather than clean an attachment.
    """
    shape = mask.shape
    clean = mask.copy()
    arm_mask = np.zeros(shape, dtype=bool)
    radii: dict[str, float] = {}
    warnings: list[str] = []
    fallback = None
    if fallback_radius_px is not None and fallback_radius_px > 0:
        fallback = float(np.clip(fallback_radius_px, 0.012 * body_height_px, 0.060 * body_height_px))

    for side in sides:
        radius = estimate_arm_radius(mask, points, visibility, side, body_height_px)
        if radius is None and fallback is not None:
            radius = fallback
            warnings.append(f"{side}: dùng bán kính tay dự phòng {radius:.1f}px")
        if radius is None:
            warnings.append(f"{side}: không ước được bán kính tay; bỏ qua")
            continue
        capsule = build_arm_capsule(shape, points, side, radius)
        # Protect a narrow vertical core around the torso axis. In a 90-degree
        # profile the near arm overlaps the torso, and a full capsule would cut
        # the torso into two runs (destroying the depth row). The core keeps the
        # anatomical centre line intact while the outer arm bulge is removed.
        core = np.zeros(shape, dtype=bool)
        half_core = max(2, int(round(0.035 * body_height_px)))
        for y in range(shape[0]):
            center_x = _torso_center_x(points, y)
            x0 = max(0, int(center_x) - half_core)
            x1 = min(shape[1], int(center_x) + half_core + 1)
            if x1 > x0:
                core[y, x0:x1] = True
        capsule &= ~core
        candidate = clean & ~capsule
        # A profile-view capsule can run through the torso centre. Reject a
        # removal that leaves the centre row narrower than a plausible torso
        # (10% of body height); keep the raw mask and report the overlap.
        shoulder = np.asarray(points[[11, 12]], dtype=float).mean(axis=0)
        hip = np.asarray(points[[23, 24]], dtype=float).mean(axis=0)
        sample_ys = np.linspace(shoulder[1] + 0.10 * (hip[1] - shoulder[1]), hip[1], 12)
        min_center = 0.10 * body_height_px
        cut_torso = False
        for sample_y in sample_ys:
            center_x = _torso_center_x(points, sample_y)
            runs = row_runs(candidate, sample_y)
            run = _run_containing(runs, center_x)
            if run is None or (run[1] - run[0]) < min_center:
                cut_torso = True
                break
        if cut_torso:
            warnings.append(f"{side}: capsule cắt qua thân (<{min_center:.0f}px); bỏ qua, giữ mask gốc")
            continue
        removed = mask & capsule
        fraction = float(removed.sum()) / max(float(mask.sum()), 1.0)
        if fraction > 0.40:
            warnings.append(f"{side}: capsule xoá {fraction * 100:.1f}% mask; bỏ qua để tránh mất thân")
            continue
        clean &= ~capsule
        arm_mask |= removed
        radii[side] = round(float(radius), 1)

    if not np.any(clean):
        warnings.append("mask rỗng sau khi loại tay; giữ mask gốc")
        return ArmRemoval(mask=mask, arm_mask=np.zeros(shape, dtype=bool), radius_px={}, warnings=warnings)
    return ArmRemoval(mask=clean, arm_mask=arm_mask, radius_px=radii, warnings=warnings)


def more_visible_arm_side(points: np.ndarray, visibility: np.ndarray) -> str:
    """The near arm in a profile view is the more visible one."""
    left = float(np.mean(np.asarray(visibility, dtype=float)[[11, 13, 15]]))
    right = float(np.mean(np.asarray(visibility, dtype=float)[[12, 14, 16]]))
    return "left" if left >= right else "right"


def row_arm_merged(
    mask: np.ndarray,
    y: float,
    center: float,
    shoulder_span_px: float,
    body_height_px: float,
) -> bool:
    """True when the row still has one abnormally wide run through the centre."""
    runs = row_runs(mask, y)
    run = _run_containing(runs, center)
    if run is None:
        return False
    width = float(run[1] - run[0])
    reference = 1.30 * shoulder_span_px
    return len(runs) == 1 and width > reference


# Plausible biacromial span as a fraction of body height. Used only to reject a
# silhouette row that is obviously wrong (arms raised, merged with a background
# object), never to invent a value.
SHOULDER_RATIO_MIN = 0.16
SHOULDER_RATIO_MAX = 0.32


def shoulder_span(obs: Any) -> tuple[float, str]:
    """Shoulder span as a fraction of body height, with its source.

    MediaPipe landmarks 11/12 sit at the glenohumeral joint centres, not on the
    outer acromion, so their distance is systematically narrower than a tape
    shoulder measurement: 28.0 cm against a 40 cm tape shoulder on the
    tape-measured subject P01b, while the silhouette row at the same height is
    38.2 cm. The tape follows the outer silhouette, so prefer that row and fall
    back to the landmark span only when the row is unusable.

    Returns ``(ratio, source)`` where source is "silhouette" or "landmark".
    """
    height = max(float(obs.height), 1.0)
    landmark = abs(float(obs.points[11, 0]) - float(obs.points[12, 0]))
    y = float((obs.points[11, 1] + obs.points[12, 1]) / 2.0)
    center = float((obs.points[11, 0] + obs.points[12, 0]) / 2.0)
    run = _run_containing(row_runs(obs.mask, y), center)
    if run is not None:
        ratio = float(run[1] - run[0]) / height
        if SHOULDER_RATIO_MIN <= ratio <= SHOULDER_RATIO_MAX:
            return ratio, "silhouette"
    return landmark / height, "landmark"


def clothing_looseness(
    chest_width_cm: float | None,
    shoulder_span_cm: float | None,
    depths_cm: list[float],
    arm_merged_rows: Mapping[str, bool],
    width_ratio: float = 1.30,
    depth_range_cm: float = 2.0,
) -> tuple[bool, list[str]]:
    """Data-driven flag: wide chest vs shoulder span, flat depth profile, merged arms."""
    reasons: list[str] = []
    if (
        chest_width_cm is not None
        and shoulder_span_cm is not None
        and shoulder_span_cm > 0
        and chest_width_cm > shoulder_span_cm * width_ratio
    ):
        reasons.append(
            f"chest_width {chest_width_cm:.1f}cm > {width_ratio:.2f} x shoulder {shoulder_span_cm:.1f}cm"
        )
    if len(depths_cm) >= 2:
        spread = float(max(depths_cm) - min(depths_cm))
        if spread < depth_range_cm:
            reasons.append(f"depth range {spread:.1f}cm < {depth_range_cm:.1f}cm")
    merged = [key for key, value in arm_merged_rows.items() if value]
    if merged:
        reasons.append("arm_merged: " + ", ".join(merged))
    return bool(reasons), reasons
