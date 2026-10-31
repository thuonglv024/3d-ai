"""Tests for the deterministic layers of the AI scan: ensemble, geometry fusion,
prior guard and prompt contract.

No network calls and no Gemini key: every test uses fake members or hand-built
inputs, so a green run says the arithmetic and the provenance rules hold, not
that the vision model is accurate. Accuracy needs tape-measured subjects.
"""

from __future__ import annotations

import asyncio

import pytest

from app.ai_scan import ensemble

from app.ai_scan.ensemble import aggregate_members, fuse_geometric
from app.ai_scan.geometry import run_geometric_estimate
from app.ai_scan.graph import calibrate
from app.ai_scan.priors import (
    EXTREME_CONFIDENCE_CAP,
    LOW_DENSITY_CONFIDENCE_CAP,
    SHRINK_ENV,
    apply_bias_correction,
    apply_prior,
    consistency_checks,
    shrink_enabled,
)
from app.ai_scan.prompts import ROLE_ADDENDA, SYSTEM_PROMPT, build_user_prompt


def member(role: str = "anchor", conf: float = 0.8, **values: float | None) -> dict:
    """One already-validated ensemble member."""
    return {
        "role": role,
        "label": role,
        "values": dict(values),
        "metric_confidence": {key: conf for key, value in values.items() if value is not None},
    }


def aggregated(conf: float = 0.5, **values: float | None) -> dict:
    keys = ("chest_cm", "waist_cm", "hip_cm", "shoulder_width_cm")
    return {
        "values": {key: values.get(key) for key in keys},
        "metric_confidence": {key: conf for key in keys},
        "support": {key: (1 if values.get(key) is not None else 0) for key in keys},
        "dispersion": {key: 0.0 for key in keys},
        "confidence": conf,
        "warnings": [],
    }


def calibrate_state(**overrides) -> dict:
    state = {
        "values": {"chest_cm": 96.0, "waist_cm": 78.0},
        "metric_confidence": {"chest_cm": 0.5, "waist_cm": 0.5},
        "estimated_by": {"chest_cm": "ensemble", "waist_cm": "ensemble"},
        "confidence": 0.8,
        "pose_quality": "good",
        "capture_mode": "full_body",
        "sex": "auto",
        "height_cm": 170.0,
        "warnings": [],
    }
    state.update(overrides)
    return state


# --- prior layer -----------------------------------------------------------


def test_prior_is_off_unless_the_operator_opts_in(monkeypatch):
    monkeypatch.delenv(SHRINK_ENV, raising=False)
    assert shrink_enabled() is False
    outcome = apply_prior({"chest_cm": 96.0}, {"chest_cm": 0.5}, 170.0, "auto")
    assert outcome.values["chest_cm"] == 96.0
    assert outcome.adjustments == {}
    assert outcome.warnings == []


def test_prior_shrink_reports_before_and_after(monkeypatch):
    monkeypatch.setenv(SHRINK_ENV, "1")
    outcome = apply_prior({"chest_cm": 96.0}, {"chest_cm": 0.5}, 170.0, "auto")
    assert outcome.values["chest_cm"] == 94.8
    assert outcome.adjustments["chest_cm"] == (96.0, 94.8)
    assert any("96.0 -> 94.8" in warning for warning in outcome.warnings)


def test_prior_guard_keeps_a_normal_value_untouched():
    outcome = apply_prior({"chest_cm": 96.0}, {"chest_cm": 0.5}, 170.0, "auto")
    assert outcome.values["chest_cm"] == 96.0
    assert outcome.confidence_caps == {}
    assert outcome.warnings == []


def test_prior_guard_flags_rare_value_without_rewriting_it():
    # female 170 cm: prior mean 92.65, sd 7.65 -> 115.6 cm is z = 3.0
    outcome = apply_prior({"chest_cm": 115.6}, {"chest_cm": 0.9}, 170.0, "female")
    assert outcome.values["chest_cm"] == 115.6
    assert outcome.confidence_caps["chest_cm"] == LOW_DENSITY_CONFIDENCE_CAP
    assert len(outcome.warnings) == 1


def test_prior_guard_caps_confidence_harder_at_extreme_z():
    # 170 + 5 sd -> z = 5.0
    outcome = apply_prior({"chest_cm": 130.9}, {"chest_cm": 0.9}, 170.0, "female")
    assert outcome.values["chest_cm"] == 130.9
    assert outcome.confidence_caps["chest_cm"] == EXTREME_CONFIDENCE_CAP


def test_bias_correction_is_identity_until_calibrated():
    values = {"chest_cm": 96.0, "waist_cm": 78.0}
    assert apply_bias_correction(values) == values


def test_hip_and_waist_ratio_warnings_are_sex_aware():
    assert any("mông nhỏ hơn" in w for w in consistency_checks({"chest_cm": 100.0, "hip_cm": 80.0}, "female")[:1])
    assert consistency_checks({"chest_cm": 100.0, "hip_cm": 96.0}, "female") == []
    assert any("eo lớn hơn" in w for w in consistency_checks({"waist_cm": 100.0, "hip_cm": 90.0}, "auto"))
    assert consistency_checks({"waist_cm": 80.0, "hip_cm": 90.0}, "auto") == []


def test_shoulder_contradiction_warning_only_when_shoulder_is_too_narrow():
    assert any(
        "Rộng vai nhỏ hơn" in w
        for w in consistency_checks({"shoulder_width_cm": 25.0, "chest_width_cm": 40.0}, "auto")
    )
    assert consistency_checks({"shoulder_width_cm": 39.0, "chest_width_cm": 30.0}, "auto") == []


# --- calibrate node --------------------------------------------------------


def test_calibrate_passes_values_through_when_shrink_is_off(monkeypatch):
    monkeypatch.delenv(SHRINK_ENV, raising=False)
    out = calibrate(calibrate_state())
    assert out["values"]["chest_cm"] == 96.0
    assert out["estimated_by"]["chest_cm"] == "ensemble"
    assert out["warnings"] == []


def test_calibrate_marks_prior_adjusted_metrics(monkeypatch):
    monkeypatch.setenv(SHRINK_ENV, "1")
    out = calibrate(calibrate_state())
    assert out["values"]["chest_cm"] == 94.8
    assert out["estimated_by"]["chest_cm"] == "ensemble+prior"
    assert any("->" in warning for warning in out["warnings"])


def test_calibrate_lowers_per_metric_confidence_on_a_rare_value():
    out = calibrate(
        calibrate_state(
            values={"chest_cm": 115.6},
            metric_confidence={"chest_cm": 0.9},
            estimated_by={"chest_cm": "ensemble"},
            sex="female",
        )
    )
    assert out["values"]["chest_cm"] == 115.6
    assert out["metric_confidence"]["chest_cm"] == LOW_DENSITY_CONFIDENCE_CAP


def test_calibrate_caps_global_confidence_when_any_warning_exists():
    out = calibrate(calibrate_state(values={"chest_cm": 115.6}, sex="female", confidence=0.95))
    assert out["confidence"] <= 0.65


# --- ensemble aggregation --------------------------------------------------


def test_aggregate_takes_the_median_and_penalises_dispersion():
    out = aggregate_members(
        [
            member("anchor", 0.8, chest_cm=90.0),
            member("shape", 0.8, chest_cm=96.0),
            member("audit", 0.8, chest_cm=110.0),
        ],
        3,
    )
    assert out["values"]["chest_cm"] == 96.0
    assert out["dispersion"]["chest_cm"] == 20.0
    assert out["metric_confidence"]["chest_cm"] <= 0.6
    assert any("lệch nhau" in warning for warning in out["warnings"])


def test_aggregate_penalises_a_metric_only_one_member_could_see():
    out = aggregate_members(
        [
            member("anchor", 0.8, chest_cm=96.0, waist_cm=78.0),
            member("shape", 0.8, chest_cm=96.0),
            member("audit", 0.8, chest_cm=96.0),
        ],
        3,
    )
    assert out["values"]["waist_cm"] == 78.0
    assert out["support"]["waist_cm"] == 1
    assert out["metric_confidence"]["waist_cm"] <= 0.45
    assert any("1/3" in warning for warning in out["warnings"])


def test_aggregate_survives_a_failed_member():
    out = aggregate_members(
        [
            {"role": "anchor", "error": "timeout"},
            member("shape", 0.8, chest_cm=96.0),
            member("audit", 0.8, chest_cm=98.0),
        ],
        3,
    )
    assert out["values"]["chest_cm"] == 97.0
    assert out["support"]["chest_cm"] == 2
    assert out["metric_confidence"]["chest_cm"] <= 0.7


# --- geometry fusion -------------------------------------------------------


def test_fusion_blends_when_two_or_more_passes_agree():
    agg = aggregated(chest_cm=100.0)
    agg["support"]["chest_cm"] = 2
    out = fuse_geometric(
        agg,
        {"available": True, "measurements": {"chest_cm": 102.0}, "warnings": []},
    )
    assert out["values"]["chest_cm"] == 100.6
    assert out["metric_confidence"]["chest_cm"] == 0.55
    assert out["estimated_by"]["chest_cm"] == "ensemble+geometry"


def test_fusion_never_moves_a_single_ai_pass_towards_geometry():
    """1 lượt AI: hình học đã biết lệch nên chỉ được dùng làm cổng, không trộn."""
    out = fuse_geometric(
        aggregated(chest_cm=100.0),  # support = 1
        {"available": True, "measurements": {"chest_cm": 102.0}, "warnings": []},
    )
    assert out["values"]["chest_cm"] == 100.0
    assert out["estimated_by"]["chest_cm"] == "ensemble"


def test_fusion_keeps_the_ai_value_and_reports_a_conflict():
    out = fuse_geometric(
        aggregated(chest_cm=100.0),
        {"available": True, "measurements": {"chest_cm": 110.0}, "warnings": []},
    )
    assert out["values"]["chest_cm"] == 100.0
    assert out["metric_confidence"]["chest_cm"] <= 0.55
    assert out["estimated_by"]["chest_cm"] == "ensemble"
    assert any("100.0" in w and "110.0" in w for w in out["warnings"])


def test_fusion_adopts_geometry_when_the_ai_returned_nothing():
    out = fuse_geometric(
        aggregated(),
        {"available": True, "measurements": {"chest_cm": 95.0}, "warnings": []},
    )
    assert out["values"]["chest_cm"] == 95.0
    assert out["metric_confidence"]["chest_cm"] == 0.5
    assert out["estimated_by"]["chest_cm"] == "geometry"


def test_geometric_estimator_contains_a_bad_photo_instead_of_raising():
    out = run_geometric_estimate(b"\x00\x00", b"\x00\x00", 170.0, "full_body")
    assert out["available"] is False
    assert out["reason"]


# --- prompt contract -------------------------------------------------------


def test_system_prompt_states_the_scale_and_clothing_rules():
    assert "head length" in SYSTEM_PROMPT
    assert "clothing_fit" in SYSTEM_PROMPT


def test_user_prompt_carries_sex_mode_and_role():
    prompt = build_user_prompt(170.0, "upper_body", "female", "audit")
    assert "female" in prompt
    assert "upper_body" in prompt
    assert ROLE_ADDENDA["audit"] in prompt


def test_each_role_gets_a_different_addendum():
    assert len(set(ROLE_ADDENDA.values())) == len(ROLE_ADDENDA) == 3


def test_structured_output_can_be_skipped_with_env(monkeypatch):
    """MORPH_AI_STRUCTURED=0: đi thẳng JSON để khỏi chờ 45 s structured rồi mới fallback."""
    monkeypatch.setenv("MORPH_AI_STRUCTURED", "0")

    class _Response:
        content = '{"chest_cm": 95.0, "confidence": 0.7}'

    class _Model:
        def with_structured_output(self, *_args, **_kwargs):
            raise AssertionError("không được gọi structured khi đã tắt")

        async def ainvoke(self, _messages):
            return _Response()

    state = {"height_cm": 170.0, "capture_mode": "upper_body", "sex": "auto",
             "front_data_url": "data:image/png;base64,AA==", "side_data_url": "data:image/png;base64,AA=="}
    out = asyncio.run(ensemble.analyze_member(_Model(), "anchor", state))
    assert out["estimate"]["chest_cm"] == 95.0


def test_structured_budget_fits_inside_the_route_timeout():
    from app.ai_scan import config

    worst = ensemble.STRUCTURED_TIMEOUT_SECONDS + ensemble.JSON_TIMEOUT_SECONDS
    assert worst < config.REQUEST_TIMEOUT_SECONDS

