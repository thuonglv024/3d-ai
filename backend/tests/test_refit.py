"""User-corrected measurements rebuild the avatar and change their provenance."""
import numpy as np
import pytest
import trimesh
from fastapi.testclient import TestClient

from app import main
from app.anny_body import available as anny_available
from app.measurements import closed_torso_section, estimate_from_profiles
from app.reconstruction import ENGINE, refit_avatar

pytestmark = pytest.mark.skipif(not anny_available()[0], reason="Anny basis chưa được tạo")


def _fitting():
    fractions = np.linspace(0.12, 1.12, 35)
    taper = 1.0 - 0.18 * np.sin(np.clip((fractions - 0.12) / 1.0, 0, 1) * np.pi)
    widths, depths = 0.20 * taper, 0.14 * taper
    measurements, targets = estimate_from_profiles(fractions, widths, depths, 170.0, 0.24, True, 0.805, 0.534)
    fitting = {
        "sex": "female",
        "sex_source": "user",
        "capture_mode": "full_body",
        "height_cm": 170.0,
        "body_model": "anny",
        "prior": {"weight": 0.5, "muscle": 0.45},
        "targets": targets,
        "width_targets": [],
        "levels": {"shoulder": 0.805, "hip": 0.534, "neck": 0.844},
        "fractions": fractions.tolist(),
        "widths": widths.tolist(),
        "depths": depths.tolist(),
    }
    return measurements, fitting


def test_refit_reimposes_edited_circumference_and_marks_user_input(tmp_path):
    measurements, fitting = _fitting()
    measurements = dict(measurements)
    measurements["chest_cm"] = 96.0
    destination = tmp_path / "refit.glb"
    profile = refit_avatar(fitting, measurements, {"chest_cm": 96.0}, 170.0, destination)

    chest = next(section for section in profile["sections"] if section["key"] == "chest_cm")
    assert chest["model_cm"] == pytest.approx(96.0, abs=0.05)
    assert profile["fit_status"] == "matched"
    details = {row["key"]: row for row in profile["measurement_details"]}
    assert details["chest_cm"]["source"] == "user_input"
    assert details["chest_cm"]["value_cm"] == pytest.approx(96.0)
    assert details["chest_cm"]["valid_for_sizing"] is True
    assert "nhập lại" in details["chest_cm"]["quality_warnings"][0]
    # Waist was not edited, so it keeps the photo provenance.
    assert details["waist_cm"]["source"] in {"photo_estimate", "photo_with_prior"}

    mesh = trimesh.load(destination, force="mesh")
    assert mesh.extents[1] == pytest.approx(1.70, abs=0.01)
    assert float(np.ptp(closed_torso_section(mesh, chest_level(profile))[1][:, 0])) > 0


def chest_level(profile):
    chest = next(section for section in profile["sections"] if section["key"] == "chest_cm")
    return float(np.mean(np.asarray(chest["points_m"])[:, 1]))


def test_refit_height_changes_model_height(tmp_path):
    measurements, fitting = _fitting()
    measurements = dict(measurements)
    measurements["height_cm"] = 180.0
    profile = refit_avatar(fitting, measurements, {"height_cm": 180.0}, 180.0, tmp_path / "tall.glb")
    assert profile["mesh_validation"]["actual_height_m"] == pytest.approx(1.80, abs=0.01)
    details = {row["key"]: row for row in profile["measurement_details"]}
    assert details["height_cm"]["value_cm"] == pytest.approx(180.0)
    assert details["height_cm"]["source"] == "user_input"


def test_patch_endpoint_updates_job_and_revision(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "jobs", {})

    def fake_refit(fitting, measurements, overrides, height_cm, destination):
        destination.write_bytes(b"glTF-fake-refit")
        return {
            "capture_mode": fitting["capture_mode"],
            "sections": [],
            "fit_status": "matched",
            "max_fit_error_cm": 0.0,
            "measurement_details": [],
            "levels": fitting["levels"],
            "engine_version": "test",
        }

    monkeypatch.setattr(main, "refit_avatar", fake_refit)
    main.jobs["scan1"] = main.Job(
        id="scan1",
        status="completed",
        guest_token="tok",
        measurements={"height_cm": 170.0, "chest_cm": 88.0, "waist_cm": 74.0, "hip_cm": 96.0},
        body_profile={"capture_mode": "full_body"},
        fitting={"capture_mode": "full_body", "targets": [{"key": "chest_cm", "target_cm": 88.0}], "levels": {"shoulder": 0.805, "hip": 0.534}},
        warnings=["old warning"],
    )
    with TestClient(main.app) as client:
        denied = client.patch("/api/scans/scan1/measurements", json={"chest_cm": 95.0})
        assert denied.status_code == 403

        empty = client.patch("/api/scans/scan1/measurements?guest_token=tok", json={})
        assert empty.status_code == 400

        response = client.patch("/api/scans/scan1/measurements?guest_token=tok", json={"chest_cm": 95.0})
        assert response.status_code == 200
        payload = response.json()
        assert payload["measurements"]["chest_cm"] == 95.0
        assert payload["revision"] == 1
        assert payload["overrides"] == {"chest_cm": 95.0}
        assert any("chỉnh tay" in warning for warning in payload["warnings"])
        assert (tmp_path / "scan1.glb").read_bytes() == b"glTF-fake-refit"

        missing = client.patch("/api/scans/nope/measurements?guest_token=tok", json={"chest_cm": 95.0})
        assert missing.status_code == 404
    main.jobs.clear()


def test_refit_exposes_v7_field_rings_and_legacy_band_rollback(tmp_path):
    measurements, fitting = _fitting()
    profile = refit_avatar(fitting, measurements, {}, 170.0, tmp_path / "field.glb", ring_mode="field")
    assert profile["engine_version"] == ENGINE
    assert profile["proportional_ring_mode"] == "field"
    assert profile["fit_status"] == "matched"
    assert profile["max_fit_error_cm"] <= .5
    for row in profile["measurement_details"]:
        assert row["engine_version"] == ENGINE
        assert "Mốc hông" in row["definition_note"]

    legacy = refit_avatar(fitting, measurements, {}, 170.0, tmp_path / "bands.glb", ring_mode="bands")
    assert legacy["proportional_ring_mode"] == "bands"
    assert legacy["fit_status"] == "matched"
