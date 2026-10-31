"""Flat-schema garment fit for DYLHEAR A03-style specs.

The garment table is flat (chest width laid flat, cm).  The full chest
circumference is ``2 x chest_flat_cm``.  The thresholds below are
**provisional** and are not calibrated against wear-test data; they exist to
make tight/snug/regular/loose/oversized explicit and testable.  This module does
not modify heatmap/BodyViewer, the anatomical k factors, or the 1.40 fit guard.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

# Temporary uncertainty model.  tape -> 0 cm; photo estimates -> 3 cm.
BODY_SOURCE_UNCERTAINTY_CM: dict[str, float] = {
    "tape": 0.0,
    "photo": 3.0,
    "photo_estimate": 3.0,
    "photo_with_prior": 3.0,
    "user_input": 0.0,
}
DEFAULT_BODY_UNCERTAINTY_CM = 3.0
DEFAULT_FLAT_TOLERANCE_CM = 1.5
DEFAULT_FIT_STYLE = "boxy"
DEFAULT_HEM_ASSUMPTION = "HPS, chưa xác minh"

# Thresholds are circumference ease (cm).  Intervals: tight <2, snug 2-8,
# regular 8-16, loose 16-24 (24 inclusive), oversized >24.
FIT_STYLE_THRESHOLDS: dict[str, dict[str, Any]] = {
    "boxy": {
        "tight_max_cm": 2.0,
        "snug_max_cm": 8.0,
        "regular_max_cm": 16.0,
        "loose_max_cm": 24.0,
        "provisional": True,
        "note": (
            "Ngưỡng tạm thời cho dáng boxy, chưa hiệu chỉnh bằng dữ liệu mặc thử; "
            "không phải khuyến nghị may đo."
        ),
    },
}

LABEL_TEXT_VI = {
    "tight": "Chật",
    "snug": "Sát",
    "regular": "Vừa",
    "loose": "Rộng",
    "oversized": "Quá rộng",
}
LABEL_COLOR = {
    "tight": "#b23a2f",
    "snug": "#c8851c",
    "regular": "#2f7a4f",
    "loose": "#2f6591",
    "oversized": "#1f4d73",
}
THRESHOLDS_NOTE = (
    "Ngưỡng fit_style là tạm thời (provisional=true), chưa hiệu chỉnh bằng "
    "dữ liệu mặc thử trên người thật."
)
SIZE_ORDER = ["S", "M", "L", "XL", "XXL"]


def load_spec(path: str | Path) -> dict:
    """Load a garment_spec.json document."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _spec_sizes(spec: Any) -> list[dict]:
    if isinstance(spec, dict) and isinstance(spec.get("sizes"), list):
        return [dict(item) for item in spec["sizes"]]
    if isinstance(spec, list):
        return [dict(item) for item in spec]
    if isinstance(spec, dict) and "size" in spec:
        return [dict(spec)]
    raise ValueError("Garment spec phải có danh sách sizes.")


def _fit_style(spec: Any) -> str:
    if isinstance(spec, dict):
        style = spec.get("fit_style")
        if not style and isinstance(spec.get("garment"), dict):
            style = spec["garment"].get("fit")
        if style:
            return str(style).strip().lower()
    return DEFAULT_FIT_STYLE


def _flat_tolerance_cm(spec: Any) -> float:
    if isinstance(spec, dict):
        explicit = spec.get("flat_tolerance_cm")
        if explicit is not None:
            return abs(float(explicit))
        tolerance = spec.get("tolerance_cm")
        if isinstance(tolerance, (int, float)):
            return abs(float(tolerance))
        garment = spec.get("garment")
        if isinstance(garment, dict) and isinstance(garment.get("tolerance_cm"), dict):
            values = [abs(float(v)) for v in garment["tolerance_cm"].values() if isinstance(v, (int, float))]
            if values:
                return max(values)
    return DEFAULT_FLAT_TOLERANCE_CM


def _measurement_point_assumption(spec: Any) -> str:
    if isinstance(spec, dict) and spec.get("measurement_point_assumption"):
        return str(spec["measurement_point_assumption"])
    return "rộng áo phẳng giả định đo ngang ngực, chưa xác minh"


def _hem_assumption(spec: Any) -> str:
    if isinstance(spec, dict) and spec.get("length_measurement_point"):
        return str(spec["length_measurement_point"])
    return DEFAULT_HEM_ASSUMPTION


def thresholds_for_style(fit_style: str | None) -> dict[str, Any]:
    style = (fit_style or DEFAULT_FIT_STYLE).strip().lower()
    return FIT_STYLE_THRESHOLDS.get(style, FIT_STYLE_THRESHOLDS[DEFAULT_FIT_STYLE])


def label_for_ease(ease_cm: float, fit_style: str | None = None) -> str:
    """Map circumference ease to tight/snug/regular/loose/oversized."""
    thresholds = thresholds_for_style(fit_style)
    if ease_cm < thresholds["tight_max_cm"]:
        return "tight"
    if ease_cm < thresholds["snug_max_cm"]:
        return "snug"
    if ease_cm < thresholds["regular_max_cm"]:
        return "regular"
    if ease_cm <= thresholds["loose_max_cm"]:
        return "loose"
    return "oversized"


def _threshold_values(thresholds: dict[str, Any]) -> list[float]:
    return [
        float(thresholds["tight_max_cm"]),
        float(thresholds["snug_max_cm"]),
        float(thresholds["regular_max_cm"]),
        float(thresholds["loose_max_cm"]),
    ]


def _nearest_threshold(ease_cm: float, thresholds: dict[str, Any]) -> tuple[float, float]:
    values = _threshold_values(thresholds)
    nearest = min(values, key=lambda value: (abs(ease_cm - value), value))
    return odd_round(nearest), odd_round(abs(ease_cm - nearest))


def odd_round(value: float) -> float:
    """One-decimal rounding used for the public JSON payload."""
    return round(float(value), 1)


def uncertainty_cm(body_source: str, flat_tolerance_cm: float) -> tuple[float, float]:
    """Return (garment circumference tolerance, combined uncertainty) in cm."""
    garment_tolerance = 2.0 * float(flat_tolerance_cm)
    body_uncertainty = BODY_SOURCE_UNCERTAINTY_CM.get(
        (body_source or "photo").strip().lower(), DEFAULT_BODY_UNCERTAINTY_CM
    )
    combined = math.sqrt(garment_tolerance ** 2 + body_uncertainty ** 2)
    return garment_tolerance, combined


def compute_chest_fit(body_chest_cm: float, body_source: str, spec: Any) -> dict:
    """Compute chest ease for every size in a flat garment spec.

    ``body_source`` is ``"tape"`` (body_unc=0) or ``"photo"`` (body_unc=3 cm,
    temporary config).  Each size returns ``ease_cm = 2*chest_flat_cm -
    body_chest_cm``, the provisional label, ``uncertainty_cm`` and
    ``is_borderline`` (distance to the nearest threshold < uncertainty).
    """
    body = float(body_chest_cm)
    if not math.isfinite(body) or body <= 0:
        raise ValueError("body_chest_cm phải > 0.")
    sizes = _spec_sizes(spec)
    style = _fit_style(spec)
    thresholds = thresholds_for_style(style)
    flat_tolerance = _flat_tolerance_cm(spec)
    garment_tolerance, combined_unc = uncertainty_cm(body_source, flat_tolerance)
    assumption = _measurement_point_assumption(spec)
    hem_assumption = _hem_assumption(spec)
    garment_unverified = "chưa xác minh" in assumption.lower()
    body_source_norm = (body_source or "photo").strip().lower()
    body_unverified = body_source_norm != "tape"
    unverified = bool(garment_unverified or body_unverified)

    rows = []
    for item in sizes:
        if item.get("chest_flat_cm") is None:
            raise ValueError(f"Size {item.get('size')} thiếu chest_flat_cm.")
        flat = float(item["chest_flat_cm"])
        circumference = 2.0 * flat
        ease = circumference - body
        label = label_for_ease(ease, style)
        nearest, distance = _nearest_threshold(ease, thresholds)
        rows.append({
            "size": item.get("size"),
            "chest_flat_cm": odd_round(flat),
            "chest_circumference_cm": odd_round(circumference),
            "length_cm": item.get("length_cm"),
            "hem_height_cm_from_shoulder": item.get("length_cm"),
            "hem_measurement_point": hem_assumption,
            "ease_cm": odd_round(ease),
            "label": label,
            "label_text": LABEL_TEXT_VI[label],
            "color": LABEL_COLOR[label],
            "uncertainty_cm": odd_round(combined_unc),
            "is_borderline": bool(distance < combined_unc),
            "nearest_threshold_cm": nearest,
            "distance_to_threshold_cm": distance,
            "unverified": unverified,
        })
    return {
        "body_chest_cm": odd_round(body),
        "body_source": body_source_norm,
        "body_uncertainty_cm": odd_round(
            BODY_SOURCE_UNCERTAINTY_CM.get(body_source_norm, DEFAULT_BODY_UNCERTAINTY_CM)
        ),
        "fit_style": style,
        "thresholds_cm": {
            "tight_max_cm": thresholds["tight_max_cm"],
            "snug_max_cm": thresholds["snug_max_cm"],
            "regular_max_cm": thresholds["regular_max_cm"],
            "loose_max_cm": thresholds["loose_max_cm"],
        },
        "thresholds_provisional": bool(thresholds["provisional"]),
        "thresholds_note": thresholds["note"],
        "garment_tolerance_cm": odd_round(garment_tolerance),
        "uncertainty_cm": odd_round(combined_unc),
        "measurement_point_assumption": assumption,
        "unverified": unverified,
        "sizes": rows,
    }


def _regular_bounds(fit_result: dict) -> tuple[float, float]:
    thresholds = fit_result["thresholds_cm"]
    return float(thresholds["snug_max_cm"]), float(thresholds["regular_max_cm"])


def _distance_to_regular(row: dict, regular_min: float, regular_max: float) -> float:
    ease = float(row["ease_cm"])
    if regular_min <= ease <= regular_max:
        return 0.0
    return min(abs(ease - regular_min), abs(ease - regular_max))


def _closest_row(rows: list[dict], regular_min: float, regular_max: float) -> dict:
    center = (regular_min + regular_max) / 2.0
    return min(
        rows,
        key=lambda row: (
            _distance_to_regular(row, regular_min, regular_max),
            abs(float(row["ease_cm"]) - center),
            SIZE_ORDER.index(row["size"]) if row["size"] in SIZE_ORDER else 99,
        ),
    )


def recommend_by_ease(fit_result: dict) -> dict:
    """Pick the size whose ease is nearest the regular band [8, 16] cm.

    ``closest_by_ease`` is always present, including when no size is
    tight/snug/regular; ``size`` remains None in that case.
    """
    rows = fit_result["sizes"]
    regular_min, regular_max = _regular_bounds(fit_result)
    closest = _closest_row(rows, regular_min, regular_max)
    closest_payload = {
        "size": closest["size"],
        "ease_cm": closest["ease_cm"],
        "label": closest["label"],
        "distance_to_regular_cm": odd_round(_distance_to_regular(closest, regular_min, regular_max)),
    }
    eligible = [row for row in rows if row["label"] in {"tight", "snug", "regular"}]
    if not eligible:
        labels = {row["label"] for row in rows}
        if labels <= {"loose", "oversized"}:
            return {
                "status": "all_sizes_wide",
                "size": None,
                "sizes": [row["size"] for row in rows],
                "closest_by_ease": closest_payload,
                "message": "Mọi size đều rộng theo ease hiện tại.",
            }
        return {
            "status": "no_eligible_size",
            "size": None,
            "sizes": [row["size"] for row in rows],
            "closest_by_ease": closest_payload,
            "message": "Mọi size đều chật hoặc sát theo ease hiện tại.",
        }

    chosen = _closest_row(eligible, regular_min, regular_max)
    return {
        "status": "ok",
        "size": chosen["size"],
        "ease_cm": chosen["ease_cm"],
        "label": chosen["label"],
        "distance_to_regular_cm": odd_round(_distance_to_regular(chosen, regular_min, regular_max)),
        "eligible_sizes": [row["size"] for row in eligible],
        "closest_by_ease": closest_payload,
        "message": f"Ease gần vùng regular nhất ở size {chosen['size']}.",
    }


def recommend_by_height_weight(height_cm: float | None, weight_kg: float | None, spec: Any) -> dict:
    """Match the supplied height/weight bands, accepting overlapping bands."""
    if height_cm is None:
        return {"status": "no_height", "size": None, "sizes": [], "message": "Thiếu chiều cao."}
    height = float(height_cm)
    weight = None if weight_kg is None else float(weight_kg)
    matches = []
    for item in _spec_sizes(spec):
        height_range = item.get("body_height_range_cm")
        if not height_range or len(height_range) != 2:
            continue
        if not (float(height_range[0]) <= height <= float(height_range[1])):
            continue
        weight_range = item.get("body_weight_range_kg")
        if weight is not None and weight_range and len(weight_range) == 2:
            if not (float(weight_range[0]) <= weight <= float(weight_range[1])):
                continue
        matches.append(item.get("size"))
    if not matches:
        return {"status": "no_match", "size": None, "sizes": [], "message": "Không có size khớp bảng cao/cân."}
    if len(matches) == 1:
        return {"status": "ok", "size": matches[0], "sizes": matches,
                "message": f"Bảng cao/cân gợi ý size {matches[0]}."}
    return {"status": "ambiguous", "size": None, "sizes": matches,
            "message": "Khoảng cao/cân chồng lấn: " + ", ".join(str(size) for size in matches) + "."}


def recommend_size(
    body_chest_cm: float,
    body_source: str,
    height_cm: float | None,
    weight_kg: float | None,
    spec: Any,
    clothing_looseness_flag: bool = False,
) -> dict:
    """Return both recommendations and an explicit conflict flag; never choose blindly.

    Photo-derived body measurements are refused when ``clothing_looseness_flag``
    is true: the result has status ``unreliable_body_measurement`` and no fit
    labels, because a loose top or arm merged into the torso cannot be trusted.
    """
    body_source_norm = (body_source or "photo").strip().lower()
    if body_source_norm.startswith("photo") and clothing_looseness_flag:
        return {
            "status": "unreliable_body_measurement",
            "body_chest_cm": odd_round(float(body_chest_cm)),
            "body_source": body_source_norm,
            "clothing_looseness_flag": True,
            "message": (
                "Cơ thể được đo từ ảnh nhưng ảnh có áo rộng hoặc tay dính thân; "
                "hãy mặc đồ ôm và tách tay khỏi người rồi quét lại."
            ),
            "by_ease": None,
            "by_height_weight": None,
            "closest_by_ease": None,
            "unverified": True,
            "notes": [THRESHOLDS_NOTE],
        }

    fit_result = compute_chest_fit(body_chest_cm, body_source, spec)
    by_ease = recommend_by_ease(fit_result)
    by_height_weight = recommend_by_height_weight(height_cm, weight_kg, spec)
    hw_sizes = by_height_weight.get("sizes") or (
        [by_height_weight["size"]] if by_height_weight.get("size") else []
    )
    conflict = False
    reason = None
    if by_ease["status"] == "ok" and hw_sizes:
        if by_ease["size"] not in hw_sizes:
            conflict = True
            reason = (
                f"Ease gợi ý {by_ease['size']} nhưng bảng cao/cân gợi ý "
                + ", ".join(str(size) for size in hw_sizes) + "."
            )
    elif by_ease["status"] != "ok" and hw_sizes:
        conflict = True
        reason = (
            f"Ease: {by_ease['message']} Bảng cao/cân gợi ý "
            + ", ".join(str(size) for size in hw_sizes) + "."
        )
    elif by_ease["status"] == "ok" and not hw_sizes:
        reason = "Bảng cao/cân không có size khớp; chỉ có gợi ý theo ease."
    return {
        "status": "ok",
        "body_chest_cm": fit_result["body_chest_cm"],
        "body_source": fit_result["body_source"],
        "clothing_looseness_flag": bool(clothing_looseness_flag),
        "fit": fit_result,
        "by_ease": by_ease,
        "closest_by_ease": by_ease["closest_by_ease"],
        "by_height_weight": by_height_weight,
        "conflict": conflict,
        "conflict_reason": reason,
        "unverified": fit_result["unverified"],
        "notes": [THRESHOLDS_NOTE],
    }
