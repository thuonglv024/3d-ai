"""Proportional scaling for the secondary body rings.

The two photos only observe chest/waist/hip. Head, neck, thigh, calf and ankle
are *modelling priors*: they follow one of the main rings with a fixed
elasticity, so a broader hip also produces slightly thicker thighs instead of
leaving the legs untouched. The coefficients below are documented guesses for a
believable silhouette, not anthropometric constants or measured data.
"""
from __future__ import annotations

import numpy as np

# `level` is normalised height (0 = floor, 1 = crown) and matches the section
# levels used by the measurement report. `driver` names the main measurement the
# ring follows; `coefficient` is the relative change of this ring per relative
# change of the driver (0.5 = half as much).
RINGS = (
    {"key": "neck_cm", "label": "Vòng cổ", "level": 0.855, "driver": "chest_cm", "coefficient": 0.35, "part": "torso"},
    {"key": "thigh_cm", "label": "Vòng đùi", "level": 0.405, "driver": "hip_cm", "coefficient": 0.60, "part": "legs"},
    {"key": "calf_cm", "label": "Vòng bắp chân", "level": 0.235, "driver": "hip_cm", "coefficient": 0.35, "part": "legs"},
    {"key": "ankle_cm", "label": "Vòng cổ chân", "level": 0.065, "driver": "hip_cm", "coefficient": 0.15, "part": "legs"},
)

HALF_BAND = 0.045  # legacy cosine bands, kept behind mode="bands"
MIN_SCALE, MAX_SCALE = 0.80, 1.30
LEG_SIGMA = 0.09
NECK_SIGMA = 0.06
LEG_MIN_X, LEG_MAX_X = 0.02, 0.17  # fractions of body height
LEG_FADE_TOP = 0.47
LEG_FADE_RANGE = 0.05
NECK_MIN_Y, NECK_MAX_Y = 0.78, 0.93


def relative_change(base_cm: float, target_cm: float) -> float:
    base = float(base_cm or 0.0)
    if base <= 1e-6:
        return 0.0
    return (float(target_cm) - base) / base


def ring_scales(base_mains: dict, target_mains: dict) -> dict[str, float]:
    """Scale factor per secondary ring, from the main measurements' change."""
    scales: dict[str, float] = {}
    for ring in RINGS:
        change = relative_change(base_mains.get(ring["driver"], 0.0), target_mains.get(ring["driver"], 0.0))
        scale = 1.0 + ring["coefficient"] * change
        scales[ring["key"]] = float(np.clip(scale, MIN_SCALE, MAX_SCALE))
    return scales


def _band_weight(y: np.ndarray, level: float) -> np.ndarray:
    w = np.clip(1.0 - np.abs(y - level) / HALF_BAND, 0.0, 1.0)
    # Cosine taper: 1 at the ring level, 0 at the band edges, no hard seam.
    return np.sin(w * np.pi / 2.0)


def _scale_torso(mesh, y: np.ndarray, weight: np.ndarray, level: float, scale: float, height_m: float) -> None:
    vertices = mesh.vertices
    band = np.abs(y - level) < HALF_BAND
    if not band.any():
        return
    center_z = float((vertices[band, 2].min() + vertices[band, 2].max()) / 2)
    factor = 1.0 + (scale - 1.0) * weight
    vertices[:, 0] *= factor
    vertices[:, 2] = center_z + (vertices[:, 2] - center_z) * factor


def _scale_legs(mesh, y: np.ndarray, weight: np.ndarray, level: float, scale: float, height_m: float) -> None:
    vertices = mesh.vertices
    band = np.abs(y - level) < HALF_BAND
    if not band.any():
        return
    for sign in (1.0, -1.0):
        selected = band & (vertices[:, 0] * sign > 0.0)
        if selected.sum() < 8:
            continue
        center_x = float((vertices[selected, 0].min() + vertices[selected, 0].max()) / 2)
        center_z = float((vertices[selected, 2].min() + vertices[selected, 2].max()) / 2)
        factor = 1.0 + (scale - 1.0) * weight[selected]
        vertices[selected, 0] = center_x + (vertices[selected, 0] - center_x) * factor
        vertices[selected, 2] = center_z + (vertices[selected, 2] - center_z) * factor


def _rbf_field(y: np.ndarray, levels, scales, sigma: float) -> np.ndarray:
    """Continuous Gaussian field that is exact at each ring level and 1.0 away."""
    centers = np.asarray(levels, dtype=float)
    amps = np.asarray(scales, dtype=float) - 1.0
    matrix = np.exp(-((centers[:, None] - centers[None, :]) / sigma) ** 2)
    matrix = matrix + np.eye(len(centers)) * 1e-6
    try:
        weights = np.linalg.solve(matrix, amps)
    except np.linalg.LinAlgError:
        weights = amps
    basis = np.exp(-((y[:, None] - centers[None, :]) / sigma) ** 2)
    return np.clip(1.0 + basis @ weights, MIN_SCALE, MAX_SCALE)


def _leg_centres(mesh, height_m: float):
    """One centre per side (mirrored), varying with height; both legs share it."""
    vertices = mesh.vertices
    y = vertices[:, 1] / height_m
    levels, xs, zs = [], [], []
    for level in (0.405, 0.235, 0.065):
        band = (np.abs(y - level) < .03) & (vertices[:, 0] > LEG_MIN_X * height_m) & (vertices[:, 0] < LEG_MAX_X * height_m)
        if band.sum() < 8:
            continue
        levels.append(level)
        xs.append(float((vertices[band, 0].min() + vertices[band, 0].max()) / 2))
        zs.append(float((vertices[band, 2].min() + vertices[band, 2].max()) / 2))
    if not levels:
        return None
    return levels, xs, zs


def _apply_rings_field(mesh, scales: dict[str, float], height_m: float) -> dict[str, float]:
    """One continuous field per part: Gaussian leg field + Gaussian neck bump."""
    vertices = mesh.vertices
    y = vertices[:, 1] / height_m
    applied: dict[str, float] = {}
    leg_levels = (0.405, 0.235, 0.065)
    leg_scales = [float(scales.get(key, 1.0)) for key in ("thigh_cm", "calf_cm", "ankle_cm")]
    if any(abs(s - 1.0) >= 1e-4 for s in leg_scales):
        centres = _leg_centres(mesh, height_m)
        if centres is not None:
            levels, xs, zs = centres
            field_scales = [leg_scales[leg_levels.index(level)] for level in levels]
            leg_field = _rbf_field(y, levels, field_scales, LEG_SIGMA)
            leg_mask = (y < LEG_FADE_TOP) & (np.abs(vertices[:, 0]) >= LEG_MIN_X * height_m) & (np.abs(vertices[:, 0]) <= LEG_MAX_X * height_m)
            # Fade back to 1.0 below the hip so the measured hip section is untouched.
            leg_fade = np.clip((LEG_FADE_TOP - y) / LEG_FADE_RANGE, 0.0, 1.0)
            leg_factor = 1.0 + (leg_field - 1.0) * leg_fade
            cx = np.interp(y, levels[::-1], xs[::-1])
            cz = np.interp(y, levels[::-1], zs[::-1])
            for sign in (1.0, -1.0):
                selected = leg_mask & (vertices[:, 0] * sign > 0.0)
                if selected.sum() < 8:
                    continue
                center_x = sign * cx[selected]
                factor = leg_factor[selected]
                vertices[selected, 0] = center_x + (vertices[selected, 0] - center_x) * factor
                vertices[selected, 2] = cz[selected] + (vertices[selected, 2] - cz[selected]) * factor
            applied.update({key: float(scales.get(key, 1.0)) for key in ("thigh_cm", "calf_cm", "ankle_cm")})

    neck_scale = float(scales.get("neck_cm", 1.0))
    if abs(neck_scale - 1.0) >= 1e-4:
        neck_field = 1.0 + (neck_scale - 1.0) * np.exp(-((y - .855) / NECK_SIGMA) ** 2)
        neck_mask = (y >= NECK_MIN_Y) & (y <= NECK_MAX_Y) & (np.abs(vertices[:, 0]) < .18 * height_m)
        if neck_mask.any():
            center_z = float((vertices[neck_mask, 2].min() + vertices[neck_mask, 2].max()) / 2)
            factor = neck_field[neck_mask]
            vertices[neck_mask, 0] *= factor
            vertices[neck_mask, 2] = center_z + (vertices[neck_mask, 2] - center_z) * factor
            applied["neck_cm"] = neck_scale
    if applied:
        mesh.fix_normals()
    return applied


def _apply_rings_bands(mesh, scales: dict[str, float], height_m: float) -> dict[str, float]:
    """Legacy implementation: four independent cosine bands (rollback path)."""
    if height_m <= 0:
        return {}
    y = mesh.vertices[:, 1] / height_m
    applied: dict[str, float] = {}
    for ring in RINGS:
        scale = float(scales.get(ring["key"], 1.0))
        if abs(scale - 1.0) < 1e-4:
            continue
        weight = _band_weight(y, ring["level"])
        if not (weight > 0).any():
            continue
        if ring["part"] == "torso":
            _scale_torso(mesh, y, weight, ring["level"], scale, height_m)
        else:
            _scale_legs(mesh, y, weight, ring["level"], scale, height_m)
        applied[ring["key"]] = scale
    if applied:
        mesh.fix_normals()
    return applied


def apply_rings(mesh, scales: dict[str, float], height_m: float, mode: str = "field") -> dict[str, float]:
    """Scale the secondary rings in place; returns the applied factors.

    ``mode="field"`` uses one continuous Gaussian field per part, so the three
    leg rings share a single scale profile and both legs use the same mirrored
    centre. ``mode="bands"`` keeps the legacy four independent cosine bands for
    rollback. `fit_measurement_targets` still re-imposes the main sections.
    """
    if mode == "bands":
        return _apply_rings_bands(mesh, scales, height_m)
    if mode != "field":
        raise ValueError(f"Unknown ring mode: {mode!r}")
    if height_m <= 0:
        return {}
    return _apply_rings_field(mesh, scales, height_m)


def describe(scales: dict[str, float]) -> list[dict]:
    """JSON-friendly explanation of the prior, exposed in the scan profile."""
    return [
        {
            "key": ring["key"],
            "label": ring["label"],
            "driver": ring["driver"],
            "coefficient": ring["coefficient"],
            "scale": round(float(scales.get(ring["key"], 1.0)), 4),
        }
        for ring in RINGS
    ]
