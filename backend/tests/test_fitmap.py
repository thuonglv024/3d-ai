"""Fit-map estimates are labelled estimates: size-chart ranges, never flat garment specs."""
import pytest
from fastapi.testclient import TestClient

from app import main
from app.fitmap import classify, compute_fit_map, ease_allowance, is_stretch


def product(fit="Regular fit vừa vặn", material="100% Cotton", garment="top"):
    return {
        "id": "p1",
        "slug": "test-top",
        "name": "Test top",
        "fit": fit,
        "material": material,
        "chart": {
            "name": "Test chart",
            "garment": garment,
            "source": "illustrative",
            "measurement_basis": "body_cm",
            "rows": [
                {"size": "S", "chest_cm": {"min": 82, "max": 90}, "waist_cm": {"min": 66, "max": 80}, "hip_cm": {"min": 88, "max": 94}},
                {"size": "M", "chest_cm": {"min": 90, "max": 98}, "waist_cm": {"min": 74, "max": 88}, "hip_cm": {"min": 94, "max": 100}},
            ],
        },
    }


def test_ease_allowance_from_fit_text():
    assert ease_allowance("Oversized fit rộng rãi") == 14.0
    assert ease_allowance("Slim regular fit") == 4.0
    assert ease_allowance(None) == 8.0


def test_stretch_detection():
    assert is_stretch("95% Cotton, 5% Spandex")
    assert is_stretch("Vải co giãn nhẹ")
    assert not is_stretch("100% Cotton")


def test_within_range_is_regular():
    result = compute_fit_map(product(), "M", {"chest_cm": 94, "waist_cm": 80})
    chest = next(r for r in result["regions"] if r["key"] == "chest_cm")
    assert chest["verdict"] == "regular"
    assert chest["garment_estimate_cm"] == pytest.approx(102.0)
    assert chest["ease_cm"] == pytest.approx(8.0)
    assert result["overall"]["key"] == "regular"
    assert result["confidence"] == "estimated_from_size_chart"


def test_body_above_range_is_tight_and_below_is_loose():
    tight = compute_fit_map(product(), "M", {"chest_cm": 105, "waist_cm": 80})
    chest = next(r for r in tight["regions"] if r["key"] == "chest_cm")
    assert chest["verdict"] == "tight"
    assert chest["ease_cm"] < 0

    loose = compute_fit_map(product(), "M", {"chest_cm": 84, "waist_cm": 80})
    chest = next(r for r in loose["regions"] if r["key"] == "chest_cm")
    assert chest["verdict"] == "loose"
    assert chest["ease_cm"] > 6


def test_stretch_fabric_tolerates_negative_ease():
    stretch = compute_fit_map(product(fit="Slim fit", material="95% Cotton, 5% Spandex"), "M", {"chest_cm": 100, "waist_cm": 80})
    chest = next(r for r in stretch["regions"] if r["key"] == "chest_cm")
    # midpoint 94 + slim ease 4 = 98, so ease is -2 cm: snug on knit, tight on woven.
    assert chest["ease_cm"] == pytest.approx(-2.0)
    assert chest["verdict"] == "snug"
    assert stretch["stretch"] is True


def test_bottom_uses_waist_and_hip():
    result = compute_fit_map(product(garment="bottom"), "M", {"chest_cm": 94, "waist_cm": 80, "hip_cm": 98})
    assert [r["key"] for r in result["regions"]] == ["waist_cm", "hip_cm"]
    assert result["overall"]["key"] == "regular"


def test_unknown_size_and_missing_measurements_are_reported():
    missing_size = compute_fit_map(product(), "XXL", {"chest_cm": 94})
    assert missing_size["status"] == "size_not_found"
    assert "M" in missing_size["available_sizes"]

    incomplete = compute_fit_map(product(), "M", {"chest_cm": 94})
    assert incomplete["status"] == "partial"
    assert incomplete["overall"]["key"] == "regular"
    assert any(r["verdict"] == "unknown" for r in incomplete["regions"])

    empty = compute_fit_map(product(), "M", {})
    assert empty["status"] == "insufficient_measurements"
    assert empty["overall"]["key"] == "unknown"


def test_classify_thresholds():
    assert classify(-1, False) == "tight"
    assert classify(1, False) == "snug"
    assert classify(4, False) == "regular"
    assert classify(9, False) == "regular"
    assert classify(11, False) == "loose"
    assert classify(-2, True) == "snug"
    assert classify(-6, True) == "tight"


def test_published_flat_spec_overrides_the_chart_estimate():
    spec_product = product()
    spec_product["garment_specs"] = [
        {"size": "M", "chest_cm": 101.6, "length_cm": 73.7, "sleeve_cm": 43.2},
    ]
    spec_product["garment_source"] = "Gildan 5000 spec sheet"
    result = compute_fit_map(spec_product, "M", {"chest_cm": 94, "waist_cm": 80})
    chest = next(r for r in result["regions"] if r["key"] == "chest_cm")
    assert chest["basis"] == "garment_flat_spec"
    assert chest["garment_estimate_cm"] == pytest.approx(101.6)
    assert chest["ease_cm"] == pytest.approx(7.6)
    assert chest["verdict"] == "regular"
    assert result["confidence"] == "published_garment_spec"
    assert result["garment_source"] == "Gildan 5000 spec sheet"
    waist = next(r for r in result["regions"] if r["key"] == "waist_cm")
    assert waist["basis"] == "size_chart_estimate"


def test_endpoint_returns_estimate_for_a_catalog_product():
    with TestClient(main.app) as client:
        catalog = client.get("/api/products").json()
        items = catalog.get("products") if isinstance(catalog, dict) else catalog
        slug = items[0]["slug"]
        response = client.post("/api/fit-map", json={
            "product_slug": slug,
            "size": items[0]["sizes"][0],
            "measurements": {"chest_cm": 94, "waist_cm": 78, "hip_cm": 96},
        })
        assert response.status_code == 200
        payload = response.json()
        assert payload["confidence"] == "estimated_from_size_chart"
        assert payload["regions"]
