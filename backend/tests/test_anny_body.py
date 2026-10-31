"""The Anny basis is a modelling prior: frame, scale and sex/weight effects."""
import numpy as np
import pytest

from app import anny_body
from app.measurements import closed_torso_section, estimate_from_profiles, fit_measurement_targets, validate_glb_mesh

pytestmark = pytest.mark.skipif(
    not anny_body.available()[0], reason="Anny basis chưa được tạo (verification/scripts/build_anny_bases.py)"
)


def test_basis_metadata_keeps_attribution():
    info = anny_body.describe()
    assert info["available"] is True
    assert info["name"] == "Anny"
    assert "Apache" in info["license"] and "CC0" in info["license"]
    assert info["vertex_count"] > 13000


def test_mesh_frame_is_metres_feet_at_floor_and_centred():
    mesh = anny_body.build("female", 0.5, 0.45, 172.0)
    assert mesh.extents[1] == pytest.approx(1.72, abs=1e-3)
    assert mesh.bounds[0, 1] == pytest.approx(0.0, abs=1e-4)
    assert abs(mesh.bounds[0, 0] + mesh.bounds[1, 0]) < 1e-3
    assert np.isfinite(mesh.vertices).all()


def test_weight_prior_widens_the_waist():
    for sex in ("female", "male"):
        light = closed_torso_section(anny_body.build(sex, 0.30, 0.45, 170.0), 0.60 * 1.7)[0]
        heavy = closed_torso_section(anny_body.build(sex, 0.70, 0.45, 170.0), 0.60 * 1.7)[0]
        assert heavy > light + 2.0


def test_sex_prior_changes_geometry():
    female = anny_body.build("female", 0.5, 0.45, 170.0).vertices
    male = anny_body.build("male", 0.5, 0.45, 170.0).vertices
    assert female.shape == male.shape
    assert np.abs(female - male).max() > 0.005


def test_phenotype_mapping_is_bounded():
    assert anny_body.phenotype_from_measurements({"waist_cm": 60}, 170.0)[0] == pytest.approx(0.30)
    assert anny_body.phenotype_from_measurements({"waist_cm": 110}, 170.0)[0] == pytest.approx(0.70)
    assert anny_body.phenotype_from_measurements({}, 170.0)[0] == pytest.approx(0.50)


def test_fit_reimposes_measurements_on_the_anny_base():
    fractions = np.linspace(0.12, 1.12, 35)
    taper = 1.0 - 0.18 * np.sin(np.clip((fractions - 0.12) / 1.0, 0, 1) * np.pi)
    widths, depths = 0.20 * taper, 0.14 * taper
    measurements, targets = estimate_from_profiles(fractions, widths, depths, 170.0, 0.24, True, 0.805, 0.534)
    mesh = anny_body.build("female", 0.5, 0.45, 170.0)
    fitted, body = fit_measurement_targets(mesh, targets, 170.0)
    assert body["fit_status"] == "matched"
    assert body["max_fit_error_cm"] <= 0.05
    assert validate_glb_mesh(fitted, 170.0, body["sections"])["valid"] is True


def test_missing_assets_are_reported_not_crashing(monkeypatch, tmp_path):
    monkeypatch.setattr(anny_body, "BASES_PATH", tmp_path / "missing.npz")
    monkeypatch.setattr(anny_body, "META_PATH", tmp_path / "missing.json")
    available, message = anny_body.available()
    assert available is False
    assert "build_anny_bases" in message
