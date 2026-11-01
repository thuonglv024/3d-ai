import numpy as np
import pytest
from app.reconstruction import ENGINE, align_mask_width, center_run_width, deform_template, read_template, segmentation_mask, smooth_avatar
from app.measurements import closed_torso_section, fit_measurement_targets
from app.images import InvalidPhoto


def test_mask_width_is_padded_to_multiple_of_four():
    for width in (798, 799, 800, 801, 802, 803, 804, 805):
        image = np.zeros((40, width, 3), dtype=np.uint8)
        aligned = align_mask_width(image)
        assert aligned.shape[0] == 40
        assert aligned.shape[1] % 4 == 0
        assert aligned.shape[1] >= width
        assert np.array_equal(aligned[:, :width], image)


@pytest.mark.parametrize("channel_axis", [False, True])
def test_mediapipe_mask_versions_produce_same_2d_silhouette(channel_axis):
    raw = np.zeros((12, 8), dtype=np.float32)
    raw[2:10, 3:6] = 0.9
    mask = segmentation_mask(raw[:, :, None] if channel_axis else raw)
    assert mask.shape == (12, 8)
    assert mask.dtype == bool
    yy, xx = np.where(mask)
    assert (yy.min(), yy.max(), xx.min(), xx.max()) == (2, 9, 3, 5)


def test_unexpected_multichannel_mask_is_rejected():
    with pytest.raises(InvalidPhoto):
        segmentation_mask(np.zeros((12, 8, 3)))


def test_torso_run_excludes_separated_arms():
    mask = np.zeros((10, 100), dtype=bool)
    mask[:, 5:15] = True
    mask[:, 30:65] = True
    mask[:, 85:95] = True
    assert center_run_width(mask, 5, 48) == 35


def test_mesh_changes_with_actual_width_and_depth_and_preserves_height():
    mesh = read_template()
    fractions = np.linspace(0.12, 1.12, 35)
    widths = np.full(35, 0.20)
    depths = np.full(35, 0.14)
    first = deform_template(mesh, fractions, widths, depths, 175)
    second = deform_template(mesh, fractions, widths * 1.12, depths * 1.15, 175)
    assert np.isfinite(first.vertices).all()
    assert first.extents[1] == pytest.approx(1.75)
    assert first.faces.shape == second.faces.shape
    assert not np.allclose(first.vertices, second.vertices)
    torso = (first.vertices[:, 1] > 0.95) & (first.vertices[:, 1] < 1.30)
    assert np.ptp(second.vertices[torso, 2]) > np.ptp(first.vertices[torso, 2])
    exported = first.export(file_type="glb")
    assert exported[:4] == b"glTF"


def test_arm_lateral_shift_when_torso_widens():
    mesh = read_template()
    fractions = np.linspace(0.12, 1.12, 35)
    widths = np.full(35, 0.20)
    depths = np.full(35, 0.14)
    normal = deform_template(mesh, fractions, widths, depths, 175)
    wider = deform_template(mesh, fractions, widths * 1.25, depths, 175)
    assert wider.extents[0] > normal.extents[0]


def test_reconstruct_end_to_end_upper_body_provenance_and_glb_validation(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import trimesh
    from app.reconstruction import reconstruct

    def make_detector_result(shoulder_half_x: float, mask_half_w: int):
        # Mốc giữ đúng tỉ lệ mô hình: crown 35px, vai 196,4px, hông 436,4px
        # (đầu–vai 0,195 H, vai–hông 0,290 H với H=827,6px) để qua cổng thang đo.
        pts = [SimpleNamespace(x=0.5, y=0.14, visibility=0.95) for _ in range(33)]
        for idx, x, y in [
            (11, 0.5 - shoulder_half_x, 0.409),
            (12, 0.5 + shoulder_half_x, 0.409),
            (23, 0.43, 0.909),
            (24, 0.57, 0.909),
        ]:
            pts[idx] = SimpleNamespace(x=x, y=y, visibility=0.95)
        for idx in range(25, 33):
            pts[idx] = SimpleNamespace(x=0.5, y=1.35, visibility=0.1)
        mask = np.zeros((480, 640), dtype=np.float32)
        mask[35:475, 320 - mask_half_w : 320 + mask_half_w] = 0.95
        return SimpleNamespace(
            pose_landmarks=[pts],
            segmentation_masks=[SimpleNamespace(numpy_view=lambda: mask)],
        )

    calls = [make_detector_result(0.15, 88), make_detector_result(0.03, 62)]
    fake_detector = SimpleNamespace(detect=lambda _: calls.pop(0))
    monkeypatch.setattr("app.reconstruction.get_detector", lambda: fake_detector)

    front_img = np.full((480, 640, 3), 140, dtype=np.uint8)
    side_img = np.full((480, 640, 3), 145, dtype=np.uint8)
    glb_path = tmp_path / "avatar_upper.glb"
    stages = []

    warnings, measurements, profile = reconstruct(
        front_img, side_img, 172.0, glb_path, stages.append, capture_mode="upper_body"
    )

    assert glb_path.is_file()
    assert glb_path.read_bytes()[:4] == b"glTF"
    loaded = trimesh.load(glb_path, force="mesh")
    assert loaded.extents[1] == pytest.approx(1.72, abs=0.015)

    # Strict upper_body guards
    assert measurements["hip_cm"] is None
    assert measurements["inseam_cm"] is None
    assert measurements["chest_cm"] > 70.0
    # Fixture nghiêng có bề dày không đổi giữa các mốc (tay/nền che) nên eo phải
    # bị từ chối kèm lý do, không trả một con số sai.
    assert measurements["waist_cm"] is None
    assert profile["waist_unavailable_reason"]

    # Profile diagnostics & mesh validation
    assert profile["engine_version"] == ENGINE
    assert profile["uncertainty_cm"] is None
    assert profile["mesh_validation"]["valid"] is True
    assert profile["mesh_validation"]["unit"] == "m"
    diag = profile["quality_diagnostics"]
    assert diag["detector_confidence_front"] > 0.8
    assert diag["detector_confidence_side"] > 0.8
    assert diag["height_scale_px"] > 0
    assert "trang phục" in diag["clothing_silhouette_note"]

    # Check hip_cm in measurement_details is strictly template_model and not valid for sizing/tracking
    details = {d["key"]: d for d in profile["measurement_details"]}
    assert details["hip_cm"]["source"] == "template_model"
    assert details["hip_cm"]["valid_for_sizing"] is False
    assert details["hip_cm"]["valid_for_tracking"] is False
    assert details["chest_cm"]["source"] == "photo_with_prior"
    assert details["chest_cm"]["valid_for_sizing"] is True


def test_sensitivity_to_imperfect_side_standing_angle():
    """Evaluate circumference sensitivity when user stands at 75 deg instead of 90 deg."""
    from app.measurements import estimate_from_profiles

    fractions = np.linspace(0.12, 1.12, 35)
    w_true = np.full(35, 0.19)
    d_true = np.full(35, 0.135)
    m_90, _ = estimate_from_profiles(fractions, w_true, d_true, 170.0, 0.22)

    # At 75 degrees yaw (15 deg off 90), apparent depth of an elliptical torso is sqrt((W cos 75)^2 + (D sin 75)^2)
    theta = np.deg2rad(75.0)
    d_75 = np.sqrt((w_true * np.cos(theta)) ** 2 + (d_true * np.sin(theta)) ** 2)
    m_75, _ = estimate_from_profiles(fractions, w_true, d_75, 170.0, 0.22)

    # 15-degree rotation error causes only a small, bounded circumference shift (< 1.5 cm)
    assert 0.0 < (m_75["chest_cm"] - m_90["chest_cm"]) < 1.5


def _smooth_targets(mesh, height_cm):
    targets = []
    for key, level, factor in (("chest_cm", .72, 1.04), ("waist_cm", .60, .96), ("hip_cm", .533, 1.03)):
        perimeter, curve = closed_torso_section(mesh, level * height_cm / 100)
        targets.append({
            "key": key,
            "label": key,
            "level": level,
            "target_cm": perimeter * factor,
            "width_cm": float(np.ptp(curve[:, 0]) * 100),
            "depth_cm": float(np.ptp(curve[:, 2]) * 100),
        })
    return targets


def test_smooth_avatar_preserves_height_floor_and_girths():
    mesh = read_template()
    mesh.apply_scale(1.75)
    targets = _smooth_targets(mesh, 175.0)
    fitted, _ = fit_measurement_targets(mesh, targets, 175.0)
    smoothed, profile = smooth_avatar(fitted, targets, 175.0)

    if profile is None:
        # Rollback path: an unchanged mesh is returned with the caller's profile.
        assert np.allclose(smoothed.vertices, fitted.vertices)
        return
    assert profile["max_fit_error_cm"] <= .5
    assert abs(smoothed.extents[1] - 1.75) <= .015
    assert abs(smoothed.vertices[:, 1].min()) < 1e-6


def test_smooth_avatar_rolls_back_when_girths_move_too_far():
    mesh = read_template()
    mesh.apply_scale(1.75)
    targets = _smooth_targets(mesh, 175.0)
    fitted, _ = fit_measurement_targets(mesh, targets, 175.0)
    bad = [dict(t, target_cm=t["target_cm"] + 20.0) for t in targets]

    rolled, profile = smooth_avatar(fitted, bad, 175.0)

    assert profile is None
    assert np.allclose(rolled.vertices, fitted.vertices)
