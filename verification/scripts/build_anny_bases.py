"""Bake the Anny body-model bases used by the avatar engine.

Anny (NAVER Labs Europe, Apache-2.0; MPFB2 assets CC0) takes ~3 minutes and
~1 GB of RAM to instantiate on CPU, which is not acceptable inside a web
request. The phenotype space we need is small (sex x weight x muscle), so this
script samples it once and stores the resulting meshes as a compact basis that
the backend interpolates linearly.

Run from the repo root (requires ``pip install anny``):

    backend/.venv/Scripts/python.exe verification/scripts/build_anny_bases.py

Outputs ``backend/models/anny-bases.npz`` + ``anny-bases.json`` and QA renders
under ``output/anny-probe/``.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from trimesh.smoothing import filter_taubin

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("ANNY_CACHE_DIR", str(ROOT / "backend" / ".anny-cache"))
sys.path.insert(0, str(ROOT / "backend"))

import anny  # noqa: E402
import torch  # noqa: E402

WEIGHTS = (0.30, 0.50, 0.70)
MUSCLES = (0.35, 0.60)
SEXES = ("female", "male")
# Anny exposes breast/hip/buttock shapes as local changes, not as phenotypes.
# v2 reduces them to weak priors: the measurement fit supplies the final shape,
# and the baked bumps were creating visible ring shelves (K3/S3/S5).
LOCAL_CHANGES = {
    "female": {
        "breast-volume-vert-up": 0.15,
        "breast-point-incr": 0.05,
        "buttocks-volume-incr": 0.10,
        "hip-scale-horiz-incr": 0.10,
        "hip-trans-out": 0.05,
    },
    "male": {
        "torso-vshape-incr": 0.25,
        "torso-muscle-pectoral-incr": 0.05,
        "l-upperarm-shoulder-muscle-incr": 0.20,
        "r-upperarm-shoulder-muscle-incr": 0.20,
        "buttocks-volume-incr": 0.02,
    },
}
BASIS_VERSION = 2
SMOOTH_ITERATIONS = 0
SMOOTH_LAMB = .45
SMOOTH_NU = .48
OUT_MODELS = ROOT / "backend" / "models"
OUT_QA = ROOT / "output" / "anny-probe"
PRIMARY = OUT_MODELS / "anny-bases.npz"
PRIMARY_META = OUT_MODELS / "anny-bases.json"
BACKUP = OUT_MODELS / "anny-bases-v1.npz"
BACKUP_META = OUT_MODELS / "anny-bases-v1.json"


def to_avatar_frame(v: np.ndarray) -> np.ndarray:
    """Anny is Z-up and faces -Y; the avatar engine is Y-up facing +Z."""
    return np.column_stack([v[:, 0], v[:, 2], -v[:, 1]])


def normalise(v: np.ndarray) -> np.ndarray:
    v = v - v.min(axis=0)
    v = v * (1.0 / (v[:, 1].max() - v[:, 1].min()))
    v[:, 0] -= (v[:, 0].min() + v[:, 0].max()) / 2
    v[:, 2] -= (v[:, 2].min() + v[:, 2].max()) / 2
    v[:, 1] -= v[:, 1].min()
    return v


def torso_width(v: np.ndarray, level: float) -> float:
    band = v[(np.abs(v[:, 1] - level) < 0.004) & (np.abs(v[:, 0]) < 0.30)]
    return float(np.ptp(band[:, 0])) if len(band) else float("nan")


def render(v: np.ndarray, faces: np.ndarray, path: Path, axis: int) -> None:
    w, h = 520, 760
    img = Image.new("RGB", (w, h), (250, 248, 244))
    draw = ImageDraw.Draw(img)
    a = v[:, axis]
    b = v[:, 1]
    scale = min((w - 100) / max(float(np.ptp(a)), 1e-6), (h - 80) / max(float(np.ptp(b)), 1e-6))
    px = (w - float(np.ptp(a)) * scale) / 2 + (a - a.min()) * scale
    py = h - 40 - (b - b.min()) * scale
    x2 = np.stack([px[faces[:, 0]], py[faces[:, 0]]], axis=1)
    x1 = np.stack([px[faces[:, 1]], py[faces[:, 1]]], axis=1)
    x0 = np.stack([px[faces[:, 2]], py[faces[:, 2]]], axis=1)
    normals = np.cross(v[faces[:, 1]] - v[faces[:, 0]], v[faces[:, 2]] - v[faces[:, 0]])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    shade = np.clip(0.40 + 0.60 * np.abs(normals[:, 2] if axis == 0 else normals[:, 0]), 0, 1)
    # Painter's algorithm: draw the far faces first so the near surface wins.
    for i in np.argsort(-v[faces][:, :, 1].mean(axis=1)):
        c = int(112 + 104 * shade[i])
        draw.polygon([tuple(x0[i]), tuple(x1[i]), tuple(x2[i])], fill=(c, c - 7, c - 16))
    img.save(path)


def main() -> int:
    t = time.time()
    model = anny.Anny(topology="anny", local_changes="default").to(dtype=torch.float32)
    print(f"model loaded in {time.time() - t:.1f}s; phenotypes={list(model.phenotype_labels)}")
    pose = torch.eye(4)[None, None].repeat(1, model.bone_count, 1, 1)
    faces = model.faces if isinstance(model.faces, np.ndarray) else model.faces.detach().cpu().numpy()
    faces = np.asarray(faces, dtype=np.int32)

    bases: dict[str, np.ndarray] = {}
    OUT_QA.mkdir(parents=True, exist_ok=True)
    labels = set(model.local_change_labels)
    for sex in SEXES:
        local = {k: v for k, v in LOCAL_CHANGES[sex].items() if k in labels}
        missing = set(LOCAL_CHANGES[sex]) - labels
        if missing:
            print("skipping unknown local changes:", sorted(missing))
        for weight in WEIGHTS:
            for muscle in MUSCLES:
                kwargs = {key: 0.5 for key in model.phenotype_labels}
                kwargs.update(gender=0.0 if sex == "female" else 1.0, weight=weight, muscle=muscle, height=0.5, age=0.5)
                out = model(pose_parameters=pose, phenotype_kwargs=kwargs, local_changes_kwargs=local)
                v = normalise(to_avatar_frame(out["vertices"][0].detach().cpu().numpy().astype(float)))
                if SMOOTH_ITERATIONS > 0:
                    smoothed = trimesh.Trimesh(vertices=v, faces=faces, process=False)
                    filter_taubin(smoothed, lamb=SMOOTH_LAMB, nu=SMOOTH_NU, iterations=SMOOTH_ITERATIONS)
                    v = normalise(np.asarray(smoothed.vertices))
                bases[f"{sex}|{weight:.2f}|{muscle:.2f}"] = v.astype(np.float32)
                if weight == 0.50 and muscle == 0.35:
                    render(v, faces, OUT_QA / f"{sex}-w050-front.png", axis=0)
                    render(v, faces, OUT_QA / f"{sex}-w050-side.png", axis=2)
                print(
                    sex, f"w={weight:.2f} m={muscle:.2f}",
                    f"shoulder={torso_width(v, .82) * 100:.1f}cm",
                    f"chest={torso_width(v, .74) * 100:.1f}cm",
                    f"waist={torso_width(v, .60) * 100:.1f}cm",
                    f"hip={torso_width(v, .52) * 100:.1f}cm",
                )

    OUT_MODELS.mkdir(parents=True, exist_ok=True)
    if PRIMARY.exists() and not BACKUP.exists():
        shutil.copy2(PRIMARY, BACKUP)
        if PRIMARY_META.exists():
            shutil.copy2(PRIMARY_META, BACKUP_META)
        print("backed up v1 ->", BACKUP.name)
    np.savez_compressed(PRIMARY, faces=faces, **bases)
    meta = {
        "source": "Anny 0.6.1 (NAVER Labs Europe), topology=anny, local_changes=v2-weak",
        "basis_version": BASIS_VERSION,
        "license": "Apache-2.0 code; MPFB2 MakeHuman assets CC0-1.0",
        "frame": "Y up, feet at y=0, front +Z, height 1.0, centred on x/z",
        "sexes": list(SEXES),
        "weights": list(WEIGHTS),
        "muscles": list(MUSCLES),
        "local_changes": LOCAL_CHANGES,
        "smoothing": {"passes": SMOOTH_ITERATIONS, "lamb": SMOOTH_LAMB, "nu": SMOOTH_NU},
        "vertex_count": int(faces.max()) + 1,
        "face_count": int(len(faces)),
        "generated_at": time.strftime("%Y-%m-%d"),
    }
    PRIMARY_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("wrote", PRIMARY, "bases", len(bases), "version", BASIS_VERSION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
