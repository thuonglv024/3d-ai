"""Continuous vertex fit field for flat garment specs.

The field is defined on mesh vertices (metres, Y up).  Only the torso between
the shoulder and the garment hem has garment data; chest ease is applied there
with a cosine taper (default 4 cm) at the shoulder and hem.  Arm vertices are
excluded by horizontal distance from the torso axis, not by a Y band, and have
coverage 0 because no sleeve ease exists.  Below the hem / outside the torso is
coverage 0 (grey).  This module does not change k, the 1.40 guard, or the
fit-style thresholds.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

import numpy as np

from .garment_fit import FIT_STYLE_THRESHOLDS, LABEL_COLOR, thresholds_for_style

FIT_FIELD_CONFIG: dict[str, Any] = {
    "taper_cm": 4.0,
    "arm_x_fraction": 0.18,
    "unknown_color": "#c9d1c8",
    "shoulder_level": 0.805,
    "hip_level": 0.534,
    "oversized_anchor_offset_cm": 8.0,
    "sleeve_ease_cm": None,
}

# Continuous palette (the thresholds themselves are read from garment_fit).
COLOR_BY_LABEL = {
    "tight": "#b23a2f",
    "snug": "#d08a2e",
    "regular": "#3f8f5c",
    "loose": "#6aa6c8",
    "oversized": "#1f4d73",
}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb: Iterable[float]) -> str:
    return "#" + "".join(f"{int(round(max(0, min(255, channel)) )):02x}" for channel in rgb)


def color_stops(fit_style: str | None = None) -> list[dict[str, Any]]:
    """Continuous colormap anchors derived from the config thresholds."""
    thresholds = thresholds_for_style(fit_style)
    loose_max = float(thresholds["loose_max_cm"])
    anchor = loose_max + float(FIT_FIELD_CONFIG["oversized_anchor_offset_cm"])
    return [
        {"ease_cm": float(thresholds["tight_max_cm"]), "label": "tight", "color": COLOR_BY_LABEL["tight"]},
        {"ease_cm": float(thresholds["snug_max_cm"]), "label": "snug", "color": COLOR_BY_LABEL["snug"]},
        {"ease_cm": float(thresholds["regular_max_cm"]), "label": "regular", "color": COLOR_BY_LABEL["regular"]},
        {"ease_cm": loose_max, "label": "loose", "color": COLOR_BY_LABEL["loose"]},
        {"ease_cm": anchor, "label": "oversized", "color": COLOR_BY_LABEL["oversized"]},
    ]


def color_for_ease(ease_cm: float, stops: list[dict[str, Any]] | None = None) -> str:
    """Piecewise-linear colour between the configured ease anchors."""
    anchors = sorted(stops or color_stops(), key=lambda item: float(item["ease_cm"]))
    if not anchors:
        return FIT_FIELD_CONFIG["unknown_color"]
    if ease_cm <= float(anchors[0]["ease_cm"]):
        return str(anchors[0]["color"])
    for left, right in zip(anchors, anchors[1:]):
        left_ease, right_ease = float(left["ease_cm"]), float(right["ease_cm"])
        if ease_cm <= right_ease:
            if right_ease <= left_ease:
                return str(right["color"])
            t = (float(ease_cm) - left_ease) / (right_ease - left_ease)
            left_rgb, right_rgb = _rgb(str(left["color"])), _rgb(str(right["color"]))
            return _hex(tuple(a + (b - a) * t for a, b in zip(left_rgb, right_rgb)))
    return str(anchors[-1]["color"])


def colors_for_ease(
    ease_values: np.ndarray,
    coverage: np.ndarray,
    stops: list[dict[str, Any]] | None = None,
    unknown_color: str | None = None,
) -> np.ndarray:
    """Per-vertex RGB (uint8) with a fixed grey for coverage == 0."""
    anchors = stops or color_stops()
    grey = _rgb(unknown_color or FIT_FIELD_CONFIG["unknown_color"])
    out = np.zeros((len(ease_values), 3), dtype=np.uint8)
    for i, (ease, covered) in enumerate(zip(ease_values, coverage)):
        out[i] = _rgb(color_for_ease(float(ease), anchors)) if covered >= 0.5 else grey
    return out


def compute_fit_field(
    vertices: np.ndarray,
    spec_size: dict[str, Any],
    chest_ease_cm: float,
    *,
    shoulder_y_m: float | None = None,
    hip_y_m: float | None = None,
    height_m: float | None = None,
    y_norm: np.ndarray | None = None,
    taper_cm: float | None = None,
    arm_x_fraction: float | None = None,
    center_x_m: float = 0.0,
    sleeve_ease_cm: float | None = None,
    fit_style: str | None = None,
) -> dict[str, Any]:
    """Return per-vertex ``ease_cm``, ``coverage`` and RGB colours.

    ``y_norm`` is optional: when omitted, Y is normalized as
    ``(y - hip_y_m) / (shoulder_y_m - hip_y_m)`` (shoulder=1, hip=0).  The
    garment length is measured from HPS (shoulder) and is unverified.
    """
    points = np.asarray(vertices, dtype=float)
    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError("vertices phải có shape (N, 3).")
    y = points[:, 1]
    x = points[:, 0]
    if y_norm is None:
        if shoulder_y_m is None or hip_y_m is None:
            if height_m is None:
                raise ValueError("Cần shoulder_y_m/hip_y_m hoặc height_m để chuẩn hoá Y.")
            shoulder_y_m = FIT_FIELD_CONFIG["shoulder_level"] * float(height_m)
            hip_y_m = FIT_FIELD_CONFIG["hip_level"] * float(height_m)
        span = float(shoulder_y_m) - float(hip_y_m)
        if span <= 1e-9:
            raise ValueError("shoulder_y_m phải cao hơn hip_y_m.")
        y_level = (y - float(hip_y_m)) / span
    else:
        y_level = np.asarray(y_norm, dtype=float)
        if y_level.shape != (len(points),):
            raise ValueError("y_norm phải có cùng số phần tử với vertices.")
        span = float(shoulder_y_m) - float(hip_y_m) if shoulder_y_m is not None and hip_y_m is not None else None
        if span is None:
            if height_m is None:
                raise ValueError("Cần shoulder_y_m/hip_y_m hoặc height_m cùng y_norm.")
            span = (FIT_FIELD_CONFIG["shoulder_level"] - FIT_FIELD_CONFIG["hip_level"]) * float(height_m)

    length_cm = spec_size.get("length_cm") if isinstance(spec_size, dict) else None
    if length_cm is None:
        coverage = np.zeros(len(points), dtype=np.float32)
        ease = np.zeros(len(points), dtype=float)
        return {
            "ease_cm": ease,
            "coverage": coverage,
            "colors": colors_for_ease(ease, coverage),
            "hem_level": None,
            "taper_cm": float(taper_cm or FIT_FIELD_CONFIG["taper_cm"]),
            "arm_x_fraction": float(arm_x_fraction or FIT_FIELD_CONFIG["arm_x_fraction"]),
            "unverified": True,
            "color_stops": color_stops(),
        }

    height = float(height_m if height_m is not None else (span if span else 1.0))
    taper = float(taper_cm if taper_cm is not None else FIT_FIELD_CONFIG["taper_cm"])
    arm_fraction = float(arm_x_fraction if arm_x_fraction is not None else FIT_FIELD_CONFIG["arm_x_fraction"])
    # Hem from HPS: shoulder is y_level 1.0; a garment length of L cm lowers the
    # hem by L/span in shoulder-to-hip level units.
    hem_level = 1.0 - (float(length_cm) / 100.0) / max(span, 1e-9)
    taper_level = max((taper / 100.0) / max(span, 1e-9), 1e-9)
    arm_mask = np.abs(x - center_x_m) > arm_fraction * height
    torso = (y_level >= hem_level) & (y_level <= 1.0) & ~arm_mask
    coverage = torso.astype(np.float32)

    edge = np.minimum((1.0 - y_level) / taper_level, (y_level - hem_level) / taper_level)
    edge = np.clip(edge, 0.0, 1.0)
    ease = float(chest_ease_cm) * (0.5 - 0.5 * np.cos(np.pi * edge))
    ease = np.where(torso, ease, 0.0)

    # Sleeves have no data yet; keep the hook explicit instead of inventing one.
    if sleeve_ease_cm is not None:
        sleeve_length_cm = float(spec_size.get("sleeve_cm") or 0.0)
        sleeve_bottom = 1.0 - (sleeve_length_cm / 100.0) / max(span, 1e-9)
        sleeve = arm_mask & (y_level >= sleeve_bottom) & (y_level <= 1.0)
        coverage = np.maximum(coverage, sleeve.astype(np.float32))
        ease = np.where(sleeve, float(sleeve_ease_cm), ease)

    stops = color_stops(fit_style)
    return {
        "ease_cm": ease,
        "coverage": coverage,
        "colors": colors_for_ease(ease, coverage, stops),
        "hem_level": float(hem_level),
        "taper_cm": taper,
        "arm_x_fraction": arm_fraction,
        "unverified": True,
        "color_stops": stops,
        "unknown_color": FIT_FIELD_CONFIG["unknown_color"],
        "sleeve_ease_cm": sleeve_ease_cm,
    }


def build_heatmap_payload(
    fit_style: str | None,
    ease_cm: float,
    spec_size: dict[str, Any],
    *,
    unverified: bool = True,
    length_measurement_point: str | None = None,
) -> dict[str, Any]:
    """JSON-safe metadata the frontend needs to colour vertices."""
    return {
        "mode": "continuous_vertex",
        "ease_cm": float(ease_cm),
        "taper_cm": float(FIT_FIELD_CONFIG["taper_cm"]),
        "arm_x_fraction": float(FIT_FIELD_CONFIG["arm_x_fraction"]),
        "garment_length_cm": spec_size.get("length_cm"),
        "garment_length_measurement_point": length_measurement_point or "HPS, chưa xác minh",
        "shoulder_level": float(FIT_FIELD_CONFIG["shoulder_level"]),
        "hip_level": float(FIT_FIELD_CONFIG["hip_level"]),
        "color_stops": color_stops(fit_style),
        "unknown_color": FIT_FIELD_CONFIG["unknown_color"],
        "unverified": bool(unverified),
        "sleeve_ease_cm": None,
        "sleeve_length_cm": spec_size.get("sleeve_cm"),
        "coverage_legend": {
            "0": "xám: không có số đo áo (tay / dưới gấu / ngoài thân)",
            "1": "vùng thân áo: ease ngực với taper 4 cm",
        },
    }
