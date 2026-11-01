from types import SimpleNamespace
import numpy as np
import pytest
from app.images import InvalidPhoto
from app.reconstruction import ENGINE, observe, capture_feedback, read_template
from app.report import measurement_report


class TorsoDetector:
    """Cropped frame whose lower legs are outside the image and invisible.

    The landmark geometry keeps the crown→shoulder and shoulder→hip anchors
    consistent (0,195 H and 0,290 H) so it passes the scale-agreement gate:
    crown 30px, shoulder 144px → torso 169,5px → hip 313,5px (.653 of 480).
    """
    def __init__(self, hip_y=.653):
        points=[SimpleNamespace(x=.5,y=.18,visibility=.9) for _ in range(33)]
        for i,x,y in [(11,.35,.3),(12,.65,.3),(23,.4,hip_y),(24,.6,hip_y)]:
            points[i]=SimpleNamespace(x=x,y=y,visibility=.95)
        for i in range(25,33):
            points[i]=SimpleNamespace(x=.5,y=1.4,visibility=.1)
        mask=np.zeros((480,640),dtype=np.float32)
        mask[30:479,215:425]=.95
        self.result=SimpleNamespace(pose_landmarks=[points],segmentation_masks=[SimpleNamespace(numpy_view=lambda:mask)])
    def detect(self,image):
        return self.result


def test_upper_capture_accepts_missing_feet_but_full_body_rejects():
    image=np.full((480,640,3),150,dtype=np.uint8)
    obs=observe(image,TorsoDetector(),"chính diện","upper_body")
    assert obs.capture_mode=="upper_body"
    assert obs.height==pytest.approx((.653-.3)*480/.29, abs=1.0)  # fusion ±1,4%
    with pytest.raises(InvalidPhoto):
        observe(image,TorsoDetector(),"chính diện","full_body")


def test_upper_requires_visible_waist_and_hips():
    with pytest.raises(InvalidPhoto,match="cạp quần"):
        observe(np.full((480,640,3),150,dtype=np.uint8),TorsoDetector(1.15),"chính diện","upper_body")


def test_observe_rejects_too_dark_or_overexposed_frames():
    with pytest.raises(InvalidPhoto, match="quá tối"):
        observe(np.zeros((480, 640, 3), dtype=np.uint8), TorsoDetector(), "chính diện", "upper_body")
    with pytest.raises(InvalidPhoto, match="cháy sáng"):
        observe(np.full((480, 640, 3), 252, dtype=np.uint8), TorsoDetector(), "chính diện", "upper_body")


def test_blank_upper_never_ready(monkeypatch):
    detector=SimpleNamespace(detect=lambda _:SimpleNamespace(pose_landmarks=[],segmentation_masks=[]))
    monkeypatch.setattr("app.reconstruction.get_detector",lambda:detector)
    res = capture_feedback(np.zeros((480,640,3),dtype=np.uint8),"front","upper_body")
    assert not res["ready"]
    assert "quality" in res
    assert res["quality"]["brightness"] == 0.0


def test_capture_feedback_returns_quality_diagnostics_dict(monkeypatch):
    monkeypatch.setattr("app.reconstruction.get_detector", lambda: TorsoDetector())
    frame = np.full((480, 640, 3), 140, dtype=np.uint8)
    res = capture_feedback(frame, "front", "upper_body")
    assert res["ready"] is True
    assert "quality" in res
    q = res["quality"]
    assert q["brightness"] == pytest.approx(140.0)
    assert 0.1 < q["mask_coverage"] < 0.8
    assert 0.8 < q["pose_visibility_mean"] <= 1.0
    assert q["shoulder_width_ratio"] > 0.12


def test_model_dimensions_have_provenance_and_unknown_lengths_stay_null():
    mesh=read_template();mesh.vertices*=1.75
    sections = [
        {"key": "chest_cm", "label": "Ngực", "target_cm": 96.0, "model_cm": 96.0, "fit_error_cm": 0.0, "points_m": [[0, 1.25, 0], [0, 1.25, 0]]},
        {"key": "waist_cm", "label": "Eo", "target_cm": 78.0, "model_cm": 78.0, "fit_error_cm": 0.0, "points_m": [[0, 1.05, 0], [0, 1.05, 0]]},
        {"key": "hip_cm", "label": "Mông", "target_cm": 98.0, "model_cm": 98.0, "fit_error_cm": 0.0, "points_m": [[0, 0.90, 0], [0, 0.90, 0]]},
    ]
    rows_upper = measurement_report(
        mesh,
        {"chest_cm": 96.0, "waist_cm": 78.0, "hip_cm": None, "shoulder_width_cm": 40.0},
        {"capture_mode": "upper_body", "sections": sections},
        175,
    )
    by_key_upper = {r["key"]: r for r in rows_upper}

    # Height is user_input
    assert by_key_upper["height_cm"]["source"] == "user_input"
    assert by_key_upper["height_cm"]["observed_region"] == "user_reported"
    assert by_key_upper["height_cm"]["valid_for_sizing"] is True
    assert by_key_upper["height_cm"]["valid_for_tracking"] is True

    # Upper torso metrics in upper_body mode
    for k in ("chest_cm", "waist_cm", "shoulder_width_cm"):
        assert by_key_upper[k]["source"] == "photo_with_prior"
        assert by_key_upper[k]["observed_region"] == "upper_torso_with_template_prior"
        assert by_key_upper[k]["valid_for_sizing"] is True
        assert by_key_upper[k]["valid_for_tracking"] is True

    # Hip in upper_body mode MUST be template_model and invalid for sizing/tracking
    assert by_key_upper["hip_cm"]["source"] == "template_model"
    assert by_key_upper["hip_cm"]["observed_region"] == "template_prior_unobserved"
    assert by_key_upper["hip_cm"]["valid_for_sizing"] is False
    assert by_key_upper["hip_cm"]["valid_for_tracking"] is False

    # Template-derived limbs/head/neck and unavailable lengths
    for row in rows_upper:
        assert row["engine_version"] == ENGINE
        assert row["uncertainty_cm"] is None
        assert isinstance(row["quality_warnings"], list) and len(row["quality_warnings"]) >= 1
        if row["key"] in {"head_cm", "neck_cm", "thigh_cm", "calf_cm", "ankle_cm"}:
            assert row["source"] == "template_model"
            assert row["observed_region"] == "template_prior_unobserved"
            assert row["valid_for_sizing"] is False
            assert row["valid_for_tracking"] is False
            assert row["value_cm"] > 0
            assert row["points_m"][0] == row["points_m"][-1]
        if row["key"] in {"inseam_cm", "arm_length_cm"}:
            assert row["value_cm"] is None
            assert row["source"] == "unavailable"
            assert row["observed_region"] == "unobserved"
            assert row["valid_for_sizing"] is False
            assert row["valid_for_tracking"] is False

    # Compare with full_body mode where hip_cm is observed
    rows_full = measurement_report(
        mesh,
        {"chest_cm": 96.0, "waist_cm": 78.0, "hip_cm": 98.0, "shoulder_width_cm": 40.0},
        {"capture_mode": "full_body", "sections": sections},
        175,
    )
    by_key_full = {r["key"]: r for r in rows_full}
    for k in ("chest_cm", "waist_cm", "hip_cm", "shoulder_width_cm"):
        assert by_key_full[k]["source"] == "photo_estimate"
        assert by_key_full[k]["observed_region"] == "frontal_and_lateral_torso"
        assert by_key_full[k]["valid_for_sizing"] is True
        assert by_key_full[k]["valid_for_tracking"] is True


def _observe_upper_with_torso_ratio(r_torso: float):
    """Crown→shoulder đúng 0,195 H; mỏ neo thân đổi theo ``r_torso``."""
    h, w = 600, 640
    h_true = 800.0
    top = 40
    shoulder_y = top + 0.195 * h_true
    nose_y = top + 0.070 * h_true
    hip_y = shoulder_y + r_torso * h_true
    image = np.full((h, w, 3), 150, dtype=np.uint8)

    points = [SimpleNamespace(x=0.5, y=nose_y / h, visibility=0.95) for _ in range(33)]
    for i, x, y in [
        (11, 0.35, shoulder_y / h),
        (12, 0.65, shoulder_y / h),
        (23, 0.40, hip_y / h),
        (24, 0.60, hip_y / h),
    ]:
        points[i] = SimpleNamespace(x=x, y=y, visibility=0.95)
    for i in range(25, 33):
        points[i] = SimpleNamespace(x=0.5, y=1.35, visibility=0.1)
    mask = np.zeros((h, w), dtype=np.float32)
    mask[top : h - 1, 200:440] = 0.95
    detector = SimpleNamespace(
        detect=lambda _, pts=points, m=mask: SimpleNamespace(
            pose_landmarks=[pts],
            segmentation_masks=[SimpleNamespace(numpy_view=lambda: m)],
        )
    )
    return observe(image, detector, "chính diện", "upper_body")


@pytest.mark.parametrize("r_torso", (0.26, 0.275, 0.29, 0.305, 0.32))
def test_upper_body_scale_agreement_accepts_natural_torso_ratios(r_torso):
    """Biến thiên tỉ lệ thân tự nhiên (0,26–0,32) nằm trong ngưỡng 20%.

    Synthetic đặt đúng mỏ neo đầu (0,195 H) nên chiều cao ước lượng phải sai ≤1,5%.
    """
    obs = _observe_upper_with_torso_ratio(r_torso)
    rel_error = abs(obs.height - 800.0) / 800.0
    assert rel_error < 0.015, f"r_torso={r_torso}: obs.height={obs.height:.2f} vs 800 ({rel_error*100:.2f}%)"
    if r_torso == 0.29:
        assert obs.height == pytest.approx(800.0, rel=1e-4)


@pytest.mark.parametrize("r_torso", (0.20, 0.38))
def test_upper_body_scale_agreement_rejects_beyond_tolerance(r_torso):
    """Lệch >20% thì từ chối, không lấy trung bình hai mỏ neo."""
    with pytest.raises(InvalidPhoto, match="lệch"):
        _observe_upper_with_torso_ratio(r_torso)


