"""LangGraph workflow for the experimental AI vision scan.

The graph has three explicit nodes so the wiring and the deterministic
validation can be tested without calling a model:

    analyze -> validate -> finalize

Only `analyze` talks to Gemini. `validate` refuses implausible values instead of
silently keeping them, and `finalize` packages the response with provenance.
"""

from __future__ import annotations

import math
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import VisionMeasurementEstimate


class AiScanState(TypedDict, total=False):
    front_data_url: str
    side_data_url: str
    height_cm: float
    capture_mode: str
    model_name: str
    estimate: dict[str, Any]
    values: dict[str, float | None]
    confidence: float
    shape_confidence: float
    pose_quality: str
    notes: str
    warnings: list[str]
    result: dict[str, Any]


METRICS: tuple[tuple[str, str, float, float], ...] = (
    ("chest_cm", "Vòng ngực", 55.0, 190.0),
    ("waist_cm", "Vòng eo", 40.0, 190.0),
    ("hip_cm", "Vòng mông", 55.0, 200.0),
    ("shoulder_width_cm", "Rộng vai", 20.0, 80.0),
    ("chest_width_cm", "Ngang ngực", 20.0, 80.0),
    ("chest_depth_cm", "Sâu ngực", 10.0, 60.0),
    ("waist_width_cm", "Ngang eo", 15.0, 80.0),
    ("waist_depth_cm", "Sâu eo", 8.0, 60.0),
    ("hip_width_cm", "Ngang mông", 20.0, 90.0),
    ("hip_depth_cm", "Sâu mông", 10.0, 60.0),
)
CORE_METRICS = tuple(metric[0] for metric in METRICS[:4])

# Plausible value / height ratios. Outside these ranges we keep the number but
# lower confidence and surface a warning; we never fabricate a correction.
RATIO_BOUNDS: dict[str, tuple[float, float]] = {
    "chest_cm": (0.38, 0.75),
    "waist_cm": (0.28, 0.65),
    "hip_cm": (0.38, 0.72),
    "shoulder_width_cm": (0.16, 0.32),
    "chest_width_cm": (0.14, 0.35),
    "chest_depth_cm": (0.08, 0.30),
    "waist_width_cm": (0.10, 0.32),
    "waist_depth_cm": (0.06, 0.28),
    "hip_width_cm": (0.15, 0.40),
    "hip_depth_cm": (0.08, 0.32),
}

# Circumference vs breadth/depth consistency: an ellipse section must land within
# this relative band of the reported circumference after anatomical calibration.
CROSS_CHECK_TOLERANCE = 0.08
CROSS_CHECK_SECTIONS = (
    ("chest_cm", "chest_width_cm", "chest_depth_cm", "Vòng ngực"),
    ("waist_cm", "waist_width_cm", "waist_depth_cm", "Vòng eo"),
    ("hip_cm", "hip_width_cm", "hip_depth_cm", "Vòng mông"),
)


def _cross_check_shape(values: dict[str, float | None]) -> list[str]:
    """Warn when a circumference contradicts the AI's own width/depth pair."""
    from ..measurements import ANATOMICAL_SECTION_FACTORS, ellipse_perimeter

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


def validate_estimate(state: AiScanState) -> dict[str, Any]:
    """Reject impossible values, enforce capture-mode rules and add warnings."""
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

    return {
        "values": values,
        "confidence": round(confidence, 2),
        "shape_confidence": round(float(min(max(estimate.shape_confidence, 0.0), 1.0)), 2),
        "pose_quality": estimate.pose_quality,
        "notes": (estimate.notes or "").strip(),
        "warnings": warnings,
    }


def finalize(state: AiScanState) -> dict[str, Any]:
    """Build the API payload with explicit AI provenance."""
    values = state.get("values") or {}
    capture_mode = state.get("capture_mode") or "upper_body"
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
            }
        )

    return {
        "result": {
            "status": "completed",
            "provider": "google-genai",
            "model": state.get("model_name", ""),
            "capture_mode": capture_mode,
            "measurements": {
                "height_cm": float(state.get("height_cm") or 0),
                **{key: values.get(key) for key, _label, _low, _high in METRICS},
            },
            "details": details,
            "confidence": float(state.get("confidence") or 0.0),
            "shape_confidence": float(state.get("shape_confidence") or 0.0),
            "pose_quality": state.get("pose_quality") or "fair",
            "notes": state.get("notes") or "",
            "warnings": list(state.get("warnings") or []),
            "source": "ai_vision_estimate",
        }
    }


def build_graph(model: Any, model_name: str):
    """Compile the analyze -> validate -> finalize LangGraph workflow."""

    async def analyze(state: AiScanState) -> dict[str, Any]:
        structured = model.with_structured_output(VisionMeasurementEstimate)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": build_user_prompt(
                            float(state.get("height_cm") or 0),
                            state.get("capture_mode") or "upper_body",
                        ),
                    },
                    {"type": "text", "text": "Front view:"},
                    {
                        "type": "image_url",
                        "image_url": {"url": state.get("front_data_url", "")},
                    },
                    {"type": "text", "text": "Side view (90 degrees):"},
                    {
                        "type": "image_url",
                        "image_url": {"url": state.get("side_data_url", "")},
                    },
                ]
            ),
        ]
        estimate = await structured.ainvoke(messages)
        if isinstance(estimate, dict):
            estimate = VisionMeasurementEstimate.model_validate(estimate)
        return {"estimate": estimate.model_dump()}

    workflow = StateGraph(AiScanState)
    workflow.add_node("analyze", analyze)
    workflow.add_node("validate", validate_estimate)
    workflow.add_node("finalize", finalize)
    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "validate")
    workflow.add_edge("validate", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()
