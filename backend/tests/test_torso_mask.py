"""Regression tests for per-image scale, arm capsules, and clothing flags."""
import numpy as np
import pytest

from app.camera_fusion import assess_cross_view_quality, extract_per_view_torso_profiles, synchronized_torso_profile
from app.images import InvalidPhoto
from app.measurements import ClothingOrArmMergedError, closed_torso_section, fit_measurement_targets
from app.reconstruction import Observation, read_template
from app.torso_mask import MIN_FRAME_COVERAGE, clothing_looseness, frame_coverage, remove_arm_capsules, row_arm_merged, shoulder_span


def _observation(height: float, mask_width_px: int, shape=(400, 400)) -> Observation:
    h, w = shape
    mask = np.zeros((h, w), dtype=bool)
    x0 = (w - mask_width_px) // 2
    mask[60:340, x0:x0 + mask_width_px] = True
    points = np.zeros((33, 2), dtype=float)
    points[:, 0] = w / 2
    points[:, 1] = 100
    points[11] = [w / 2 - 50, 100]
    points[12] = [w / 2 + 50, 100]
    points[23] = [w / 2 - 40, 300]
    points[24] = [w / 2 + 40, 300]
    visibility = np.full(33, 0.9, dtype=float)
    return Observation(mask=mask, points=points, visibility=visibility, top=60, bottom=340,
                       height=float(height), capture_mode="full_body")


def test_per_view_scale_keeps_cm_equal_when_lateral_is_taller():
    frontal = _observation(height=800.0, mask_width_px=160)
    # Same physical body, but the lateral image is 8% taller and its pixels are
    # 8% larger: 160 * 1.08 = 172.8 px.
    lateral = _observation(height=864.0, mask_width_px=173)
    fractions, widths, depths = extract_per_view_torso_profiles(frontal, lateral)
    assert np.median(widths) == pytest.approx(160 / 800.0, rel=1e-3)
    assert np.median(depths) == pytest.approx(173 / 864.0, rel=1e-3)
    # The old shared-height normalisation would inflate depth by 8%.
    old_depth = 173 / 800.0
    assert old_depth / np.median(depths) == pytest.approx(1.08, rel=1e-3)


def test_synchronized_torso_profile_accepts_per_view_norm_height():
    lateral = _observation(height=864.0, mask_width_px=173)
    _, own = synchronized_torso_profile(lateral, norm_height=lateral.height)
    _, shared = synchronized_torso_profile(
        _observation(height=864.0, mask_width_px=173), shared_height=800.0
    )
    assert np.median(own) == pytest.approx(173 / 864.0, rel=1e-3)
    assert np.median(shared) == pytest.approx(173 / 800.0, rel=1e-3)


def test_arm_capsule_removes_separated_arms_but_keeps_torso():
    mask = np.zeros((300, 200), dtype=bool)
    mask[50:251, 70:131] = True       # torso
    mask[60:251, 10:31] = True        # left arm
    mask[60:251, 170:191] = True      # right arm
    points = np.zeros((33, 2), dtype=float)
    points[:, 0], points[:, 1] = 100, 90
    points[11], points[12] = [75, 90], [125, 90]
    points[13], points[14] = [20, 160], [180, 160]
    points[15], points[16] = [20, 230], [180, 230]
    points[23], points[24] = [80, 250], [120, 250]
    visibility = np.full(33, 0.95, dtype=float)

    removal = remove_arm_capsules(mask, points, visibility, body_height_px=300.0)
    assert set(removal.radius_px) == {"left", "right"}
    assert removal.arm_mask.sum() > 0
    assert not removal.mask[200, 20]      # left arm removed
    assert not removal.mask[200, 180]     # right arm removed
    assert removal.mask[200, 100]         # torso centre kept


def test_clothing_flag_on_and_off():
    on_flag, on_reasons = clothing_looseness(
        53.1, 27.8, [23.8, 23.7, 23.6],
        {"chest_cm": True, "waist_cm": False, "hip_cm": False},
    )
    assert on_flag is True
    assert any("chest_width" in reason for reason in on_reasons)
    assert any("depth range" in reason for reason in on_reasons)
    assert any("arm_merged" in reason for reason in on_reasons)

    off_flag, off_reasons = clothing_looseness(
        31.0, 40.0, [22.0, 18.0, 23.0],
        {"chest_cm": False, "waist_cm": False, "hip_cm": False},
    )
    assert off_flag is False
    assert off_reasons == []


def test_row_arm_merged_uses_shoulder_span():
    mask = np.zeros((200, 300), dtype=bool)
    mask[50:150, 20:280] = True  # one wide run, arms merged
    assert row_arm_merged(mask, 100, 150, shoulder_span_px=100, body_height_px=200)
    split = mask.copy()
    split[:, 100:110] = False  # a gap through the centre is not a merged row
    assert not row_arm_merged(split, 100, 90, shoulder_span_px=100, body_height_px=200)


def test_fit_guard_error_has_code_and_clothing_message():
    mesh = read_template()
    mesh.apply_scale(1.75)
    perimeter, _ = closed_torso_section(mesh, 0.705 * 1.75)
    targets = [{
        "key": "chest_cm", "label": "Ngực", "level": 0.705,
        "target_cm": perimeter * 1.50, "width_cm": 30.0, "depth_cm": 20.0,
    }]
    with pytest.raises(ClothingOrArmMergedError) as exc:
        fit_measurement_targets(mesh, targets, 175)
    assert exc.value.code == "CLOTHING_OR_ARM_MERGED"
    assert "mặc đồ rộng" in str(exc.value)
    assert exc.value.factor == pytest.approx(1.50, abs=0.01)


def test_cross_view_warning_threshold_is_15_percent():
    frontal = _observation(height=400.0, mask_width_px=120)
    lateral_10 = _observation(height=440.0, mask_width_px=132)
    lateral_18 = _observation(height=472.0, mask_width_px=142)
    assert assess_cross_view_quality(frontal, lateral_10)["cross_view_warning"] is None
    warning = assess_cross_view_quality(frontal, lateral_18)["cross_view_warning"]
    assert warning is not None
    assert "18.0%" in warning


def test_arm_capsule_rejects_destructive_profile_removal():
    # Near arm centred on the torso axis: a full capsule would cut the torso in
    # half, so the remover must keep the original mask and warn instead.
    mask = np.zeros((300, 200), dtype=bool)
    mask[50:251, 70:131] = True
    points = np.zeros((33, 2), dtype=float)
    points[:, 0], points[:, 1] = 100, 90
    points[11], points[12] = [75, 90], [125, 90]
    points[13], points[14] = [100, 160], [100, 160]
    points[15], points[16] = [100, 230], [100, 230]
    points[23], points[24] = [80, 250], [120, 250]
    visibility = np.full(33, 0.95, dtype=float)
    removal = remove_arm_capsules(mask, points, visibility, body_height_px=300.0)
    assert removal.mask.sum() == mask.sum()
    assert any("bỏ qua" in warning for warning in removal.warnings)


def test_shoulder_span_prefers_the_silhouette_over_the_joint_centres():
    """Landmark 11/12 là tâm khớp vai, hẹp hơn vai thật ~10 cm (P01b: 28 vs 40).

    Đo trên silhouette tại hàng vai cho 38,4 cm; helper phải chọn nguồn đó.
    """
    obs = _observation(height=800.0, mask_width_px=200)
    ratio, source = shoulder_span(obs)
    assert source == "silhouette"
    assert ratio == pytest.approx(200 / 800.0, rel=1e-3)  # 0.25 * height
    assert ratio * 170.0 == pytest.approx(42.5, abs=0.1)  # cm ở người cao 170
    # Landmark của fixture chỉ rộng 100 px = 0.125 * height, tức 21 cm ở 170 cm.
    landmark_ratio = 100.0 / 800.0
    assert landmark_ratio < ratio


def test_shoulder_span_is_unavailable_when_the_row_is_unusable():
    obs = _observation(height=800.0, mask_width_px=120)
    obs.mask[:] = False  # hàng vai không còn run nào chứa tâm
    ratio, source = shoulder_span(obs)
    assert source == "unavailable"
    assert ratio is None


def test_shoulder_span_is_unavailable_for_an_implausibly_wide_row():
    # Run rộng 360/800 = 0.45 H: nghi tay giơ/che nền, phải quay về landmark.
    obs = _observation(height=800.0, mask_width_px=360)
    ratio, source = shoulder_span(obs)
    assert source == "unavailable"
    assert ratio is None

def test_frame_coverage_rejects_a_person_who_is_too_far():
    # mask cao 400 px, người cao 200 px -> 50% khung: phải bị từ chối
    obs = _observation(height=200.0, mask_width_px=120)
    coverage = frame_coverage(obs)
    assert coverage == pytest.approx(0.5, abs=1e-3)
    assert coverage < MIN_FRAME_COVERAGE
    # người chiếm 80% khung thì qua cổng
    assert frame_coverage(_observation(height=320.0, mask_width_px=120)) >= MIN_FRAME_COVERAGE

