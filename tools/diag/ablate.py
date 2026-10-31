"""Ablation for one case: base Anny vs +proportional rings vs full pipeline.

Answers "which stage creates the bumps": the base mesh itself, the secondary-ring
scaling, or the measurement fit/smoothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tools" / "diag"))

from app import anny_body, proportions  # noqa: E402
from app.measurements import closed_torso_section, fit_measurement_targets  # noqa: E402
from build_and_scan import CASES, build_targets, cross_section, second_differences  # noqa: E402

OUT = ROOT / "tools" / "diag" / "out"
CASE = CASES[0]  # male average
FEATURES = {
    "hip_fit": 0.50,
    "waist_fit": 0.60,
    "chest_fit": 0.72,
    "shoulder": 0.805,
    "neck_band": 0.855,
    "head_slice": 0.955,
    "thigh_band": 0.405,
    "calf_band": 0.235,
    "ankle_band": 0.065,
}


def scan(path: Path, height_cm: float) -> list[dict]:
    mesh = trimesh.load(path, force="mesh")
    rows = []
    for z in np.arange(0, height_cm + 1e-6, 2.0):
        total, loops = cross_section(mesh, z / 100)
        rows.append({"z_cm": float(z), "perimeter_cm": total, "loops": loops})
    return second_differences(rows)


def window_peaks(rows: list[dict], height_cm: float) -> dict:
    z = np.array([r["z_cm"] for r in rows])
    d2 = np.array([r["d2_cm"] for r in rows])
    out = {}
    for name, level in FEATURES.items():
        mask = np.abs(z - level * height_cm) <= 3
        out[name] = round(float(np.abs(d2[mask]).max()), 2) if mask.any() else 0.0
    return out


def main() -> None:
    case = CASE
    h_m = case.height_cm / 100
    targets = build_targets(case)
    base = anny_body.build(case.sex, case.weight, case.muscle, case.height_cm)
    base.export(OUT / "ablate_base.glb", file_type="glb", include_normals=True)

    base_mains = {}
    for target in targets:
        base_mains[target["key"]] = closed_torso_section(base, target["level"] * h_m)[0]
    scales = proportions.ring_scales(base_mains, {t["key"]: t["target_cm"] for t in targets})
    prop = base.copy()
    proportions.apply_rings(prop, scales, h_m)
    prop.export(OUT / "ablate_prop.glb", file_type="glb", include_normals=True)

    fitted, _ = fit_measurement_targets(prop.copy(), targets, case.height_cm)
    fitted.export(OUT / "ablate_prop_fit.glb", file_type="glb", include_normals=True)

    result = {}
    for label, path in (
        ("base", OUT / "ablate_base.glb"),
        ("base+prop", OUT / "ablate_prop.glb"),
        ("base+prop+fit", OUT / "ablate_prop_fit.glb"),
        ("full", OUT / "a_male_average.glb"),
    ):
        rows = scan(path, case.height_cm)
        result[label] = {"windows": window_peaks(rows, case.height_cm)}
        (OUT / f"ablate_{label.replace('+', '_')}_d2.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(label, json.dumps(result[label]["windows"], ensure_ascii=False))
    (OUT / "ablation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
