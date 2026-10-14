import numpy as np
import pytest
from app.reconstruction import read_template, deform_template


def calculate_measurements(mesh, height_cm: float) -> dict[str, float]:
    import trimesh
    h_m = height_cm / 100.0

    def slice_contour_perimeter(y_val: float, max_half_width: float) -> float:
        lines = trimesh.intersections.mesh_plane(mesh, plane_normal=[0, 1, 0], plane_origin=[0, y_val, 0])
        if len(lines) == 0:
            return 0.0
        centers_x = np.abs(lines.mean(axis=1)[:, 0])
        torso_lines = lines[centers_x <= max_half_width]
        if len(torso_lines) == 0:
            return 0.0
        diff = torso_lines[:, 0, :] - torso_lines[:, 1, :]
        return float(np.sum(np.sqrt((diff ** 2).sum(axis=-1)))) * 100.0

    chest_levels = np.linspace(0.69, 0.74, 6) * h_m
    chest_perims = [slice_contour_perimeter(y, 0.22 * h_m) for y in chest_levels]
    chest_cm = round(max(chest_perims) if chest_perims else 0.0, 1)

    waist_levels = np.linspace(0.56, 0.63, 8) * h_m
    waist_perims = [slice_contour_perimeter(y, 0.20 * h_m) for y in waist_levels]
    valid_waist = [p for p in waist_perims if p > 0]
    waist_cm = round(min(valid_waist) if valid_waist else 0.0, 1)

    hip_levels = np.linspace(0.47, 0.54, 8) * h_m
    hip_perims = [slice_contour_perimeter(y, 0.26 * h_m) for y in hip_levels]
    hip_cm = round(max(hip_perims) if hip_perims else 0.0, 1)

    shoulder_lines = trimesh.intersections.mesh_plane(mesh, plane_normal=[0, 1, 0], plane_origin=[0, 0.805 * h_m, 0])
    if len(shoulder_lines) > 0:
        shoulder_pts = shoulder_lines.reshape(-1, 3)
        shoulder_width_cm = round(float(np.ptp(shoulder_pts[:, 0])) * 100.0, 1)
    else:
        shoulder_width_cm = round(0.24 * height_cm, 1)

    inseam_cm = round(0.46 * height_cm, 1)

    return {
        "height_cm": round(height_cm, 1),
        "chest_cm": chest_cm,
        "waist_cm": waist_cm,
        "hip_cm": hip_cm,
        "shoulder_width_cm": shoulder_width_cm,
        "inseam_cm": inseam_cm,
    }


def test_measurements_calculation():
    mesh = read_template()
    fractions = np.linspace(0.12, 1.12, 35)
    widths = np.full(35, 0.20)
    depths = np.full(35, 0.14)
    deformed = deform_template(mesh, fractions, widths, depths, 175)
    m = calculate_measurements(deformed, 175)
    
    assert m["height_cm"] == 175.0
    assert 70.0 < m["chest_cm"] < 120.0
    assert 60.0 < m["waist_cm"] < 110.0
    assert 75.0 < m["hip_cm"] < 130.0
    assert m["waist_cm"] < m["chest_cm"]
    assert m["waist_cm"] < m["hip_cm"]
    assert 30.0 < m["shoulder_width_cm"] < 60.0
    assert 65.0 < m["inseam_cm"] < 95.0
