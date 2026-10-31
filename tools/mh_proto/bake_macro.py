"""Part B: bake macro-only male/female bases using Anny (MPFB2/MakeHuman assets),
local_changes="none" so only the macro phenotypes drive the shape.

This is a proxy for standalone MakeHuman: no bpy/mpfb/makehuman is installed in this
environment, but Anny exposes exactly the MakeHuman macro set on CC0 MPFB2 assets.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("ANNY_CACHE_DIR", str(ROOT / "backend" / ".anny-cache"))
sys.path.insert(0, str(ROOT / "backend"))

import anny  # noqa: E402
import torch  # noqa: E402

OUT = ROOT / "tools" / "mh_proto" / "out"
OUT.mkdir(parents=True, exist_ok=True)

MACROS = {
    "female": {"gender": 0.0, "age": 0.5, "muscle": 0.6, "weight": 0.5, "height": 0.5, "proportions": 0.5},
    "male": {"gender": 1.0, "age": 0.5, "muscle": 0.6, "weight": 0.5, "height": 0.5, "proportions": 0.5},
}


def to_avatar_frame(v):
    return np.column_stack([v[:, 0], v[:, 2], -v[:, 1]])


def normalise(v):
    v = v - v.min(axis=0)
    v = v * (1.0 / (v[:, 1].max() - v[:, 1].min()))
    v[:, 0] -= (v[:, 0].min() + v[:, 0].max()) / 2
    v[:, 2] -= (v[:, 2].min() + v[:, 2].max()) / 2
    v[:, 1] -= v[:, 1].min()
    return v


t0 = time.time()
model = anny.Anny(topology="anny", local_changes="none").to(dtype=torch.float32)
print(f"loaded {time.time()-t0:.1f}s; phenotypes={list(model.phenotype_labels)}; local={len(model.local_change_labels)}")
pose = torch.eye(4)[None, None].repeat(1, model.bone_count, 1, 1)
faces = model.faces if isinstance(model.faces, np.ndarray) else model.faces.detach().cpu().numpy()
faces = np.asarray(faces, dtype=np.int32)

for sex, kwargs in MACROS.items():
    out = model(pose_parameters=pose, phenotype_kwargs=kwargs, local_changes_kwargs={})
    v = normalise(to_avatar_frame(out["vertices"][0].detach().cpu().numpy().astype(float)))
    np.save(OUT / f"{sex}_macro.npy", v.astype(np.float32))
    print(sex, "saved", v.shape, "vert count", v.shape[0])

np.save(OUT / "faces.npy", faces)
print("wrote", OUT, "faces", faces.shape)
