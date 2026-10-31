import numpy as np
import pytest

from app.anatomy import depth_weights, resolve_sex, shape_sex
from app.reconstruction import deform_template, read_template

FRACTIONS = np.linspace(0.12, 1.12, 35)
WIDTHS = 0.20 + 0.02 * np.sin(FRACTIONS * 3.0)
DEPTHS = 0.14 + 0.01 * np.cos(FRACTIONS * 2.5)


def _slice(mesh, height_fraction: float):
    y = mesh.vertices[:, 1]
    normalised = (y - y.min()) / (y.max() - y.min())
    return mesh.vertices[np.abs(normalised - height_fraction) < 0.006]


def test_explicit_sex_choice_wins_over_inference():
    assert resolve_sex("male", {"chest_cm": 100.0, "hip_cm": 90.0}) == ("male", "user")
    assert resolve_sex("female", {"chest_cm": 80.0, "hip_cm": 110.0}) == ("female", "user")


@pytest.mark.parametrize(
    "measurements,expected",
    [
        ({"chest_cm": 84.0, "waist_cm": 66.0, "hip_cm": 96.0, "shoulder_width_cm": 37.0}, "female"),
        ({"chest_cm": 104.0, "waist_cm": 94.0, "hip_cm": 96.0, "shoulder_width_cm": 46.0}, "male"),
    ],
)
def test_auto_sex_follows_reported_proportions(measurements, expected):
    assert resolve_sex("auto", measurements, "full_body") == (expected, "auto")


def test_auto_sex_in_upper_body_uses_shoulder_and_waist_ratios():
    female = resolve_sex("auto", {"chest_cm": 88.0, "waist_cm": 66.0, "shoulder_width_cm": 37.0}, "upper_body")
    male = resolve_sex("auto", {"chest_cm": 100.0, "waist_cm": 88.0, "shoulder_width_cm": 48.0}, "upper_body")
    assert female[0] == "female"
    assert male[0] == "male"


def test_sex_shape_keeps_scale_and_moves_shoulders():
    template = read_template()
    female = shape_sex(template, "female")
    male = shape_sex(template, "male")

    assert female.extents[1] == pytest.approx(template.extents[1])
    assert female.bounds[0, 1] == pytest.approx(template.bounds[0, 1])
    assert np.ptp(_slice(male, 0.805)[:, 0]) > np.ptp(_slice(female, 0.805)[:, 0])


def test_sex_shape_uses_lateral_profile_without_cone_bumps():
    template = read_template()
    female = shape_sex(template, "female")
    male = shape_sex(template, "male")

    torso = lambda mesh, y: _slice(mesh, y)[np.abs(_slice(mesh, y)[:, 0]) < 0.12]
    # Shoulders differ, but chest/hip depth must stay identical: a Gaussian bump
    # on this mesh reads as a cone, so depth volumes are intentionally disabled.
    assert np.ptp(_slice(male, 0.805)[:, 0]) > np.ptp(_slice(female, 0.805)[:, 0])
    assert np.ptp(torso(female, 0.72)[:, 2]) == pytest.approx(np.ptp(torso(male, 0.72)[:, 2]), abs=1e-6)
    assert np.ptp(torso(female, 0.52)[:, 2]) == pytest.approx(np.ptp(torso(male, 0.52)[:, 2]), abs=1e-6)


def test_deform_template_accepts_sex_and_preserves_height():
    template = read_template()
    female = deform_template(template, FRACTIONS, WIDTHS, DEPTHS, 170.0, "female")
    male = deform_template(template, FRACTIONS, WIDTHS, DEPTHS, 170.0, "male")
    assert female.extents[1] == pytest.approx(1.70)
    assert male.extents[1] == pytest.approx(1.70)
    assert not np.allclose(female.vertices, male.vertices)


def test_depth_weights_put_chest_growth_in_front_and_hip_behind():
    chest_front, chest_back = depth_weights(np.array([0.72]))
    hip_front, hip_back = depth_weights(np.array([0.52]))
    assert chest_front[0] > chest_back[0]
    assert hip_back[0] > hip_front[0]


def test_template_joint_landmarks_match_anatomical_levels():
    from app.anatomy import template_landmarks
    from app.reconstruction import TEMPLATE_PATH

    landmarks = template_landmarks(str(TEMPLATE_PATH))
    assert landmarks["shoulder"] == pytest.approx(0.805, abs=0.01)
    assert landmarks["hip"] == pytest.approx(0.534, abs=0.02)
    assert landmarks["neck"] > landmarks["shoulder"] > landmarks["hip"]


def test_shoulder_width_target_only_moves_part_of_the_way():
    from app.anatomy import template_landmarks
    from app.measurements import closed_torso_section, estimate_from_profiles, fit_measurement_targets
    from app.reconstruction import TEMPLATE_PATH

    landmarks = template_landmarks(str(TEMPLATE_PATH))
    levels = (landmarks["shoulder"], landmarks["hip"])
    template = read_template()
    measurements, targets = estimate_from_profiles(
        FRACTIONS, WIDTHS, DEPTHS, 170.0, 0.24, True, *levels
    )
    mesh = deform_template(template, FRACTIONS, WIDTHS, DEPTHS, 170.0, "female", levels)
    _, before = closed_torso_section(mesh, levels[0] * 1.70)
    target = measurements["shoulder_width_cm"]
    fitted, _ = fit_measurement_targets(
        mesh,
        targets,
        170.0,
        [{"key": "shoulder_width_cm", "kind": "width", "level": levels[0],
          "target_cm": target, "width_cm": target, "blend": 0.6}],
    )
    _, after = closed_torso_section(fitted, levels[0] * 1.70)
    before_cm, after_cm = np.ptp(before[:, 0]) * 100, np.ptp(after[:, 0]) * 100
    assert after_cm < before_cm
    assert target - 0.5 <= after_cm <= before_cm - 0.6 * (before_cm - target) + 0.5
