"""Part B: compare macro-only bases vs the current Anny bases."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tools" / "diag"))

from app import anny_body  # noqa: E402
from app.measurements import closed_torso_section  # noqa: E402
from build_and_scan import cross_section, second_differences, max_abs_d2  # noqa: E402

OUT = ROOT / "tools" / "mh_proto" / "out"
H = 1.70
H_CM = 170.0


def mesh_from_npy(path, faces):
    v = np.load(path).astype(float) * H
    v[:, 1] -= v[:, 1].min()
    return trimesh.Trimesh(vertices=v, faces=np.asarray(faces), process=False)


def curves(mesh):
    rows = []
    for z in np.arange(0, H_CM + 1e-6, 2.0):
        total, loops = cross_section(mesh, z / 100)
        rows.append({"z_cm": float(z), "perimeter_cm": total, "loops": loops})
    return rows


def metric(mesh, level, cx=None):
    return closed_torso_section(mesh, level * H, center_x_m=cx * H if cx else None)[0]


faces = np.load(OUT / "faces.npy")
rows = []
for sex in ("male", "female"):
    macro = mesh_from_npy(OUT / f"{sex}_macro.npy", faces)
    anny = anny_body.build(sex, 0.5, 0.6, H_CM)
    for label, mesh in (("macro", macro), ("anny", anny)):
        d2 = second_differences(curves(mesh))
        shoulder_w = float(np.ptp(closed_torso_section(mesh, .805 * H)[1][:, 0]))
        hip_w = float(np.ptp(closed_torso_section(mesh, .534 * H)[1][:, 0]))
        waist_c = metric(mesh, .60)
        hip_c = metric(mesh, .534)
        rows.append({
            "sex": sex, "base": label,
            "verts": len(mesh.vertices), "faces": len(mesh.faces),
            "d2_050": max_abs_d2(d2, H_CM, .50),
            "d2_060": max_abs_d2(d2, H_CM, .60),
            "d2_072": max_abs_d2(d2, H_CM, .72),
            "d2_0855": max_abs_d2(d2, H_CM, .855),
            "shoulder_hip": round(shoulder_w / max(hip_w, 1e-6), 3),
            "leg_ratio": round(1.0 - .534, 3),
            "waist_hip": round(waist_c / max(hip_c, 1e-6), 3),
        })
        print(rows[-1])
