"""Tests for the continuous per-vertex fit field."""
import numpy as np
import pytest

from app.fit_field import build_heatmap_payload, color_for_ease, color_stops, compute_fit_field


SPEC_SIZE = {"size": "S", "length_cm": 63.0, "sleeve_cm": 19.0}
HEIGHT_M = 1.56
SHOULDER_M = 0.805 * HEIGHT_M
HIP_M = 0.534 * HEIGHT_M


def _vertices():
    # torso centre, near-shoulder, mid-torso, above hem, below hem, arm
    return np.array([
        [0.0, 1.25, 0.0],   # torso within the shoulder taper
        [0.0, 1.00, 0.0],   # torso mid
        [0.0, 0.70, 0.0],   # torso above hem (hip is lower)
        [0.0, 0.60, 0.0],   # below hem
        [0.30, 1.00, 0.0],  # arm (x > 0.18 * height)
    ], dtype=float)


def test_field_covers_torso_between_shoulder_and_hem_only():
    result = compute_fit_field(
        _vertices(), SPEC_SIZE, 18.0,
        shoulder_y_m=SHOULDER_M, hip_y_m=HIP_M, height_m=HEIGHT_M, fit_style="boxy",
    )
    coverage = result["coverage"]
    assert coverage[0] == 1 and coverage[1] == 1 and coverage[2] == 1
    assert coverage[3] == 0  # below hem
    assert coverage[4] == 0  # arm excluded by horizontal distance
    assert result["ease_cm"][1] == pytest.approx(18.0)
    assert result["ease_cm"][0] < 18.0  # shoulder taper
    assert result["ease_cm"][3] == 0.0


def test_colors_are_grey_without_coverage_and_continuous_with_it():
    result = compute_fit_field(
        _vertices(), SPEC_SIZE, 18.0,
        shoulder_y_m=SHOULDER_M, hip_y_m=HIP_M, height_m=HEIGHT_M, fit_style="boxy",
    )
    colors = result["colors"]
    assert tuple(colors[3]) == (201, 209, 200)  # unknown grey
    assert tuple(colors[4]) == (201, 209, 200)
    assert tuple(colors[1]) != (201, 209, 200)


def test_color_stops_and_piecewise_interpolation():
    stops = color_stops("boxy")
    assert [stop["ease_cm"] for stop in stops] == [2.0, 8.0, 16.0, 24.0, 32.0]
    assert color_for_ease(2.0, stops) == "#b23a2f"
    assert color_for_ease(8.0, stops) == "#d08a2e"
    assert color_for_ease(16.0, stops) == "#3f8f5c"
    assert color_for_ease(24.0, stops) == "#6aa6c8"
    assert color_for_ease(32.0, stops) == "#1f4d73"
    mid = color_for_ease(12.0, stops)
    assert mid.startswith("#") and mid not in {"#d08a2e", "#3f8f5c"}


def test_missing_length_means_no_garment_coverage():
    result = compute_fit_field(
        _vertices(), {"size": "S"}, 18.0,
        shoulder_y_m=SHOULDER_M, hip_y_m=HIP_M, height_m=HEIGHT_M,
    )
    assert np.all(result["coverage"] == 0)


def test_heatmap_payload_has_stops_and_unverified_hem():
    payload = build_heatmap_payload(
        "boxy", 18.0, SPEC_SIZE, unverified=True,
        length_measurement_point="HPS, chưa xác minh",
    )
    assert payload["mode"] == "continuous_vertex"
    assert payload["ease_cm"] == 18.0
    assert payload["garment_length_cm"] == 63.0
    assert payload["unverified"] is True
    assert len(payload["color_stops"]) == 5
    assert payload["coverage_legend"]["0"].startswith("xám")