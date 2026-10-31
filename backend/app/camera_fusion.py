"""Tier 2 camera scale fusion and anatomical landmark alignment across frontal and lateral views."""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d

from .images import InvalidPhoto
from .torso_mask import more_visible_arm_side, remove_arm_capsules


def _nanmedian_small(values: list[float]) -> float:
    valid = sorted(v for v in values if np.isfinite(v))
    n = len(valid)
    if not n:
        return float("nan")
    mid = n >> 1
    return float(valid[mid]) if (n & 1) else 0.5 * (valid[mid - 1] + valid[mid])


def center_run_width(mask: np.ndarray, y: float, center: float) -> float:
    """Width of foreground run nearest the anatomical centre, excluding arms."""
    row = mask[min(max(int(round(y)), 0), mask.shape[0] - 1)]
    if row[0] or row[-1]:
        padded = np.empty(len(row) + 2, dtype=bool)
        padded[0] = False
        padded[1:-1] = row
        padded[-1] = False
        idx_trans = np.flatnonzero(padded[1:] != padded[:-1])
    else:
        idx_trans = np.flatnonzero(row[1:] != row[:-1]) + 1
    if not len(idx_trans):
        return float("nan")
    starts = idx_trans[0::2]
    ends = idx_trans[1::2]
    if len(starts) == 1:
        return float(ends[0] - starts[0])
    containing = np.where((starts <= center) & (ends > center))[0]
    idx = int(containing[0]) if len(containing) else int(np.argmin(abs((starts + ends) / 2 - center)))
    return float(ends[idx] - starts[idx])


def aligned_torso_landmarks(obs, reference_obs=None) -> tuple[np.ndarray, np.ndarray]:
    """Compute visibility-weighted shoulder and hip centres with cross-view vertical regularization.

    - Frontal view (`reference_obs is None` and balanced visibility): weighted average of
      shoulder pair `[11, 12]` and hip pair `[23, 24]` by landmark visibility.
    - Lateral view (`reference_obs` provided or one body side occluded): prioritizes the
      camera-facing side (`left = [11, 23]` vs `right = [12, 24]`) so occluded far-side
      landmarks cannot drag the torso axis. When captured on the same camera frame shape as
      `reference_obs`, regularizes `hip[1]` using the frontal `ref_torso` span so horizontal
      scan rows cut through identical anatomical planes in both views.
    """
    points = np.asarray(obs.points, dtype=float)
    vis = np.clip(np.asarray(obs.visibility, dtype=float), 1e-4, 1.0)

    left_vis = vis[[11, 23]]
    right_vis = vis[[12, 24]]
    left_mean, right_mean = float(np.mean(left_vis)), float(np.mean(right_vis))
    left_min, right_min = float(np.min(left_vis)), float(np.min(right_vis))

    asymmetric_side = abs(left_mean - right_mean) > 0.15 or min(left_min, right_min) < 0.50

    if reference_obs is None and not asymmetric_side:
        shoulder = np.average(points[[11, 12]], axis=0, weights=vis[[11, 12]])
        hip = np.average(points[[23, 24]], axis=0, weights=vis[[23, 24]])
    else:
        if left_min >= 0.55 and right_min < 0.50:
            side_weights = np.array([1.0, 0.0], dtype=float)
        elif right_min >= 0.55 and left_min < 0.50:
            side_weights = np.array([0.0, 1.0], dtype=float)
        elif abs(left_mean - right_mean) > 0.15:
            side_weights = np.array([left_mean, right_mean], dtype=float) ** 4
        else:
            side_weights = np.array([left_mean, right_mean], dtype=float)

        w_shoulder = side_weights * vis[[11, 12]]
        if float(np.sum(w_shoulder)) <= 0:
            w_shoulder = vis[[11, 12]]
        shoulder = np.average(points[[11, 12]], axis=0, weights=w_shoulder)

        w_hip = side_weights * vis[[23, 24]]
        if float(np.sum(w_hip)) <= 0:
            w_hip = vis[[23, 24]]
        hip = np.average(points[[23, 24]], axis=0, weights=w_hip)

    shoulder = np.asarray(shoulder, dtype=float).copy()
    hip = np.asarray(hip, dtype=float).copy()

    if reference_obs is not None:
        ref_shoulder, ref_hip = aligned_torso_landmarks(reference_obs, reference_obs=None)
        ref_torso = float(ref_hip[1] - ref_shoulder[1])
        lat_torso = float(hip[1] - shoulder[1])
        if ref_torso > 0:
            if obs.mask.shape == reference_obs.mask.shape:
                # Same fixed camera resolution: lock vertical torso span to frontal reference
                # so horizontal scan rows slice identical anatomical planes regardless of 90° hip drift.
                regularized_torso = ref_torso
            else:
                scale_y = float(obs.mask.shape[0]) / max(float(reference_obs.mask.shape[0]), 1.0)
                scaled_ref_torso = ref_torso * scale_y
                regularized_torso = 0.85 * scaled_ref_torso + 0.15 * lat_torso
            hip[1] = float(np.clip(shoulder[1] + regularized_torso, shoulder[1] + 1.0, obs.mask.shape[0] - 1.0))

    return shoulder, hip


def fuse_camera_scale(frontal, lateral) -> float:
    """Compute a unified reference height scale `shared_height` across frontal and lateral views.

    When both photos are captured from the same fixed webcam (`frontal.mask.shape == lateral.mask.shape`),
    locking `shared_height` to the frontal reference scale guarantees that both `widths` and `depths`
    are normalized by the exact same denominator:
        (D_px / H_shared) / (W_px / H_shared) == D_px / W_px
    making the depth-to-width ratio (D/W) completely immune (0.00% error) to vertical hip landmark drift
    in the 90-degree lateral view.
    """
    frontal_h = float(frontal.height)
    lateral_h = float(lateral.height)
    if not np.isfinite(frontal_h) or frontal_h <= 0:
        raise InvalidPhoto("Chiều cao tham chiếu ảnh chính diện không hợp lệ.")
    if not np.isfinite(lateral_h) or lateral_h <= 0:
        raise InvalidPhoto("Chiều cao tham chiếu ảnh nghiêng không hợp lệ.")

    if frontal.mask.shape == lateral.mask.shape:
        diff_ratio = abs(lateral_h - frontal_h) / max(frontal_h, 1.0)
        mode = getattr(frontal, "capture_mode", "full_body")
        max_allowed = 0.45 if mode == "full_body" else 0.55
        if diff_ratio > max_allowed:
            raise InvalidPhoto(
                "Khoảng cách đứng giữa ảnh chính diện và ảnh nghiêng chênh lệch quá lớn. "
                "Hãy giữ nguyên vị trí đứng khi xoay người 90°."
            )
        return frontal_h

    scale_y = float(frontal.mask.shape[0]) / max(float(lateral.mask.shape[0]), 1.0)
    projected_lateral_h = lateral_h * scale_y
    diff_ratio = abs(projected_lateral_h - frontal_h) / max(frontal_h, 1.0)
    if diff_ratio > 0.45:
        raise InvalidPhoto(
            "Khoảng cách đứng giữa ảnh chính diện và ảnh nghiêng chênh lệch quá lớn. "
            "Hãy giữ nguyên vị trí đứng khi xoay người 90°."
        )
    return float(0.90 * frontal_h + 0.10 * projected_lateral_h)


def assess_cross_view_quality(frontal, lateral, shared_height: float | None = None) -> dict:
    """Build cross-view quality diagnostics for profile['quality_diagnostics'].

    Explicitly distinguishes MediaPipe `detector_confidence` (2D landmark visibility)
    from anthropometric measurement accuracy.
    """
    h_scale = float(shared_height if shared_height is not None else fuse_camera_scale(frontal, lateral))
    mode = getattr(frontal, "capture_mode", "full_body")
    key_indices = [11, 12, 23, 24] if mode == "upper_body" else [11, 12, 23, 24, 25, 26, 27, 28]
    vis_front = np.asarray(frontal.visibility, dtype=float)
    vis_side = np.asarray(lateral.visibility, dtype=float)
    conf_front = float(np.mean(vis_front[key_indices])) if len(vis_front) > max(key_indices) else float(np.mean(vis_front))
    conf_side = float(np.mean(vis_side[key_indices])) if len(vis_side) > max(key_indices) else float(np.mean(vis_side))

    scale_y = (
        1.0
        if frontal.mask.shape == lateral.mask.shape
        else float(frontal.mask.shape[0]) / max(float(lateral.mask.shape[0]), 1.0)
    )
    projected_lateral_h = float(lateral.height) * scale_y
    height_ratio = projected_lateral_h / max(float(frontal.height), 1.0)
    diff_ratio = abs(projected_lateral_h - float(frontal.height)) / max(float(frontal.height), 1.0)

    cross_view_warning = None
    if diff_ratio > 0.15:
        cross_view_warning = (
            f"Chiều cao khung người giữa 2 góc chụp chênh lệch {diff_ratio * 100:.1f}% (>15%); "
            "mỗi ảnh được quy đổi cm/px theo chiều cao riêng, nhưng hãy đứng nguyên vị trí "
            "khi xoay người 90° để hạn chế sai số tỷ lệ."
        )

    return {
        "detector_confidence_front": round(conf_front, 4),
        "detector_confidence_side": round(conf_side, 4),
        "confidence_semantics": "detector_confidence_only_not_measurement_accuracy",
        "height_scale_px": round(h_scale, 2),
        "front_body_height_px": round(float(frontal.height), 2),
        "side_body_height_px": round(float(lateral.height), 2),
        "per_view_scale_note": "cm/px dùng chiều cao từng ảnh; độ sâu không chuẩn hoá bằng shared height.",
        "cross_view_height_ratio": round(height_ratio, 4),
        "cross_view_height_diff_ratio": round(diff_ratio, 4),
        "cross_view_warning": cross_view_warning,
        "clothing_silhouette_note": (
            "Biên dạng 2D bao gồm cả độ dày trang phục; quần áo rộng có thể làm tăng chu vi ngực/eo/mông ước lượng."
        ),
    }


def synchronized_torso_profile(
    obs,
    reference_obs=None,
    shared_height: float | None = None,
    norm_height: float | None = None,
    arm_sides: tuple[str, ...] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract normalized silhouette widths/depths for one view.

    ``norm_height`` is the body height *of this image*, so the caller can turn
    the ratios into cm with that image's own cm/px scale. ``shared_height`` is
    kept for the legacy paired helper (and its regression test); new callers
    should pass ``norm_height``. The arm capsules are removed once per
    Observation before any row is sampled.
    """
    shoulder, hip = aligned_torso_landmarks(obs, reference_obs=reference_obs)
    norm = float(norm_height if norm_height is not None else (shared_height if shared_height is not None else obs.height))
    if not np.isfinite(norm) or norm <= 0:
        raise InvalidPhoto("Không xác định được chiều cao tham chiếu.")
    if hip[1] - shoulder[1] < norm * 0.15:
        raise InvalidPhoto("Không xác định được vùng thân. Hãy đứng thẳng và chụp lại.")

    # Remove the arm capsules once; later calls on the same Observation reuse the
    # cleaned mask instead of carving it twice.
    if not hasattr(obs, "arm_mask"):
        obs.raw_mask = obs.mask
        removal = remove_arm_capsules(
            obs.raw_mask,
            np.asarray(obs.points, dtype=float),
            np.asarray(obs.visibility, dtype=float),
            float(obs.height),
            fallback_radius_px=getattr(obs, "arm_radius_hint", None),
            sides=arm_sides or ("left", "right"),
        )
        obs.mask = removal.mask
        obs.arm_mask = removal.arm_mask
        obs.arm_radius_px = removal.radius_px
        obs.arm_removal_warnings = removal.warnings

    fractions = np.linspace(0.12, 1.12, 35)
    sampled = np.minimum(fractions, 0.78) if getattr(obs, "capture_mode", "full_body") == "upper_body" else fractions
    rows = shoulder[1] + sampled * (hip[1] - shoulder[1])
    centers = shoulder[0] + sampled * (hip[0] - shoulder[0])
    widths = []
    for row, center in zip(rows, centers):
        local = [center_run_width(obs.mask, row + d, center) for d in (-2, -1, 0, 1, 2)]
        widths.append(_nanmedian_small(local) / norm)
    widths = np.asarray(widths, dtype=float)
    if not np.all(np.isfinite(widths)) or np.min(widths) < 0.06 or np.max(widths) > 0.40:
        raise InvalidPhoto("Đường viền cơ thể chưa rõ. Hãy dùng nền đơn giản và tránh tay che thân.")
    return fractions, gaussian_filter1d(widths, sigma=1.4)


torso_profile = synchronized_torso_profile


def extract_per_view_torso_profiles(frontal, lateral) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Widths normalized by the frontal height, depths by the lateral height.

    The two photos can be taken at different distances. Dividing both views by a
    shared denominator inflated depth whenever the lateral subject was closer;
    each view now has its own cm/px scale (``height_cm / view.height``).
    """
    fractions, widths = synchronized_torso_profile(frontal, reference_obs=None, norm_height=frontal.height)
    if getattr(frontal, "arm_radius_px", None):
        hint = float(np.mean(list(frontal.arm_radius_px.values()))) * float(lateral.height) / max(float(frontal.height), 1.0)
        lateral.arm_radius_hint = hint
    _, depths = synchronized_torso_profile(
        lateral,
        reference_obs=frontal,
        norm_height=lateral.height,
        arm_sides=(more_visible_arm_side(lateral.points, lateral.visibility),),
    )
    return fractions, widths, depths


def extract_paired_torso_profiles(frontal, lateral) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Legacy shared-height extraction, kept for the old D/W regression test.

    New measurement code uses :func:`extract_per_view_torso_profiles`.
    """
    shared_height = fuse_camera_scale(frontal, lateral)
    fractions, widths = synchronized_torso_profile(frontal, reference_obs=None, shared_height=shared_height)
    _, depths = synchronized_torso_profile(lateral, reference_obs=frontal, shared_height=shared_height)
    return fractions, widths, depths
