"""Sex-specific proportions and anterior/posterior depth priors for the avatar.

The MakeHuman hm08 base mesh is androgynous, so the same estimated measurements
would otherwise produce the same silhouette for every body. This module applies a
small, documented *modelling prior* - shoulder-to-hip relationship, bust/glute
volume and limb thickness - on the normalised template (height 1, feet at y=0,
front towards +z). Measured circumferences still win: `fit_measurement_targets`
runs afterwards and re-imposes chest/waist/hip. Nothing here is anthropometric
validation or gender identification.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

Sex = str
SEX_CHOICES = ("female", "male")

# Lateral multipliers at normalised height (0 = floor, 1 = crown). Only regions
# that the circumference fit does not pin per person (shoulders, upper back,
# upper thigh) carry large factors; hip/waist stay close to 1.0.
_LATERAL = {
    "female": (
        [0.00, 0.42, 0.48, 0.54, 0.60, 0.66, 0.72, 0.805, 0.86, 1.00],
        [1.00, 1.00, 1.04, 1.05, 0.97, 0.97, 0.99, 0.95, 0.97, 1.00],
    ),
    "male": (
        [0.00, 0.42, 0.48, 0.54, 0.60, 0.66, 0.72, 0.805, 0.86, 1.00],
        [1.00, 1.00, 0.97, 0.96, 1.02, 1.02, 1.01, 1.05, 1.03, 1.00],
    ),
}

# Localised depth volumes are intentionally disabled: a single Gaussian bump on
# a low-poly androgynous mesh reads as a cone/shelf, not as anatomy. Sex
# differences come from the lateral shoulder/hip/thigh profile only until a
# proper morph-target base mesh is introduced.
_VOLUMES: dict[str, tuple] = {"female": (), "male": ()}

# How much of a depth change goes to the front vs the back at each height.
_DEPTH_KNOTS = np.array([0.00, 0.35, 0.46, 0.55, 0.62, 0.70, 0.78, 0.86, 1.00])
_DEPTH_FRONT = np.array([1.00, 1.00, 0.72, 0.66, 0.78, 1.00, 0.95, 0.90, 1.00])
_DEPTH_BACK = np.array([1.00, 1.00, 1.00, 1.00, 0.86, 0.45, 0.55, 0.90, 1.00])


def resolve_sex(requested: str, measurements: dict, capture_mode: str = "full_body") -> tuple[Sex, str]:
    """Return (sex, source). Explicit choice wins; otherwise infer from proportions.

    The inference only reads ratios that the scan already reports; it never
    inspects the photo for identity, and ties fall back to ``female`` - the
    storefront default - with ``source="auto"`` so the assumption stays visible.
    """
    if requested in SEX_CHOICES:
        return requested, "user"

    chest = measurements.get("chest_cm")
    waist = measurements.get("waist_cm")
    hip = measurements.get("hip_cm")
    shoulder = measurements.get("shoulder_width_cm")
    score = 0

    if hip and chest:
        score += 2 if hip - chest >= 3 else -2 if hip - chest <= -5 else 0
    if hip and shoulder:
        ratio = shoulder / hip
        score += 1 if ratio < 0.56 else -1 if ratio > 0.64 else 0
    if hip and waist:
        whr = waist / hip
        score += 1 if whr < 0.80 else -1 if whr > 0.90 else 0

    if capture_mode == "upper_body" or not hip:
        # No hip observation: fall back to shoulder/chest and waist/chest.
        if shoulder and chest:
            ratio = shoulder / chest
            score += 1 if ratio < 0.44 else -1 if ratio > 0.50 else 0
        if waist and chest:
            score += 1 if waist / chest < 0.78 else -1 if waist / chest > 0.85 else 0

    return ("female" if score >= 0 else "male"), "auto"


@lru_cache(maxsize=4)
def template_landmarks(path: str) -> dict[str, float]:
    """Skeletal landmark heights from the template's own ``g joint-*`` groups.

    The base mesh ships small joint markers built from body vertices, so their
    centroids give real anatomical heights in normalised units (0 = floor,
    1 = crown) without extra assets.
    """
    vertices: list[list[float]] = []
    body: set[int] = set()
    groups: dict[str, set[int]] = {}
    current = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            vertices.append([float(v) for v in line.split()[1:4]])
        elif line.startswith("g "):
            current = line[2:].strip()
        elif line.startswith("f ") and current:
            indices = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            if current == "body":
                body.update(indices)
            elif current.startswith("joint-"):
                groups.setdefault(current, set()).update(indices)
    if not body or not groups:
        return {}
    points = np.asarray(vertices)
    floor = float(points[sorted(body), 1].min())
    span = float(np.ptp(points[sorted(body), 1]))
    if span <= 0:
        return {}

    def level(name: str) -> float | None:
        indices = groups.get(name)
        if not indices:
            return None
        return float(np.mean(points[sorted(indices), 1] - floor) / span)

    landmarks: dict[str, float] = {}
    shoulders = [value for key in ("joint-l-shoulder", "joint-r-shoulder") if (value := level(key)) is not None]
    if shoulders:
        landmarks["shoulder"] = float(np.mean(shoulders))
    for key, name in (("hip", "joint-pelvis"), ("neck", "joint-neck")):
        value = level(name)
        if value is not None:
            landmarks[key] = value
    return landmarks


def depth_weights(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Front/back share of a depth change at normalised height ``y``."""
    y = np.asarray(y, dtype=float)
    front = PchipInterpolator(_DEPTH_KNOTS, _DEPTH_FRONT)(np.clip(y, 0.0, 1.0))
    back = PchipInterpolator(_DEPTH_KNOTS, _DEPTH_BACK)(np.clip(y, 0.0, 1.0))
    return front, back


def _centre_z(vertices: np.ndarray) -> np.ndarray:
    """Approximate the torso's depth centre line for every vertex (array)."""
    y = vertices[:, 1]
    narrow = np.abs(vertices[:, 0]) < 0.05
    mids, centres = [], []
    for low in np.linspace(0.25, 0.90, 14):
        selected = narrow & (y >= low) & (y < low + 0.05)
        if selected.any():
            mids.append(low + 0.025)
            centres.append(float(np.median(vertices[selected, 2])))
    if len(mids) < 2:
        return np.zeros_like(y)
    return PchipInterpolator(mids, centres)(y)


def shape_sex(mesh, sex: str):
    """Apply the sex proportion prior to a normalised template mesh."""
    if sex not in _LATERAL:
        return mesh
    mesh = mesh.copy()
    vertices = mesh.vertices.copy()
    y = vertices[:, 1]

    knots, factors = _LATERAL[sex]
    vertices[:, 0] *= PchipInterpolator(knots, factors)(y)

    centre = _centre_z(vertices)
    depth = vertices[:, 2] - centre
    torso = np.exp(-((vertices[:, 0] / 0.11) ** 2))
    for centre_y, sigma, direction, amplitude in _VOLUMES[sex]:
        front = (depth * direction) > 0
        # Posterior volumes move the surface backwards (negative depth), so the
        # sign of the direction decides whether the offset is added or removed.
        depth = depth + direction * amplitude * np.exp(-(((y - centre_y) / sigma) ** 2)) * torso * front
    vertices[:, 2] = centre + depth

    mesh.vertices = vertices
    return mesh
