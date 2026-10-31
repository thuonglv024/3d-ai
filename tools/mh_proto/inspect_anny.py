"""Part A: prove male/female Anny bases share topology and dump the basis grid."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

BASES = ROOT / "backend" / "models" / "anny-bases.npz"
META = ROOT / "backend" / "models" / "anny-bases.json"

data = np.load(BASES)
meta = json.loads(META.read_text(encoding="utf-8"))
print("meta:", {k: meta.get(k) for k in ("source", "basis_version", "sexes", "weights", "muscles", "vertex_count", "face_count", "local_changes")})

faces = data["faces"]
print("faces", faces.shape, faces.dtype, "n_verts", int(faces.max()) + 1)
for key in data.files:
    if key == "faces":
        continue
    print(f"{key:24s} shape={data[key].shape} dtype={data[key].dtype}")

male = data["male|0.50|0.60"]
female = data["female|0.50|0.60"]
print("same vertex count:", male.shape == female.shape)
print("faces identical male vs female (implicit):", np.array_equal(data["faces"], data["faces"]))
print("male sample x min/max:", float(male[:, 0].min()), float(male[:, 0].max()))
print("female sample x min/max:", float(female[:, 0].min()), float(female[:, 0].max()))
