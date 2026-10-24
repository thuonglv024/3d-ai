"""Secondary rings follow the three measured rings with documented coefficients."""
import numpy as np
import pytest

from app import anny_body, proportions
from app.measurements import closed_torso_section

pytestmark = pytest.mark.skipif(not anny_body.available()[0], reason="Anny basis chưa được tạo")

H = 1.70
LEVELS = {
    "chest": (0.72, None),
    "waist": (0.62, None),
    "hip": (0.50, None),
    "neck": (0.855, None),
    "thigh": (0.405, 0.055),
    "calf": (0.235, 0.06),
    "ankle": (0.065, 0.06),
}


def ring(mesh, level, cx=None):
    return closed_torso_section(mesh, level * H, center_x_m=cx * H if cx else None)[0]


def test_ring_scales_follow_driver_and_are_clamped():
    scales = proportions.ring_scales({"chest_cm": 90, "hip_cm": 95}, {"chest_cm": 99, "hip_cm": 95})
    assert scales["neck_cm"] == pytest.approx(1 + 0.35 * 0.10)
    assert scales["thigh_cm"] == pytest.approx(1.0)
    huge = proportions.ring_scales({"chest_cm": 90, "hip_cm": 95}, {"chest_cm": 300, "hip_cm": 95})
    assert huge["neck_cm"] == pytest.approx(proportions.MAX_SCALE)


def test_apply_rings_scales_secondary_rings_without_touching_main_rings():
    mesh = anny_body.build("female", 0.5, 0.45, H * 100)
    before = {key: ring(mesh, level, cx) for key, (level, cx) in LEVELS.items()}
    scales = {"neck_cm": 1.05, "thigh_cm": 1.08, "calf_cm": 1.04, "ankle_cm": 1.02}
    applied = proportions.apply_rings(mesh, scales, H)
    assert set(applied) == set(scales)

    for key in ("chest", "waist", "hip"):
        assert ring(mesh, LEVELS[key][0], LEVELS[key][1]) == pytest.approx(before[key], abs=0.5)

    assert ring(mesh, 0.855) / before["neck"] == pytest.approx(1.05, abs=0.005)
    assert ring(mesh, 0.405, 0.055) / before["thigh"] == pytest.approx(1.08, abs=0.005)
    assert ring(mesh, 0.235, 0.06) / before["calf"] == pytest.approx(1.04, abs=0.005)
    assert ring(mesh, 0.065, 0.06) / before["ankle"] == pytest.approx(1.02, abs=0.005)
    assert np.isfinite(mesh.vertices).all()


def test_wider_chest_and_hip_produce_larger_secondary_rings():
    mesh = anny_body.build("male", 0.5, 0.45, H * 100)
    base = {key: ring(mesh, level, cx) for key, (level, cx) in LEVELS.items()}
    base_mains = {"chest_cm": base["chest"], "waist_cm": base["waist"], "hip_cm": base["hip"]}
    scales = proportions.ring_scales(base_mains, {"chest_cm": base["chest"] * 1.08, "waist_cm": base["waist"], "hip_cm": base["hip"] * 1.06})
    assert scales["neck_cm"] > 1.0 and scales["thigh_cm"] > 1.0
    proportions.apply_rings(mesh, scales, H)
    assert ring(mesh, 0.855) > base["neck"]
    assert ring(mesh, 0.405, 0.055) > base["thigh"]


def test_field_mode_uses_one_continuous_scale_and_bands_flag_still_works():
    mesh = anny_body.build("female", 0.5, 0.45, H * 100)
    before = {key: ring(mesh, level, cx) for key, (level, cx) in LEVELS.items()}
    scales = {"neck_cm": 1.05, "thigh_cm": 1.08, "calf_cm": 1.04, "ankle_cm": 1.02}

    fielded = mesh.copy()
    assert set(proportions.apply_rings(fielded, scales, H, mode="field")) == set(scales)
    for key, level, cx, expected in (
        ("neck", .855, None, 1.05),
        ("thigh", .405, .055, 1.08),
        ("calf", .235, .06, 1.04),
        ("ankle", .065, .06, 1.02),
    ):
        actual = ring(fielded, level, cx)
        assert abs(actual - before[key] * expected) <= .5
        assert actual / before[key] == pytest.approx(expected, abs=.01)

    # Both legs use the same mirrored centre and therefore the same factor.
    left = ring(fielded, .405, .055) / before["thigh"]
    right = ring(fielded, .405, -.055) / ring(mesh, .405, -.055)
    assert left == pytest.approx(right, abs=.01)

    banded = mesh.copy()
    assert set(proportions.apply_rings(banded, scales, H, mode="bands")) == set(scales)
    assert ring(banded, .405, .055) / before["thigh"] == pytest.approx(1.08, abs=.01)


def test_describe_exposes_coefficients_for_the_scan_profile():
    described = {item["key"]: item for item in proportions.describe({"neck_cm": 1.03})}
    assert described["neck_cm"]["driver"] == "chest_cm"
    assert described["neck_cm"]["coefficient"] == 0.35
    assert described["neck_cm"]["scale"] == pytest.approx(1.03)
