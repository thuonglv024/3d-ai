"""Tests for the flat-schema garment fit module and its fitmap integration."""
from pathlib import Path

import pytest

from app.fitmap import compute_fit_map
from app.garment_fit import (
    compute_chest_fit,
    load_spec,
    recommend_by_ease,
    recommend_by_height_weight,
    recommend_size,
)

SPEC_PATH = Path(__file__).resolve().parents[1] / "data" / "pilot_selfie" / "garment_spec.json"


@pytest.fixture(scope="module")
def spec():
    return load_spec(SPEC_PATH)


def _product(garment_specs, fit="boxy"):
    return {
        "id": "a03",
        "slug": "a03",
        "name": "DYLHEAR A03",
        "fit": fit,
        "material": "cotton",
        "garment_specs": garment_specs,
        "chart": {
            "name": "A03 chart",
            "garment": "top",
            "source": "user_provided",
            "measurement_basis": "body_cm",
            "rows": [
                {"size": "S", "chest_cm": {"min": 82, "max": 90}, "waist_cm": {"min": 66, "max": 74}},
                {"size": "M", "chest_cm": {"min": 90, "max": 98}, "waist_cm": {"min": 74, "max": 82}},
            ],
        },
    }


def test_flat_width_is_doubled_for_circumference(spec):
    fit = compute_chest_fit(80, "tape", spec)
    sizes = {row["size"]: row for row in fit["sizes"]}
    assert sizes["S"]["chest_flat_cm"] == 49.0
    assert sizes["S"]["chest_circumference_cm"] == 98.0
    assert sizes["XXL"]["chest_circumference_cm"] == 114.0
    assert fit["unverified"] is True
    assert fit["thresholds_provisional"] is True


@pytest.mark.parametrize(
    "body,expected",
    [
        (80, {"S": 18, "M": 22, "L": 26}),
        (90, {"S": 8, "M": 12, "L": 16}),
        (100, {"S": -2, "M": 2, "L": 6}),
        (110, {"S": -12, "M": -8, "L": -4}),
    ],
)
def test_ease_for_body_80_90_100_110_on_sml(spec, body, expected):
    fit = compute_chest_fit(body, "tape", spec)
    sizes = {row["size"]: row for row in fit["sizes"]}
    for size, ease in expected.items():
        assert sizes[size]["ease_cm"] == pytest.approx(ease, abs=0.1)


def test_borderline_turns_on_and_off(spec):
    # Tape -> combined uncertainty sqrt(3^2 + 0^2) = 3.0 cm.
    on = compute_chest_fit(80, "tape", spec)
    sizes = {row["size"]: row for row in on["sizes"]}
    assert sizes["S"]["uncertainty_cm"] == pytest.approx(3.0)
    assert sizes["S"]["is_borderline"] is True   # 18 cm, 2 cm from 16
    assert sizes["XL"]["is_borderline"] is False  # 30 cm, 6 cm from 24
    off = compute_chest_fit(78, "tape", spec)
    off_s = {row["size"]: row for row in off["sizes"]}["S"]
    assert off_s["ease_cm"] == pytest.approx(20.0)
    assert off_s["is_borderline"] is False  # 4 cm from both 16 and 24


def test_photo_body_source_has_larger_uncertainty(spec):
    tape = compute_chest_fit(80, "tape", spec)
    photo = compute_chest_fit(80, "photo", spec)
    assert tape["uncertainty_cm"] == pytest.approx(3.0)
    assert photo["uncertainty_cm"] == pytest.approx(4.2, abs=0.05)
    assert photo["unverified"] is True


def test_size_recommendation_conflict_and_overlap(spec):
    # Body 90: ease picks M (12 cm), height 156 picks S -> conflict.
    conflict = recommend_size(90, "tape", 156, None, spec)
    assert conflict["by_ease"]["size"] == "M"
    assert conflict["by_height_weight"]["size"] == "S"
    assert conflict["conflict"] is True
    assert conflict["conflict_reason"]

    # Height 160 is in both S and M bands; ease picks M -> no conflict.
    overlap = recommend_size(90, "tape", 160, None, spec)
    assert overlap["by_height_weight"]["status"] == "ambiguous"
    assert set(overlap["by_height_weight"]["sizes"]) == {"S", "M"}
    assert overlap["by_ease"]["size"] == "M"
    assert overlap["conflict"] is False

    # The real pilot: all sizes are wide; height table says S.
    pilot = recommend_size(80, "tape", 156, None, spec)
    assert pilot["by_ease"]["status"] == "all_sizes_wide"
    assert "rộng" in pilot["by_ease"]["message"]
    assert pilot["by_height_weight"]["size"] == "S"
    assert pilot["conflict"] is True


def test_height_weight_uses_weight_when_present(spec):
    height_only = recommend_by_height_weight(160, None, spec)
    assert set(height_only["sizes"]) == {"S", "M"}
    weighted = recommend_by_height_weight(160, 50, spec)
    assert weighted["size"] == "S"


def test_hem_height_is_recorded_with_assumption(spec):
    fit = compute_chest_fit(80, "tape", spec)
    sizes = {row["size"]: row for row in fit["sizes"]}
    assert sizes["S"]["hem_height_cm_from_shoulder"] == 63.0
    assert sizes["M"]["hem_height_cm_from_shoulder"] == 65.0
    assert "HPS" in sizes["S"]["hem_measurement_point"]


def test_fitmap_uses_flat_spec_and_marks_other_regions_no_garment_data():
    product = _product([{"size": "M", "chest_flat_cm": 51.0, "length_cm": 65.0}])
    result = compute_fit_map(product, "M", {"chest_cm": 90, "waist_cm": 80})
    chest = next(r for r in result["regions"] if r["key"] == "chest_cm")
    waist = next(r for r in result["regions"] if r["key"] == "waist_cm")
    assert chest["garment_estimate_cm"] == 102.0
    assert chest["ease_cm"] == 12.0
    assert chest["fit_label"] == "regular"
    assert chest["basis"] == "garment_flat_spec"
    assert chest["unverified"] is True
    assert "uncertainty_cm" in chest and "is_borderline" in chest
    assert waist["status"] == "no_garment_data"
    assert "ease_cm" not in waist
    assert "garment_estimate_cm" not in waist
    assert result["overall"]["key"] == "regular"
    assert any("no_garment_data" in warning for warning in result["warnings"])
    assert result["heatmap"]["mode"] == "continuous_vertex"
    assert result["heatmap"]["ease_cm"] == 12.0
    assert result["heatmap"]["garment_length_cm"] == 65.0
    assert result["heatmap"]["unverified"] is True
    assert len(result["heatmap"]["color_stops"]) == 5


def test_old_flat_spec_chest_cm_keeps_old_behaviour():
    product = _product([{"size": "M", "chest_cm": 101.6}])
    result = compute_fit_map(product, "M", {"chest_cm": 94, "waist_cm": 80})
    chest = next(r for r in result["regions"] if r["key"] == "chest_cm")
    waist = next(r for r in result["regions"] if r["key"] == "waist_cm")
    assert chest["garment_estimate_cm"] == pytest.approx(101.6)
    assert chest["ease_cm"] == pytest.approx(7.6)
    assert chest["basis"] == "garment_flat_spec"
    assert "fit_label" not in chest
    assert waist["status"] == "estimated"
    assert waist["basis"] == "size_chart_estimate"
    assert result["heatmap"] is None


def test_all_sizes_wide_message_when_no_eligible_size(spec):
    fit = compute_chest_fit(80, "tape", spec)
    recommendation = recommend_by_ease(fit)
    assert recommendation["status"] == "all_sizes_wide"
    assert recommendation["size"] is None
    assert "rộng" in recommendation["message"]


def test_closest_by_ease_is_present_when_all_sizes_are_wide(spec):
    recommendation = recommend_size(80, "tape", 156, None, spec)
    assert recommendation["by_ease"]["status"] == "all_sizes_wide"
    closest = recommendation["closest_by_ease"]
    assert closest["size"] == "S"
    assert closest["ease_cm"] == pytest.approx(18.0)
    assert closest["distance_to_regular_cm"] == pytest.approx(2.0)


def test_photo_with_looseness_flag_is_unreliable_and_has_no_fit_labels(spec):
    result = recommend_size(
        80, "photo", 156, None, spec, clothing_looseness_flag=True
    )
    assert result["status"] == "unreliable_body_measurement"
    assert "mặc đồ ôm" in result["message"]
    assert result["clothing_looseness_flag"] is True
    assert "fit" not in result
    assert result["by_ease"] is None
    assert result["by_height_weight"] is None
    assert result["closest_by_ease"] is None


def test_tape_with_looseness_flag_still_returns_labels(spec):
    result = recommend_size(
        90, "tape", 160, None, spec, clothing_looseness_flag=True
    )
    assert result["status"] == "ok"
    assert result["fit"]["sizes"]
    assert result["closest_by_ease"]["size"] == "M"
