"""Diagnostic: build the current avatar pipeline for 3 synthetic bodies and scan
horizontal cross-sections every 2 cm to look for bumps/steps.

This does NOT modify production code. It reuses the same functions the backend
uses when the user edits measurements (refit_avatar), so the mesh is produced by
the current pipeline: Anny basis -> proportional rings -> fit_measurement_targets
-> Laplacian smoothing + re-fit -> GLB.

Run:
    backend/.venv/Scripts/python.exe tools/diag/build_and_scan.py
"""
from __future__ import annotations

import csv
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import app.reconstruction as reconstruction  # noqa: E402
from app import anny_body  # noqa: E402
from app.measurements import closed_torso_section  # noqa: E402
from app.reconstruction import refit_avatar  # noqa: E402

OUT = ROOT / "tools" / "diag" / "out"
OUT.mkdir(parents=True, exist_ok=True)

STEP_M = 0.02  # 2 cm sampling
LEVELS = {"chest_cm": 0.72, "waist_cm": 0.60, "hip_cm": 0.50}
LABELS = {"chest_cm": "Ngực", "waist_cm": "Eo", "hip_cm": "Mông"}


@dataclass
class Case:
    key: str
    sex: str
    height_cm: float
    weight: float
    muscle: float
    chest_cm: float
    waist_cm: float
    hip_cm: float
    shoulder_cm: float


CASES = [
    Case("a_male_average", "male", 175, 0.50, 0.45, 96.0, 82.0, 98.0, 44.0),
    Case("b_female_slim", "female", 162, 0.30, 0.35, 80.0, 64.0, 88.0, 37.0),
    Case("c_male_obese", "male", 172, 0.70, 0.45, 120.0, 110.0, 118.0, 48.0),
]


def build_targets(case: Case) -> list[dict]:
    """Target circumferences + the base mesh's own W/D ratio at each level."""
    h = case.height_cm / 100
    base = anny_body.build(case.sex, case.weight, case.muscle, case.height_cm)
    targets = []
    requested = {"chest_cm": case.chest_cm, "waist_cm": case.waist_cm, "hip_cm": case.hip_cm}
    for key, level in LEVELS.items():
        _, curve = closed_torso_section(base, level * h)
        width_cm = float(np.ptp(curve[:, 0]) * 100)
        depth_cm = float(np.ptp(curve[:, 2]) * 100)
        targets.append({
            "key": key,
            "label": LABELS[key],
            "target_cm": requested[key],
            "width_cm": width_cm,
            "depth_cm": depth_cm,
            "level": level,
        })
    return targets


def build_mesh(case: Case) -> tuple[Path, dict, float, int]:
    targets = build_targets(case)
    measurements = {
        "height_cm": case.height_cm,
        "chest_cm": case.chest_cm,
        "waist_cm": case.waist_cm,
        "hip_cm": case.hip_cm,
        "shoulder_width_cm": case.shoulder_cm,
        "inseam_cm": None,
    }
    fitting = {
        "sex": case.sex,
        "sex_source": "user",
        "capture_mode": "full_body",
        "height_cm": case.height_cm,
        "body_model": "anny",
        "prior": {"weight": case.weight, "muscle": case.muscle},
        "targets": targets,
        "width_targets": [],
        "levels": {"shoulder": 0.805, "hip": 0.534, "neck": 0.855},
        "fractions": [],
        "widths": [],
        "depths": [],
    }
    destination = OUT / f"{case.key}.glb"

    # Count how many fit passes run (direct fit + post-smoothing re-fit). Each
    # pass currently performs 4 PCHIP iterations (documented in K1 §4).
    original_fit = reconstruction.fit_measurement_targets
    fit_calls = 0

    def counted_fit(*args, **kwargs):
        nonlocal fit_calls
        fit_calls += 1
        return original_fit(*args, **kwargs)

    started = time.perf_counter()
    reconstruction.fit_measurement_targets = counted_fit
    try:
        profile = refit_avatar(fitting, measurements, {}, case.height_cm, destination)
    finally:
        reconstruction.fit_measurement_targets = original_fit
    build_s = time.perf_counter() - started

    (OUT / f"{case.key}.profile.json").write_text(
        json.dumps({
            "fit_status": profile.get("fit_status"),
            "max_fit_error_cm": profile.get("max_fit_error_cm"),
            "fit_calls": fit_calls,
            "fit_iterations": fit_calls * 4,
            "build_s": round(build_s, 4),
            "sections": [
                {k: s.get(k) for k in ("key", "target_cm", "model_cm", "fit_error_cm")}
                for s in profile.get("sections", [])
            ],
            "proportional_rings": profile.get("proportional_rings"),
            "mesh_validation": profile.get("mesh_validation"),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return (
        destination,
        profile,
        build_s,
        fit_calls,
        float(next(t for t in targets if t["key"] == "hip_cm")["level"]),
        float((profile.get("levels") or {}).get("hip", 0.0)),
    )


def cross_section(mesh: trimesh.Trimesh, y: float) -> tuple[float, int]:
    """Total perimeter (cm) and number of closed loops at height y (metres)."""
    segments = trimesh.intersections.mesh_plane(mesh, [0, 1, 0], [0, y, 0])
    if len(segments) == 0:
        return 0.0, 0
    total = float(np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1).sum() * 100)
    # Count loops from the segment graph (rounded endpoints).
    points, graph = {}, {}
    for a, b in segments:
        ka, kb = tuple(np.round(a, 6)), tuple(np.round(b, 6))
        if ka == kb:
            continue
        points[ka], points[kb] = a, b
        graph.setdefault(ka, set()).add(kb)
        graph.setdefault(kb, set()).add(ka)
    seen, loops = set(), 0
    for start in graph:
        if start in seen:
            continue
        stack, component = [start], set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            stack.extend(graph[node] - component)
        seen.update(component)
        if len(component) >= 3 and all(len(graph[n]) == 2 for n in component):
            loops += 1
    return total, loops


def scan_mesh(path: Path, height_cm: float) -> list[dict]:
    mesh = trimesh.load(path, force="mesh")
    rows = []
    for z_cm in np.arange(0.0, height_cm + 1e-6, STEP_M * 100):
        total, loops = cross_section(mesh, z_cm / 100)
        rows.append({"z_cm": round(float(z_cm), 2), "perimeter_cm": round(total, 3), "loops": loops})
    return rows


def second_differences(rows: list[dict]) -> list[dict]:
    """Discrete second difference on the 2 cm grid, only across stable loop counts."""
    out = []
    for i in range(1, len(rows) - 1):
        a, b, c = rows[i - 1], rows[i], rows[i + 1]
        if a["loops"] != b["loops"] or b["loops"] != c["loops"]:
            continue
        if min(a["perimeter_cm"], b["perimeter_cm"], c["perimeter_cm"]) <= 0:
            continue
        d2 = c["perimeter_cm"] - 2 * b["perimeter_cm"] + a["perimeter_cm"]
        out.append({
            "z_cm": b["z_cm"],
            "perimeter_cm": b["perimeter_cm"],
            "loops": b["loops"],
            "d2_cm": round(float(d2), 3),
            "d2_pct": round(float(abs(d2) / max(b["perimeter_cm"], 1e-6) * 100), 2),
        })
    return out


def max_abs_d2(rows: list[dict], height_cm: float, level: float, half_window: float = 0.02) -> float:
    """max |d2| inside +/-(half_window * H) around a normalised height."""
    z = np.array([r["z_cm"] for r in rows], dtype=float)
    d2 = np.array([r["d2_cm"] for r in rows], dtype=float)
    mask = np.abs(z / max(height_cm, 1e-6) - level) <= half_window
    return round(float(np.max(np.abs(d2[mask]))), 3) if mask.any() else 0.0


def main() -> int:
    summary = []
    case_metrics: dict[str, dict] = {}
    for case in CASES:
        glb, profile, build_s, fit_calls, hip_level, hip_landmark = build_mesh(case)
        mesh = trimesh.load(glb, force="mesh")
        height_cm = float(mesh.extents[1] * 100)
        rows = scan_mesh(glb, height_cm)
        d2 = second_differences(rows)
        peaks = sorted(d2, key=lambda r: abs(r["d2_cm"]), reverse=True)[:12]
        csv_path = OUT / f"{case.key}_sections.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["z_cm", "perimeter_cm", "loops"])
            writer.writeheader()
            writer.writerows(rows)
        (OUT / f"{case.key}_d2.json").write_text(json.dumps(d2, ensure_ascii=False, indent=1), encoding="utf-8")
        metrics = {
            "height_cm": round(height_cm, 3),
            "max_fit_error_cm": profile.get("max_fit_error_cm"),
            "fit_status": profile.get("fit_status"),
            "fit_calls": fit_calls,
            "fit_iterations": fit_calls * 4,
            "build_s": round(build_s, 4),
            "hip_level": round(hip_level, 4),
            "hip_landmark_level": round(hip_landmark, 4),
            "d2_0.50": max_abs_d2(d2, height_cm, 0.50),
            "d2_0.60": max_abs_d2(d2, height_cm, 0.60),
            "d2_0.72": max_abs_d2(d2, height_cm, 0.72),
            "d2_0.855": max_abs_d2(d2, height_cm, 0.855),
            "d2_0.405": max_abs_d2(d2, height_cm, 0.405),
            "d2_0.235": max_abs_d2(d2, height_cm, 0.235),
            "mesh_valid": bool((profile.get("mesh_validation") or {}).get("valid")),
        }
        case_metrics[case.key] = metrics
        summary.append({
            "case": case.key,
            "sex": case.sex,
            "height_cm": round(height_cm, 1),
            "requested": {"chest": case.chest_cm, "waist": case.waist_cm, "hip": case.hip_cm},
            "peaks": peaks,
            "max_abs_d2_cm": max((abs(r["d2_cm"]) for r in d2), default=0.0),
            "metrics": metrics,
        })
        print(f"\n== {case.key} ({case.sex}, {height_cm:.1f} cm) ==")
        print(
            f"  fit={metrics['max_fit_error_cm']} cm  build={metrics['build_s']}s  "
            f"fit_calls={fit_calls}  hip_level={metrics['hip_level']}  "
            f"d2[.50/.60/.72/.855]={metrics['d2_0.50']}/{metrics['d2_0.60']}/{metrics['d2_0.72']}/{metrics['d2_0.855']}"
        )
        for peak in peaks[:8]:
            print(f"  z={peak['z_cm']:6.1f} cm  P={peak['perimeter_cm']:7.1f} cm  d2={peak['d2_cm']:8.2f}  ({peak['d2_pct']:.2f}%)  loops={peak['loops']}")

    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "metrics.json").write_text(
        json.dumps({"schema": 1, "step": 1, "cases": case_metrics}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nwrote {OUT / 'summary.json'} and {OUT / 'metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
