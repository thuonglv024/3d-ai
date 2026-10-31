"""Three-member concurrent AI ensemble with deterministic aggregation.

Instead of one Gemini call, the scan fires three structured-output calls at the
same time (asyncio.gather), each with a different role prompt, while the
MediaPipe geometric estimator runs in a thread. The members' values are
validated individually, then fused:

- median per metric across members (robust to one deviant member);
- dispersion between members becomes a per-metric confidence penalty and a
  user-facing warning — never a silent rewrite;
- when the geometric estimate agrees with the AI median within tolerance, the
  two are blended; when it disagrees, the conflict is reported.

A single-member failure degrades the ensemble instead of failing the request.
"""
from __future__ import annotations

import asyncio
import json
import statistics
from typing import Any

import logging

logger = logging.getLogger(__name__)

# Structured output (tool calling) is what the free tier answers 503 to.
STRUCTURED_TIMEOUT_SECONDS = 45
JSON_TIMEOUT_SECONDS = 120


def structured_enabled() -> bool:
    import os

    return os.getenv('MORPH_AI_STRUCTURED', '1').strip().lower() not in {'0', 'false', 'off'}

from langchain_core.messages import HumanMessage, SystemMessage

from .metrics import (
    CORE_METRICS,
    DISPERSION_TOLERANCE_CM,
    GEOMETRY_FUSION_TOLERANCE_CM,
    GEOMETRY_METRICS,
    METRIC_LABELS,
    METRICS,
)
from .prompts import ROLE_LABELS_VI, SYSTEM_PROMPT, build_user_prompt
from .schemas import VisionMeasurementEstimate

MEMBER_ROLES: tuple[str, ...] = ("anchor", "shape", "audit")


async def analyze_member(model: Any, role: str, state: dict[str, Any]) -> dict[str, Any]:
    """One ensemble member: one Gemini call for its role.

    Structured output (function calling) is tried first. On free tiers the model
    frequently answers 503 UNAVAILABLE to tool-calling requests with images
    while plain vision requests still work, so a failure falls back to a plain
    JSON answer parsed locally. Same schema, same prompt, different transport.
    """
    structured = None if not structured_enabled() else model.with_structured_output(VisionMeasurementEstimate)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": build_user_prompt(
                        float(state.get("height_cm") or 0),
                        state.get("capture_mode") or "upper_body",
                        state.get("sex") or "auto",
                        role,
                    ),
                },
                {"type": "text", "text": "Front view:"},
                {"type": "image_url", "image_url": {"url": state.get("front_data_url", "")}},
                {"type": "text", "text": "Side view (90 degrees):"},
                {"type": "image_url", "image_url": {"url": state.get("side_data_url", "")}},
            ]
        ),
    ]
    try:
        if structured is None:
            raise RuntimeError('MORPH_AI_STRUCTURED=0: bỏ qua structured output')
        estimate = await asyncio.wait_for(structured.ainvoke(messages), timeout=STRUCTURED_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 - transport fallback, see docstring
        logger.info("Structured call failed (%s); retrying as plain JSON", str(exc)[:120])
        estimate = await _json_fallback(model, messages, role)
    if isinstance(estimate, dict):
        estimate = VisionMeasurementEstimate.model_validate(estimate)
    return {
        "role": role,
        "label": ROLE_LABELS_VI.get(role, role),
        "estimate": estimate.model_dump(),
    }


def _schema_fields() -> list[str]:
    return list(VisionMeasurementEstimate.model_fields)


async def _json_fallback(model: Any, messages: list[Any], role: str) -> VisionMeasurementEstimate:
    """Ask for the same payload as plain JSON and parse it without tools."""
    keys = ", ".join(_schema_fields())
    instruction = (
        "Return ONE JSON object and nothing else (no markdown fence), using exactly these keys: "
        f"{keys}. Use null for any value you cannot support. Numbers are centimetres."
    )
    plain_messages = [SystemMessage(content=instruction)] + list(messages)
    response = await asyncio.wait_for(model.ainvoke(plain_messages), timeout=JSON_TIMEOUT_SECONDS)
    text = response.content if hasattr(response, "content") else str(response)
    if isinstance(text, list):  # Gemini returns content parts
        text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in text)
    cleaned = str(text).strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"{role}: model không trả JSON hợp lệ")
    payload = json.loads(cleaned[start:end + 1])
    return VisionMeasurementEstimate.model_validate(payload)


async def gather_members(model: Any, state: dict[str, Any], roles: tuple[str, ...] = MEMBER_ROLES) -> list[dict[str, Any]]:
    """Fire all member calls concurrently; failures become error entries."""
    async def one(role: str) -> dict[str, Any]:
        try:
            return await analyze_member(model, role, state)
        except Exception as exc:  # noqa: BLE001 - a failed member must not fail the scan
            return {"role": role, "label": ROLE_LABELS_VI.get(role, role), "error": str(exc)[:200]}

    return list(await asyncio.gather(*(one(role) for role in roles)))


def aggregate_members(
    validated_members: list[dict[str, Any]],
    member_count: int,
) -> dict[str, Any]:
    """Median + dispersion + per-metric confidence across validated members."""
    per_metric: dict[str, list[tuple[float, float]]] = {key: [] for key, _l, _lo, _hi in METRICS}
    for member in validated_members:
        if member.get("error"):
            continue
        values = member.get("values") or {}
        confidences = member.get("metric_confidence") or {}
        for key in per_metric:
            value = values.get(key)
            if value is None:
                continue
            per_metric[key].append((float(value), float(confidences.get(key, 0.5))))

    values: dict[str, float | None] = {}
    metric_confidence: dict[str, float] = {}
    support: dict[str, int] = {}
    dispersion: dict[str, float] = {}
    warnings: list[str] = []
    for key, label, _low, _high in METRICS:
        entries = per_metric[key]
        if not entries:
            values[key] = None
            support[key] = 0
            continue
        entries.sort()
        nums = [v for v, _c in entries]
        median = float(statistics.median(nums))
        spread = max(nums) - min(nums)
        tolerance = DISPERSION_TOLERANCE_CM.get(key, 4.0)
        confidence = float(statistics.median([c for _v, c in entries]))
        values[key] = round(median, 1)
        support[key] = len(entries)
        dispersion[key] = round(spread, 1)
        if spread > tolerance:
            confidence = min(confidence, 0.6)
            warnings.append(
                f"{label}: ba lượt AI ước lượng lệch nhau {spread:.1f} cm; độ tin cậy của số đo này bị hạ."
            )
        if member_count >= 3 and len(entries) == 1:
            confidence = min(confidence, 0.45)
            warnings.append(
                f"{label}: chỉ 1/{member_count} thành viên AI ước lượng được; số đo này chưa vững."
            )
        elif member_count >= 3 and len(entries) < member_count:
            confidence = min(confidence, 0.7)
        metric_confidence[key] = round(confidence, 2)

    core_confidences = [metric_confidence[key] for key in CORE_METRICS if values.get(key) is not None]
    global_confidence = round(sum(core_confidences) / len(core_confidences), 2) if core_confidences else 0.0
    return {
        "values": values,
        "metric_confidence": metric_confidence,
        "support": support,
        "dispersion": dispersion,
        "confidence": global_confidence,
        "warnings": warnings,
    }


def fuse_geometric(
    aggregated: dict[str, Any],
    geometric: dict[str, Any] | None,
) -> dict[str, Any]:
    """Blend the AI median with the MediaPipe geometric estimate.

    Agreement within tolerance -> weighted blend (AI 0.7 / geometry 0.3) and a
    small confidence boost. Disagreement -> keep the AI value, cap confidence
    and surface the conflict. Missing AI value -> adopt the geometric value at
    reduced confidence so a clearly measured section is not thrown away.
    """
    values = dict(aggregated["values"])
    metric_confidence = dict(aggregated["metric_confidence"])
    support = dict(aggregated["support"])
    warnings = list(aggregated["warnings"])
    estimated_by: dict[str, str] = {
        key: "ensemble" for key in values if values.get(key) is not None
    }
    if not geometric or not geometric.get("available"):
        return {**aggregated, "values": values, "metric_confidence": metric_confidence,
                "support": support, "warnings": warnings, "estimated_by": estimated_by}

    for key in GEOMETRY_METRICS:
        geo_value = (geometric.get("measurements") or {}).get(key)
        if geo_value is None:
            continue
        label = METRIC_LABELS.get(key, key)
        ai_value = values.get(key)
        if ai_value is None:
            values[key] = round(float(geo_value), 1)
            metric_confidence[key] = 0.5
            support[key] = 0
            estimated_by[key] = "geometry"
            warnings.append(
                f"{label}: AI không ước lượng được, dùng số đo hình học MediaPipe từ chính hai ảnh."
            )
            continue
        diff = abs(float(ai_value) - float(geo_value))
        tolerance = GEOMETRY_FUSION_TOLERANCE_CM.get(key, 5.0)
        if diff <= tolerance:
            if support.get(key, 0) < 2:
                # Only one model pass saw this metric: averaging it with the
                # geometric estimate would let a known-biased estimator move the
                # only AI vote. Keep the model's number; geometry stays a check.
                estimated_by[key] = "ensemble"
                continue
            values[key] = round(0.7 * float(ai_value) + 0.3 * float(geo_value), 1)
            metric_confidence[key] = min(1.0, metric_confidence.get(key, 0.5) + 0.05)
            estimated_by[key] = "ensemble+geometry"
        else:
            metric_confidence[key] = min(metric_confidence.get(key, 0.5), 0.55)
            estimated_by[key] = "ensemble"
            warnings.append(
                f"{label}: ước lượng AI ({ai_value:.1f} cm) và hình học MediaPipe "
                f"({geo_value:.1f} cm) lệch {diff:.1f} cm; giữ ước lượng AI, nên kiểm tra lại."
            )
    return {**aggregated, "values": values, "metric_confidence": metric_confidence,
            "support": support, "warnings": warnings, "estimated_by": estimated_by}


POSE_SEVERITY = {"good": 0, "fair": 1, "poor": 2}


def worst_pose_quality(validated_members: list[dict[str, Any]]) -> str:
    qualities = [
        member.get("pose_quality") or "fair"
        for member in validated_members
        if not member.get("error")
    ]
    if not qualities:
        return "fair"
    return max(qualities, key=lambda q: POSE_SEVERITY.get(q, 1))


def member_summaries(validated_members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for member in validated_members:
        if member.get("error"):
            summaries.append({
                "role": member.get("role", ""),
                "label": member.get("label", member.get("role", "")),
                "confidence": None,
                "supported_metrics": 0,
                "error": member["error"],
            })
            continue
        values = member.get("values") or {}
        summaries.append({
            "role": member.get("role", ""),
            "label": member.get("label", ""),
            "confidence": float(member.get("confidence") or 0.0),
            "supported_metrics": sum(1 for key in CORE_METRICS if values.get(key) is not None),
            "error": None,
        })
    return summaries






