"""LangGraph workflow for the experimental AI vision scan.

The graph has four explicit nodes so the wiring and the deterministic
validation can be tested without calling a model:

    analyze -> validate -> calibrate -> finalize

``analyze`` fires three role-differentiated Gemini calls concurrently
(asyncio.gather) while the MediaPipe geometric estimator runs on the same two
photos in a worker thread - the whole fan-out costs about one call's wall
time. ``validate`` refuses implausible member values, aggregates the members
(median + dispersion) and fuses the geometric estimate. ``calibrate`` applies
bias correction, the anthropometric prior blend and cross-metric consistency
checks. ``finalize`` packages the response with full provenance.
"""

from __future__ import annotations

import asyncio
import math
import statistics
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .ensemble import (
    MEMBER_ROLES,
    aggregate_members,
    fuse_geometric,
    gather_members,
    member_summaries,
    worst_pose_quality,
)
from .geometry import run_geometric_estimate
from .metrics import CORE_METRICS, METRICS  # re-exported for service/router use
from .priors import apply_bias_correction, apply_prior, consistency_checks
from .schemas import VisionMeasurementEstimate

METRIC_KEYS = tuple(metric[0] for metric in METRICS)


class AiScanState(TypedDict, total=False):
    front_data_url: str
    side_data_url: str
    front_bytes: bytes
    side_bytes: bytes
    height_cm: float
    capture_mode: str
    sex: str
    model_name: str
    member_results: list[dict[str, Any]]
    member_count: int
    member_meta: list[dict[str, Any]]
    geo_result: dict[str, Any]
    values: dict[str, float | None]
    metric_confidence: dict[str, float]
    support: dict[str, int]
    dispersion: dict[str, float]
    estimated_by: dict[str, str]
    confidence: float
    shape_confidence: float
    pose_quality: str
    notes: str
    warnings: list[str]
    result: dict[str, Any]


def validate_estimate(state: dict[str, Any]) -> dict[str, Any]:
    """Validate one member's raw estimate; reject impossible values."""
    estimate = VisionMeasurementEstimate.model_validate(state.get("estimate") or {})
    height_cm = float(state.get("height_cm") or 0)
    capture_mode = state.get("capture_mode") or "upper_body"
    warnings: list[str] = []
    values: dict[str, float | None] = {}

    for key, label, low, high in METRICS:
        raw = getattr(estimate, key)
        if raw is None:
            values[key] = None
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            values[key] = None
            warnings.append(f"AI trả về {label} không phải số hợp lệ; đã bỏ qua.")
            continue
        if not math.isfinite(value) or value < low or value > high:
            values[key] = None
            warnings.append(
                f"AI trả về {label} ngoài khoảng hợp lệ ({low:.0f}–{high:.0f} cm); đã bỏ qua."
            )
            continue
        values[key] = round(value, 1)

    if capture_mode == "upper_body":
        if any(values.get(key) is not None for key in ("hip_cm", "hip_width_cm", "hip_depth_cm")):
            warnings.append(
                "Chế độ thân trên không ước lượng vòng mông hoặc hình khối hông; các giá trị đó đã bị bỏ."
            )
        for key in ("hip_cm", "hip_width_cm", "hip_depth_cm"):
            values[key] = None

    # Cross-measurement sanity checks: warn, do not rewrite the model output.
    chest = values.get("chest_cm")
    waist = values.get("waist_cm")
    if chest is not None and waist is not None and waist > chest + 5:
        warnings.append("Vòng eo ước lượng lớn hơn vòng ngực; kết quả có thể chưa chính xác.")

    from .metrics import RATIO_BOUNDS

    if height_cm > 0:
        for key, label, _low, _high in METRICS:
            value = values.get(key)
            if value is None:
                continue
            low_ratio, high_ratio = RATIO_BOUNDS[key]
            ratio = value / height_cm
            if not low_ratio <= ratio <= high_ratio:
                warnings.append(
                    f"{label} ước lượng lệch nhiều so với chiều cao đã nhập; "
                    "hãy kiểm tra lại ảnh và chiều cao."
                )

    if all(values.get(key) is None for key in CORE_METRICS):
        warnings.append("AI không ước lượng được số đo nào từ hai ảnh.")

    warnings.extend(_cross_check_shape(values))

    confidence = float(min(max(estimate.confidence, 0.0), 1.0))
    if estimate.pose_quality == "poor":
        confidence = min(confidence, 0.45)
    if capture_mode == "upper_body" and values.get("hip_cm") is None:
        confidence = min(confidence, 0.85)
    if warnings:
        confidence = min(confidence, 0.65)

    # Per-metric confidence only survives for metrics that are still set.
    metric_confidence = {
        key: float(value)
        for key, value in (estimate.metric_confidence or {}).items()
        if values.get(key) is not None and math.isfinite(float(value))
    }

    return {
        "values": values,
        "metric_confidence": metric_confidence,
        "confidence": round(confidence, 2),
        "shape_confidence": round(float(min(max(estimate.shape_confidence, 0.0), 1.0)), 2),
        "pose_quality": estimate.pose_quality,
        "clothing_fit": estimate.clothing_fit,
        "notes": (estimate.notes or "").strip(),
        "warnings": warnings,
    }


def _cross_check_shape(values: dict[str, float | None]) -> list[str]:
    """Warn when a circumference contradicts the AI's own width/depth pair."""
    from ..measurements import ANATOMICAL_SECTION_FACTORS, ellipse_perimeter

    CROSS_CHECK_SECTIONS = (
        ("chest_cm", "chest_width_cm", "chest_depth_cm", "Vòng ngực"),
        ("waist_cm", "waist_width_cm", "waist_depth_cm", "Vòng eo"),
        ("hip_cm", "hip_width_cm", "hip_depth_cm", "Vòng mông"),
    )
    CROSS_CHECK_TOLERANCE = 0.08
    warnings: list[str] = []
    for circ_key, width_key, depth_key, label in CROSS_CHECK_SECTIONS:
        circumference = values.get(circ_key)
        width = values.get(width_key)
        depth = values.get(depth_key)
        if circumference is None or width is None or depth is None:
            continue
        try:
            expected = ellipse_perimeter(width, depth) * ANATOMICAL_SECTION_FACTORS.get(circ_key, 1.0)
        except Exception:  # noqa: BLE001 - invalid geometry is reported as a warning
            continue
        if abs(expected - circumference) / max(circumference, 1.0) > CROSS_CHECK_TOLERANCE:
            warnings.append(
                f"{label}: chu vi và cặp ngang/sâu AI trả về lệch quá "
                f"{CROSS_CHECK_TOLERANCE * 100:.0f}%; nên xem lại kết quả."
            )
    return warnings


async def analyze(state: AiScanState, model: Any, roles: tuple[str, ...]) -> dict[str, Any]:
    """Fire all ensemble members and the geometric estimator concurrently."""
    members_task = gather_members(model, state, roles)
    geo_task = asyncio.to_thread(
        run_geometric_estimate,
        state.get("front_bytes"),
        state.get("side_bytes"),
        float(state.get("height_cm") or 0),
        state.get("capture_mode") or "upper_body",
    )
    member_results, geo_result = await asyncio.gather(members_task, geo_task)
    return {
        "member_results": member_results,
        "member_count": len(roles),
        "geo_result": geo_result,
    }


def validate(state: AiScanState) -> dict[str, Any]:
    """Validate every member, aggregate the medians, fuse the geometry."""
    member_results = state.get("member_results") or []
    validated: list[dict[str, Any]] = []
    for member in member_results:
        if member.get("error"):
            validated.append(member)
            continue
        outcome = validate_estimate(
            {
                "height_cm": state.get("height_cm") or 0,
                "capture_mode": state.get("capture_mode") or "upper_body",
                "estimate": member.get("estimate") or {},
            }
        )
        validated.append({**member, **outcome})

    member_count = int(state.get("member_count") or len(member_results) or 1)
    aggregated = aggregate_members(validated, member_count)
    fused = fuse_geometric(aggregated, state.get("geo_result"))

    shape_confidences = [
        float(member.get("shape_confidence") or 0.0)
        for member in validated
        if not member.get("error")
    ]
    meta = []
    for member in validated:
        values = member.get("values") or {}
        meta.append({
            "role": member.get("role", ""),
            "label": member.get("label", ""),
            "confidence": member.get("confidence"),
            "supported_metrics": sum(1 for key in CORE_METRICS if values.get(key) is not None),
            "error": member.get("error"),
            "pose_quality": member.get("pose_quality"),
            "shape_confidence": member.get("shape_confidence"),
            "notes": member.get("notes") or "",
        })
    member_warnings: list[str] = []
    for member in validated:
        member_warnings.extend(member.get("warnings") or [])

    return {
        **fused,
        "shape_confidence": round(statistics.median(shape_confidences), 2) if shape_confidences else 0.0,
        "pose_quality": worst_pose_quality(validated),
        "member_meta": meta,
        "member_warnings": member_warnings,
    }


def calibrate(state: AiScanState) -> dict[str, Any]:
    """Bias correction, plausibility guard, optional prior shrink, consistency.

    The guard never rewrites a measurement: it lowers that metric's confidence
    and adds a warning. Values are only moved toward the prior when the
    operator opts in via ``MORPH_AI_PRIOR_SHRINK=1``, and every moved value is
    reported as ``before -> after`` and marked ``ensemble+prior``.
    """
    values = dict(state.get("values") or {})
    metric_confidence = dict(state.get("metric_confidence") or {})
    estimated_by = dict(state.get("estimated_by") or {})
    warnings = list(state.get("warnings") or [])
    warnings.extend(state.get("member_warnings") or [])
    sex = state.get("sex") or "auto"
    height_cm = float(state.get("height_cm") or 0)

    corrected = apply_bias_correction(values)
    outcome = apply_prior(corrected, metric_confidence, height_cm, sex)
    warnings.extend(outcome.warnings)
    for key, cap in outcome.confidence_caps.items():
        current = float(metric_confidence.get(key, 0.5))
        metric_confidence[key] = round(min(current, cap), 2)
    for key in outcome.adjustments:
        if estimated_by.get(key):
            estimated_by[key] = "ensemble+prior"
    warnings.extend(consistency_checks(outcome.values, sex))

    confidence = float(state.get("confidence") or 0.0)
    pose = state.get("pose_quality") or "fair"
    if pose == "poor":
        confidence = min(confidence, 0.45)
    if (state.get("capture_mode") or "") == "upper_body" and outcome.values.get("hip_cm") is None:
        confidence = min(confidence, 0.85)
    if warnings:
        confidence = min(confidence, 0.65)

    return {
        "values": outcome.values,
        "metric_confidence": metric_confidence,
        "estimated_by": estimated_by,
        "warnings": warnings,
        "confidence": round(confidence, 2),
    }


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _pick_notes(meta: list[dict[str, Any]]) -> str:
    for entry in meta:
        if entry.get("role") == "audit" and entry.get("notes"):
            return entry["notes"]
    for entry in meta:
        if entry.get("notes"):
            return entry["notes"]
    return ""


def finalize(state: AiScanState) -> dict[str, Any]:
    """Build the API payload with explicit AI provenance."""
    values = state.get("values") or {}
    capture_mode = state.get("capture_mode") or "upper_body"
    metric_confidence = state.get("metric_confidence") or {}
    support = state.get("support") or {}
    estimated_by = state.get("estimated_by") or {}
    details = []
    for key, label, _low, _high in METRICS:
        display_label = label
        if key == "hip_cm" and capture_mode == "upper_body":
            display_label = "Vòng mông (không ước lượng ở chế độ thân trên)"
        details.append(
            {
                "key": key,
                "label": display_label,
                "value_cm": values.get(key),
                "source": "ai_vision_estimate",
                "confidence": metric_confidence.get(key),
                "support": support.get(key),
                "estimated_by": estimated_by.get(key) if values.get(key) is not None else None,
            }
        )

    geo = state.get("geo_result") or {}
    meta = state.get("member_meta") or []
    return {
        "result": {
            "status": "completed",
            "provider": "google-genai",
            "model": state.get("model_name", ""),
            "capture_mode": capture_mode,
            "sex": state.get("sex") or "auto",
            "measurements": {
                "height_cm": float(state.get("height_cm") or 0),
                **{key: values.get(key) for key in METRIC_KEYS},
            },
            "details": details,
            "confidence": float(state.get("confidence") or 0.0),
            "shape_confidence": float(state.get("shape_confidence") or 0.0),
            "pose_quality": state.get("pose_quality") or "fair",
            "notes": _pick_notes(meta),
            "warnings": _unique(list(state.get("warnings") or [])),
            "source": "ai_vision_estimate",
            "ensemble": {
                "size": int(state.get("member_count") or len(meta)),
                "members": member_summaries(meta),
                "geometric_available": bool(geo.get("available")),
            },
            "geometric_check": {
                "available": bool(geo.get("available")),
                "reason": str(geo.get("reason") or ""),
                "measurements": dict(geo.get("measurements") or {}),
                "warnings": list(geo.get("warnings") or []),
            },
        }
    }


def build_graph(model: Any, model_name: str, roles: tuple[str, ...] = MEMBER_ROLES):
    """Compile the analyze -> validate -> calibrate -> finalize workflow."""

    async def analyze_node(state: AiScanState) -> dict[str, Any]:
        return await analyze(state, model, roles)

    workflow = StateGraph(AiScanState)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("validate", validate)
    workflow.add_node("calibrate", calibrate)
    workflow.add_node("finalize", finalize)
    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "validate")
    workflow.add_edge("validate", "calibrate")
    workflow.add_edge("calibrate", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()
