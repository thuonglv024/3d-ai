"""Export a fixed male/female archetype set for visual and metric review.

Run from the repo root:

    backend/.venv/Scripts/python.exe verification/scripts/qa_export_avatars.py

Writes ``output/runs/qa-avatars/<sex>-<archetype>.glb`` plus ``metrics.json`` so any
change to the avatar engine can be compared against a known baseline.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app import anny_body  # noqa: E402
from app.anatomy import template_landmarks  # noqa: E402
from app.measurements import closed_torso_section, estimate_from_profiles, fit_measurement_targets, validate_glb_mesh  # noqa: E402
from app.reconstruction import TEMPLATE_PATH, deform_template, read_template  # noqa: E402

HEIGHT_CM = 170.0
FRACTIONS = np.linspace(0.12, 1.12, 35)
ARCHETYPES = {
    "slim": (0.185, 0.125),
    "standard": (0.200, 0.140),
    "broad": (0.225, 0.155),
}


def profile(width: float, depth: float) -> tuple[np.ndarray, np.ndarray]:
    taper = 1.0 - 0.18 * np.sin(np.clip((FRACTIONS - 0.12) / 1.0, 0, 1) * np.pi)
    return width * taper, depth * taper


def main() -> int:
    landmarks = template_landmarks(str(TEMPLATE_PATH))
    shoulder_level, hip_level = landmarks["shoulder"], landmarks["hip"]
    levels = (shoulder_level, hip_level)
    template = read_template()
    anny_ready, _ = anny_body.available()
    out = ROOT / "output" / "runs" / "qa-avatars"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (width, depth) in ARCHETYPES.items():
        widths, depths = profile(width, depth)
        measurements, targets = estimate_from_profiles(
            FRACTIONS, widths, depths, HEIGHT_CM, 0.24, True, shoulder_level, hip_level
        )
        shoulder = measurements["shoulder_width_cm"]
        for sex in ("female", "male"):
            if anny_ready:
                weight, muscle = anny_body.phenotype_from_measurements(measurements, HEIGHT_CM)
                mesh = anny_body.build(sex, weight, muscle, HEIGHT_CM)
                width_targets = []
            else:
                mesh = deform_template(template, FRACTIONS, widths, depths, HEIGHT_CM, sex, levels)
                width_targets = [
                    {"key": "shoulder_width_cm", "kind": "width", "level": shoulder_level,
                     "target_cm": shoulder, "width_cm": shoulder, "blend": 0.6}
                ]
            mesh, body = fit_measurement_targets(mesh, targets, HEIGHT_CM, width_targets)
            path = out / f"{sex}-{name}.glb"
            mesh.export(path, file_type="glb", include_normals=True)
            _, shoulder_curve = closed_torso_section(mesh, shoulder_level * HEIGHT_CM / 100)
            rows.append({
                "sex": sex,
                "archetype": name,
                "body_model": "anny" if anny_ready else "template",
                "shoulder_width_cm": round(float(np.ptp(shoulder_curve[:, 0]) * 100), 1),
                "reported_shoulder_cm": shoulder,
                "fit_error_cm": body["max_fit_error_cm"],
                "fit_status": body["fit_status"],
                "mesh_valid": validate_glb_mesh(mesh, HEIGHT_CM, body["sections"])["valid"],
                "file": str(path.relative_to(ROOT)),
            })
    payload = {"height_cm": HEIGHT_CM, "body_model": "anny" if anny_ready else "template", "levels": {"shoulder": shoulder_level, "hip": hip_level}, "avatars": rows}
    (out / "metrics.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    for row in rows:
        print(
            f"{row['sex']:6s} {row['archetype']:9s} shoulder={row['shoulder_width_cm']:5.1f}cm "
            f"(reported {row['reported_shoulder_cm']:4.1f}) fit={row['fit_error_cm']} "
            f"{row['fit_status']} valid={row['mesh_valid']}"
        )
    print(f"{len(rows)} avatars -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
