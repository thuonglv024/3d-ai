import numpy as np
import pytest

from app.measurements import closed_torso_section, fit_measurement_targets
from app.reconstruction import read_template


@pytest.mark.parametrize(
    "height_cm,factors",
    [
        (175.0, (1.04, .96, 1.03)),
        (162.0, (1.06, .94, 1.05)),
        (172.0, (1.10, .90, 1.08)),
    ],
)
def test_smooth_fit_keeps_all_three_girths_within_half_cm(height_cm, factors):
    mesh = read_template()
    mesh.apply_scale(height_cm / 100)
    targets = []
    for key, level, factor in zip(("chest_cm", "waist_cm", "hip_cm"), (.72, .60, .533), factors):
        perimeter, curve = closed_torso_section(mesh, level * height_cm / 100)
        targets.append({
            "key": key,
            "label": key,
            "level": level,
            "target_cm": perimeter * factor,
            "width_cm": float(np.ptp(curve[:, 0]) * 100),
            "depth_cm": float(np.ptp(curve[:, 2]) * 100),
        })

    _, profile = fit_measurement_targets(mesh, targets, height_cm, fit_mode="smooth")

    assert profile["fit_mode"] == "smooth"
    assert profile["fit_iterations"] <= 12
    assert profile["max_fit_error_cm"] <= .5
    for section in profile["sections"]:
        assert abs(section["model_cm"] - section["target_cm"]) <= .5
