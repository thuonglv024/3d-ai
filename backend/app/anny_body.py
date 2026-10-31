"""Anny-derived body bases for the avatar engine.

The meshes in ``backend/models/anny-bases.npz`` are generated offline from the
Anny parametric body model (NAVER Labs Europe, Apache-2.0 code, MPFB2/MakeHuman
assets CC0-1.0) by ``verification/scripts/build_anny_bases.py``. Anny itself
takes ~3 minutes and ~1 GB to instantiate on CPU, which cannot happen inside a
web request, so the runtime only reads this compact sex x weight x muscle basis
and interpolates it linearly.

Everything here is a *modelling prior*: measured circumferences are still
imposed afterwards by ``fit_measurement_targets``. Nothing in this module is
anthropometric validation.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import trimesh

from .config import MODELS

BASES_PATH = MODELS / "anny-bases.npz"
META_PATH = MODELS / "anny-bases.json"
BACKUP_BASES_PATH = MODELS / "anny-bases-v1.npz"
BACKUP_META_PATH = MODELS / "anny-bases-v1.json"
COLOR = [148, 170, 146, 255]


def _load(path: Path, meta_path: Path) -> tuple[dict[tuple[str, float, float], np.ndarray], np.ndarray, dict]:
    data = np.load(path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meshes: dict[tuple[str, float, float], np.ndarray] = {}
    for key in data.files:
        if key == "faces":
            continue
        sex, weight, muscle = key.split("|")
        meshes[(sex, float(weight), float(muscle))] = data[key]
    return meshes, data["faces"], meta


def available() -> tuple[bool, str]:
    if not BASES_PATH.is_file() or not META_PATH.is_file():
        return False, "Chưa có basis Anny trong backend/models (chạy verification/scripts/build_anny_bases.py)."
    return True, ""


@lru_cache(maxsize=1)
def _basis() -> tuple[dict[tuple[str, float, float], np.ndarray], np.ndarray, dict]:
    last_error: Exception | None = None
    for bases, meta in ((BASES_PATH, META_PATH), (BACKUP_BASES_PATH, BACKUP_META_PATH)):
        if not (bases.is_file() and meta.is_file()):
            continue
        try:
            return _load(bases, meta)
        except Exception as exc:  # corrupt/mismatched primary falls back to v1
            last_error = exc
    raise RuntimeError(f"Không đọc được basis Anny: {last_error}")


def phenotype_from_measurements(measurements: dict, height_cm: float | None) -> tuple[float, float]:
    """Map the reported measurements to the basis grid (a prior, not a body-fat measurement).

    Waist-to-height ratio is used only to pick where the body carries mass; the
    grid is coarse on purpose so a noisy estimate cannot produce an extreme body.
    """
    waist = measurements.get("waist_cm")
    height = height_cm or measurements.get("height_cm")
    if not waist or not height:
        return 0.50, 0.45
    ratio = float(waist) / float(height)
    weight = float(np.interp(ratio, (0.40, 0.48, 0.58), (0.30, 0.50, 0.70)))
    return round(weight, 3), 0.45


def _interp(sex: str, weight: float, muscle: float) -> np.ndarray:
    meshes, _, meta = _basis()
    weights = sorted({w for (s, w, _) in meshes if s == sex})
    muscles = sorted({m for (s, _, m) in meshes if s == sex})
    if not weights or not muscles:
        raise KeyError(f"Không có basis Anny cho giới {sex!r}.")

    weight = float(np.clip(weight, weights[0], weights[-1]))
    muscle = float(np.clip(muscle, muscles[0], muscles[-1]))
    w0, w1 = _bracket(weights, weight)
    m0, m1 = _bracket(muscles, muscle)
    tw = 0.0 if w1 == w0 else (weight - w0) / (w1 - w0)
    tm = 0.0 if m1 == m0 else (muscle - m0) / (m1 - m0)

    result = np.zeros_like(meshes[(sex, w0, m0)], dtype=np.float64)
    for wi, ww in ((w0, 1 - tw), (w1, tw)):
        for mi, mm in ((m0, 1 - tm), (m1, tm)):
            if ww and mm:
                result += ww * mm * meshes[(sex, wi, mi)]
    return result


def _bracket(values: list[float], x: float) -> tuple[float, float]:
    if x <= values[0]:
        return values[0], values[0]
    if x >= values[-1]:
        return values[-1], values[-1]
    for low, high in zip(values, values[1:]):
        if low <= x <= high:
            return low, high
    return values[-1], values[-1]


def build(sex: str, weight: float, muscle: float, height_cm: float) -> trimesh.Trimesh:
    """Return a body mesh in metres, Y up, feet at y=0, front +Z."""
    vertices = _interp(sex, weight, muscle).copy()
    _, faces, _ = _basis()
    height_m = float(height_cm) / 100.0
    vertices *= height_m
    vertices[:, 1] -= vertices[:, 1].min()
    mesh = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces, dtype=np.int64), process=False)
    mesh.visual.vertex_colors = COLOR
    mesh.fix_normals()
    return mesh


def describe() -> dict:
    ok, message = available()
    if not ok:
        return {"available": False, "message": message}
    _, _, meta = _basis()
    return {
        "available": True,
        "name": "Anny",
        "version": meta.get("source", "anny"),
        "basis_version": meta.get("basis_version"),
        "license": meta.get("license"),
        "weights": meta.get("weights"),
        "muscles": meta.get("muscles"),
        "vertex_count": meta.get("vertex_count"),
    }
