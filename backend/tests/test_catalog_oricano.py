"""Áo thun nam Oricano: dữ liệu thật từ bảng size của hãng (dạng trải phẳng).

Khoá ba điều:
1. số đo áo (dài áo / ½ ngực / dài tay / rộng vai) được seed đúng như bảng của
   hãng, và vòng ngực áo = 2 × ½ ngực;
2. fit map dùng chính số đo phẳng đó (`basis = garment_flat_spec`) và trả
   `no_garment_data` cho eo/hông thay vì bịa;
3. bảng vòng cơ thể trong catalog là **suy ra** (trừ ease), không phải số của hãng.
"""
from __future__ import annotations

import pytest

from app.db import get_product_by_slug_or_id
from app.fitmap import compute_fit_map
from app.seed import seed_catalog

SLUG = "ao-thun-oricano-nam"
HALF_CHEST = {"S": 41.0, "M": 43.0, "L": 45.0, "XL": 47.0, "XXL": 49.0}
LENGTH = {"S": 61.0, "M": 63.0, "L": 65.0, "XL": 67.0, "XXL": 69.0}
SLEEVE = {"S": 17.0, "M": 18.0, "L": 19.0, "XL": 20.0, "XXL": 21.0}
SHOULDER = {"S": 38.0, "M": 39.0, "L": 40.0, "XL": 41.0, "XXL": 42.0}


@pytest.fixture
def oricano(tmp_path) -> dict:
    db_file = tmp_path / "oricano.db"
    seed_catalog(db_file)
    product = get_product_by_slug_or_id(SLUG, db_file)
    assert product is not None, "sản phẩm Oricano chưa được seed"
    return product


def test_seeded_specs_match_the_brand_sheet(oricano):
    specs = {item["size"]: item for item in oricano["garment_specs"]}
    assert list(specs) == ["S", "M", "L", "XL", "XXL"]
    for size, half in HALF_CHEST.items():
        assert specs[size]["chest_flat_cm"] == pytest.approx(half)
        assert specs[size]["chest_cm"] == pytest.approx(half * 2)
        assert specs[size]["length_cm"] == pytest.approx(LENGTH[size])
        assert specs[size]["sleeve_cm"] == pytest.approx(SLEEVE[size])
        assert specs[size]["shoulder_cm"] == pytest.approx(SHOULDER[size])


def test_fit_map_uses_the_flat_spec_for_chest(oricano):
    fit = compute_fit_map(oricano, "M", {"chest_cm": 82.0, "waist_cm": 70.0})
    chest = next(region for region in fit["regions"] if region["key"] == "chest_cm")
    assert chest["status"] == "estimated"
    assert chest["basis"] == "garment_flat_spec"
    assert chest["garment_estimate_cm"] == pytest.approx(86.0)  # 2 x 43
    assert chest["ease_cm"] == pytest.approx(4.0)
    assert fit["confidence"] == "published_garment_spec"
    assert fit["heatmap"]["mode"] == "continuous_vertex"
    assert fit["heatmap"]["garment_length_cm"] == pytest.approx(63.0)


def test_fit_map_refuses_to_invent_waist_and_hip(oricano):
    fit = compute_fit_map(oricano, "M", {"chest_cm": 82.0, "waist_cm": 70.0, "hip_cm": 95.0})
    regions = {region["key"]: region for region in fit["regions"]}
    assert regions["waist_cm"]["status"] == "no_garment_data"
    assert regions["waist_cm"]["verdict"] == "unknown"


def test_body_rows_never_claim_the_garment_size(oricano):
    rows = {row["size"]: row for row in oricano["chart"]["rows"]}
    specs = {item["size"]: item for item in oricano["garment_specs"]}
    for size, row in rows.items():
        assert row["chest_cm"]["max"] < specs[size]["chest_cm"]
        assert row["waist_cm"]["max"] < row["chest_cm"]["max"]
    assert "suy ra" in oricano["chart"]["name"].lower()


def test_every_size_has_a_variant_so_it_can_be_tried(oricano):
    sizes = {variant["size"] for variant in oricano["variants"] if variant.get("is_active", 1)}
    assert sizes == set(HALF_CHEST)
    assert oricano["image"].endswith("ao-thun-oricano-nam.jpg")
