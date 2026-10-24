"""Estimated tightness/looseness per body region, from the product size chart.

This is an *estimate*, not a garment simulation. The catalog stores the body
measurement range each size is designed for (`measurement_basis = "body_cm"`),
not flat garment dimensions, so the garment circumference is approximated as the
range midpoint plus an ease allowance inferred from the product's `fit` label
(slim/regular/oversized). Each region then reports the difference between that
estimated garment circumference and the user's measured body circumference.

Nothing here changes the reported body measurements, and none of it is a
fit guarantee: real garments differ in cut, seam allowance and fabric recovery.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .sizing import SizeChart

CONFIDENCE = "estimated_from_size_chart"

# Normalised height bands used to paint the region on the 3D avatar.
REGIONS = {
    "chest_cm": {"label": "Vòng ngực", "band": (0.64, 0.79)},
    "waist_cm": {"label": "Vòng eo", "band": (0.54, 0.64)},
    "hip_cm": {"label": "Vòng mông", "band": (0.455, 0.555)},
}

# Circumference allowance (cm) the garment is assumed to add on top of the chart
# midpoint. Parsed from the free-text `fit` field, so this is a documented guess.
EASE_BY_FIT = {
    "oversized": 14.0,
    "slim": 4.0,
    "tailored": 4.0,
    "fitted": 3.0,
    "crop": 6.0,
    "loose": 12.0,
    "relaxed": 10.0,
    "boxy": 12.0,
    "comfortable": 9.0,
    "straight": 8.0,
    "regular": 8.0,
}
DEFAULT_EASE = 8.0

VERDICTS = {
    "tight": {"label": "Chật", "color": "#b23a2f"},
    "snug": {"label": "Sát", "color": "#c8851c"},
    "regular": {"label": "Vừa", "color": "#2f7a4f"},
    "loose": {"label": "Rộng", "color": "#2f6591"},
    "unknown": {"label": "Chưa đủ số đo", "color": "#8b9188"},
}
_ORDER = {"tight": 3, "snug": 2, "regular": 1, "loose": 0, "unknown": -1}


class FitMapRequest(BaseModel):
    product_id: Optional[str] = None
    product_slug: Optional[str] = None
    size: str = Field(min_length=1, max_length=20)
    measurements: dict[str, Optional[float]] = Field(default_factory=dict)


def ease_allowance(fit_text: Optional[str]) -> float:
    text = (fit_text or "").lower()
    for key, value in EASE_BY_FIT.items():
        if key in text:
            return value
    return DEFAULT_EASE


def is_stretch(material_text: Optional[str]) -> bool:
    text = (material_text or "").lower()
    return any(token in text for token in ("spandex", "elastane", "lycra", "co giãn", "đàn hồi"))


def classify(ease_cm: float, stretch: bool) -> str:
    """Map circumference ease to a verdict. Knitwear tolerates negative ease."""
    if stretch:
        if ease_cm < -5.0:
            return "tight"
        if ease_cm < 0.0:
            return "snug"
    else:
        if ease_cm < 0.0:
            return "tight"
        if ease_cm < 2.0:
            return "snug"
    if ease_cm <= 10.0:
        return "regular"
    return "loose"


def _regions_for(garment: Optional[str]) -> list[str]:
    kind = (garment or "").lower().strip()
    if kind == "bottom":
        return ["waist_cm", "hip_cm"]
    if kind == "dress":
        return ["chest_cm", "waist_cm", "hip_cm"]
    return ["chest_cm", "waist_cm"]


def compute_fit_map(product: dict, size: str, measurements: dict) -> dict:
    chart = SizeChart(**product["chart"])
    row = next((r for r in chart.rows if r.size == size), None)
    if row is None:
        return {
            "status": "size_not_found",
            "size": size,
            "available_sizes": [r.size for r in chart.rows],
            "regions": [],
            "overall": {**VERDICTS["unknown"], "key": "unknown"},
            "confidence": CONFIDENCE,
            "warnings": ["Size này không có trong bảng size của sản phẩm."],
        }

    specs = {
        str(item.get("size")): item
        for item in (product.get("garment_specs") or [])
        if isinstance(item, dict) and item.get("size")
    }
    size_spec = specs.get(size)
    stretch = is_stretch(product.get("material"))
    baseline = ease_allowance(product.get("fit"))
    regions = []
    uses_flat_spec = False
    for key in _regions_for(chart.garment):
        spec = REGIONS[key]
        rng = getattr(row, key)
        value = measurements.get(key)
        if rng is None or value is None or value <= 0:
            regions.append({
                "key": key,
                "label": spec["label"],
                "status": "unknown",
                "verdict": "unknown",
                "band": {"from": spec["band"][0], "to": spec["band"][1]},
                **VERDICTS["unknown"],
            })
            continue
        body = float(value)
        midpoint = (rng.min + rng.max) / 2
        garment_cm = midpoint + baseline
        basis = "size_chart_estimate"
        flat_value = size_spec.get(key) if size_spec else None
        if flat_value is not None:
            try:
                flat_cm = float(flat_value)
            except (TypeError, ValueError):
                flat_cm = 0.0
            if flat_cm > 0:
                garment_cm = flat_cm
                basis = "garment_flat_spec"
                uses_flat_spec = True
        ease = garment_cm - body
        verdict = classify(ease, stretch)
        regions.append({
            "key": key,
            "label": spec["label"],
            "status": "estimated",
            "body_cm": round(body, 1),
            "range_min_cm": round(rng.min, 1),
            "range_max_cm": round(rng.max, 1),
            "garment_estimate_cm": round(garment_cm, 1),
            "ease_cm": round(ease, 1),
            "clearance_cm": round(ease / 6.2832, 1),
            "verdict": verdict,
            "label_text": VERDICTS[verdict]["label"],
            "color": VERDICTS[verdict]["color"],
            "basis": basis,
            "band": {"from": spec["band"][0], "to": spec["band"][1]},
        })

    known = [r for r in regions if r["verdict"] != "unknown"]
    if not known:
        overall_key = "unknown"
    else:
        overall_key = max(known, key=lambda r: _ORDER[r["verdict"]])["verdict"]
    if uses_flat_spec:
        warnings = [
            "Số đo may lấy từ bảng thông số đã công bố của hãng (chiều rộng trải phẳng ×2), không phải đo lại sản phẩm thực tế.",
            "Chưa mô phỏng vải, đường may hay độ rơi; cùng một size có thể khác nhau giữa các lô hàng.",
        ]
    else:
        warnings = [
            "Ước lượng từ khoảng số đo cơ thể của bảng size, không phải số đo may (flat) hay mô phỏng vải.",
            "Độ co giãn chỉ suy từ mô tả chất liệu; cùng một size có thể khác nhau giữa các lô hàng.",
        ]
    if stretch:
        warnings.append("Chất liệu có thành phần co giãn: ngưỡng chật được nới cho hàng dệt kim.")
    return {
        "status": "ok" if len(known) == len(regions) else ("partial" if known else "insufficient_measurements"),
        "size": size,
        "garment": chart.garment,
        "stretch": stretch,
        "baseline_ease_cm": baseline,
        "regions": regions,
        "overall": {**VERDICTS[overall_key], "key": overall_key},
        "confidence": "published_garment_spec" if uses_flat_spec else CONFIDENCE,
        "garment_source": product.get("garment_source"),
        "warnings": warnings,
    }
