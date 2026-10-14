import numpy as np
import pytest

from app.camera_fusion import (
    aligned_torso_landmarks,
    extract_paired_torso_profiles,
    fuse_camera_scale,
    synchronized_torso_profile,
)
from app.images import InvalidPhoto
from app.measurements import estimate_from_profiles
from app.reconstruction import Observation, torso_profile as legacy_torso_profile


def _make_observation(
    *,
    shape: tuple[int, int] = (480, 640),
    shoulder_y: float = 140.0,
    hip_y: float = 380.0,
    center_x: float = 320.0,
    base_half_span: float = 90.0,
    waist_taper: float = 12.0,
    height: float | None = None,
    capture_mode: str = "upper_body",
    left_vis: float = 0.95,
    right_vis: float = 0.95,
    right_offset: tuple[float, float] = (0.0, 0.0),
) -> Observation:
    h, w = shape
    mask = np.zeros((h, w), dtype=bool)
    true_torso = 380.0 - 140.0
    for y in range(25, h - 5):
        t = (y - 140.0) / true_torso
        # Smooth anatomical contour (wider at chest/hip, narrower at waist t ~ 0.65)
        contour = base_half_span - waist_taper * np.exp(-((t - 0.65) / 0.22) ** 2)
        half_w = int(round(max(contour, 20.0)))
        x0 = max(4, int(round(center_x)) - half_w)
        x1 = min(w - 4, int(round(center_x)) + half_w)
        mask[y, x0:x1] = True

    points = np.zeros((33, 2), dtype=float)
    points[:, 0] = center_x
    points[:, 1] = shoulder_y
    # Left side [11, 23]
    points[11] = [center_x - 65.0, shoulder_y]
    points[23] = [center_x - 45.0, hip_y]
    # Right side [12, 24]
    points[12] = [center_x + 65.0 + right_offset[0], shoulder_y + right_offset[1] * 0.2]
    points[24] = [center_x + 45.0 + right_offset[0], hip_y + right_offset[1]]

    visibility = np.full(33, 0.9, dtype=float)
    visibility[[11, 23]] = left_vis
    visibility[[12, 24]] = right_vis

    inferred_height = float((hip_y - shoulder_y) / 0.29) if height is None else float(height)
    return Observation(
        mask=mask,
        points=points,
        visibility=visibility,
        top=25,
        bottom=h - 6,
        height=inferred_height,
        capture_mode=capture_mode,
    )


@pytest.mark.parametrize("drift_ratio,expected_legacy_err", [(0.10, 1.0 - 1.0 / 1.10), (-0.10, 1.0 / 0.90 - 1.0)])
def test_hip_vertical_drift_10_percent_preserves_exact_depth_to_width_ratio(drift_ratio, expected_legacy_err):
    """When 90-degree lateral hip landmarks drift by +/-10%, fused D/W error must be 0.00% (< 0.5%)."""
    base_shoulder_y = 140.0
    base_hip_y = 380.0
    base_torso = base_hip_y - base_shoulder_y

    frontal = _make_observation(
        shoulder_y=base_shoulder_y,
        hip_y=base_hip_y,
        base_half_span=95.0,
        waist_taper=0.0,
        capture_mode="upper_body",
    )
    lateral_clean = _make_observation(
        shoulder_y=base_shoulder_y,
        hip_y=base_hip_y,
        base_half_span=68.0,
        waist_taper=0.0,
        capture_mode="upper_body",
    )

    drifted_hip_y = base_shoulder_y + base_torso * (1.0 + drift_ratio)
    lateral_drifted = _make_observation(
        shoulder_y=base_shoulder_y,
        hip_y=drifted_hip_y,
        base_half_span=68.0,
        waist_taper=0.0,
        capture_mode="upper_body",
    )

    # Verify lateral.height drifted by +10% or -10% relative to frontal.height
    assert lateral_drifted.height == pytest.approx(frontal.height * (1.0 + drift_ratio), rel=1e-6)

    # Baseline clean ratio
    _, w_clean, d_clean = extract_paired_torso_profiles(frontal, lateral_clean)
    baseline_dw = d_clean / w_clean

    # 1. Legacy independent calculation suffers exact ~9.09% (+10% drift) and ~11.11% (-10% drift) D/W distortion
    _, w_legacy = legacy_torso_profile(frontal)
    _, d_legacy_drifted = legacy_torso_profile(lateral_drifted)
    legacy_dw_err = float(np.mean(np.abs((d_legacy_drifted / w_legacy) - baseline_dw) / baseline_dw))
    assert legacy_dw_err == pytest.approx(expected_legacy_err, rel=1e-4)
    assert 0.09 <= legacy_dw_err <= 0.112

    # 2. Tier 2 Camera Fusion + synchronized torso profile achieves 0.00% D/W distortion
    shared_h = fuse_camera_scale(frontal, lateral_drifted)
    assert shared_h == pytest.approx(frontal.height, abs=1e-9)

    _, w_fused, d_fused = extract_paired_torso_profiles(frontal, lateral_drifted)
    fused_dw = d_fused / w_fused
    fused_dw_err = float(np.max(np.abs(fused_dw - baseline_dw) / baseline_dw))

    assert fused_dw_err < 0.005  # strictly < 0.5%
    assert fused_dw_err == pytest.approx(0.0, abs=1e-12)  # exact 0.00% immunity

    # 3. Also verify on a non-uniform contoured torso (waist_taper > 0) where scan rows vary with y
    frontal_contoured = _make_observation(shoulder_y=base_shoulder_y, hip_y=base_hip_y, base_half_span=95.0, waist_taper=14.0)
    lateral_contoured_clean = _make_observation(shoulder_y=base_shoulder_y, hip_y=base_hip_y, base_half_span=68.0, waist_taper=10.0)
    lateral_contoured_drifted = _make_observation(shoulder_y=base_shoulder_y, hip_y=drifted_hip_y, base_half_span=68.0, waist_taper=10.0)

    _, w_c_clean, d_c_clean = extract_paired_torso_profiles(frontal_contoured, lateral_contoured_clean)
    _, w_c_fused, d_c_fused = extract_paired_torso_profiles(frontal_contoured, lateral_contoured_drifted)
    contoured_dw_err = float(np.max(np.abs((d_c_fused / w_c_fused) - (d_c_clean / w_c_clean)) / (d_c_clean / w_c_clean)))
    assert contoured_dw_err == pytest.approx(0.0, abs=1e-12)

    # Verify downstream body measurements (chest/waist) remain identical and do not bloat/flatten
    m_clean, _ = estimate_from_profiles(np.linspace(0.12, 1.12, 35), w_c_clean, d_c_clean, 172.0, 0.22)
    m_drifted, _ = estimate_from_profiles(np.linspace(0.12, 1.12, 35), w_c_fused, d_c_fused, 172.0, 0.22)
    assert m_drifted["chest_cm"] == pytest.approx(m_clean["chest_cm"], abs=1e-6)
    assert m_drifted["waist_cm"] == pytest.approx(m_clean["waist_cm"], abs=1e-6)


def test_aligned_torso_landmarks_rejects_occluded_far_side_drift():
    """In 90-degree side view, low-visibility far-side landmarks must not pull shoulder/hip centres."""
    frontal = _make_observation(shoulder_y=140.0, hip_y=380.0)
    # Near side (left) is clearly visible (0.95) at hip_y=380; far side (right) is occluded (0.20) and drifts +55px
    lateral_occluded = _make_observation(
        shoulder_y=140.0,
        hip_y=380.0,
        left_vis=0.95,
        right_vis=0.20,
        right_offset=(40.0, 55.0),
    )

    shoulder, hip = aligned_torso_landmarks(lateral_occluded, reference_obs=frontal)
    assert shoulder[0] == pytest.approx(lateral_occluded.points[11, 0], abs=1e-6)
    assert hip[0] == pytest.approx(lateral_occluded.points[23, 0], abs=1e-6)
    assert hip[1] - shoulder[1] == pytest.approx(380.0 - 140.0, abs=1e-6)


def test_fuse_camera_scale_validates_and_handles_cross_resolution():
    frontal = _make_observation(shape=(480, 640), height=900.0)
    lateral_HalfRes = _make_observation(shape=(240, 320), height=440.0)
    fused = fuse_camera_scale(frontal, lateral_HalfRes)
    # Projected lateral height is 440 * (480 / 240) = 880; 0.9 * 900 + 0.1 * 880 = 898.0
    assert fused == pytest.approx(898.0, abs=1e-6)

    invalid_obs = _make_observation(height=0.0)
    with pytest.raises(InvalidPhoto):
        fuse_camera_scale(invalid_obs, frontal)
    with pytest.raises(InvalidPhoto):
        synchronized_torso_profile(invalid_obs)


def test_cross_view_distance_mismatch_warning_and_rejection():
    from app.camera_fusion import assess_cross_view_quality

    frontal = _make_observation(shape=(480, 640), height=400.0, capture_mode="full_body")
    # 38% difference -> triggers warning (> 35%), does not reject (<= 45%)
    lateral_warn = _make_observation(shape=(480, 640), height=552.0, capture_mode="full_body")
    diag = assess_cross_view_quality(frontal, lateral_warn)
    assert diag["detector_confidence_front"] > 0.8
    assert diag["detector_confidence_side"] > 0.8
    assert diag["height_scale_px"] == pytest.approx(400.0)
    assert diag["cross_view_height_ratio"] == pytest.approx(1.38)
    assert diag["cross_view_warning"] is not None
    assert "38.0%" in diag["cross_view_warning"]
    assert "trang phục" in diag["clothing_silhouette_note"]

    # > 45% difference in full_body -> rejected with InvalidPhoto
    lateral_extreme = _make_observation(shape=(480, 640), height=620.0, capture_mode="full_body")
    with pytest.raises(InvalidPhoto, match="Khoảng cách đứng"):
        fuse_camera_scale(frontal, lateral_extreme)
