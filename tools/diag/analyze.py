"""Summarise the 2 cm cross-section scans, build the frozen baseline, and check
future steps against tools/diag/thresholds.json.

Usage:
    python tools/diag/analyze.py                         # human-readable report
    python tools/diag/analyze.py --make-baseline RUN1 RUN2
    python tools/diag/analyze.py --check [--current METRICS_JSON]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "diag" / "out"
BASELINE = ROOT / "tools" / "diag" / "baseline.json"
THRESHOLDS = ROOT / "tools" / "diag" / "thresholds.json"

CASES = {
    "a_male_average": 175.0,
    "b_female_slim": 162.0,
    "c_male_obese": 172.0,
}
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
WINDOW_CM = 3.0


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def detailed_report() -> None:
    for case, height in CASES.items():
        path = OUT / f"{case}_d2.json"
        if not path.is_file():
            continue
        rows = load_json(path)
        z = np.array([r["z_cm"] for r in rows])
        d2 = np.array([r["d2_cm"] for r in rows])
        pct = np.array([r["d2_pct"] for r in rows])
        print(f"\n### {case} (H={height} cm)")
        print("top peaks:")
        for idx in np.argsort(-np.abs(d2))[:15]:
            print(f"  z={z[idx]:6.1f}  z/H={z[idx]/height:.3f}  P={rows[idx]['perimeter_cm']:7.1f}  d2={d2[idx]:8.2f}  pct={pct[idx]:6.2f}  loops={rows[idx]['loops']}")
        baseline = float(np.median(np.abs(d2)))
        print("feature windows (max |d2| within +/-3 cm):")
        for name, level in FEATURES.items():
            target = level * height
            mask = np.abs(z - target) <= WINDOW_CM
            if not mask.any():
                continue
            local = np.abs(d2[mask])
            print(f"  {name:11s} z~{target:6.1f}  max|d2|={local.max():7.2f}  ratio_vs_median={local.max()/max(baseline,1e-6):5.1f}")
        for label, lo, hi in [("feet", 0, .06), ("legs", .06, .40), ("hip/thigh", .40, .56), ("waist", .56, .66), ("chest", .66, .80), ("shoulder/neck", .80, .88), ("head", .88, 1.0)]:
            mask = (z / height >= lo) & (z / height < hi)
            if mask.any():
                print(f"  region {label:14s} max|d2|={np.abs(d2[mask]).max():7.2f}  mean|d2|={np.abs(d2[mask]).mean():6.2f}  n={mask.sum()}")
        print(f"  median|d2|={baseline:.2f} cm")


def make_baseline(run1_path: str, run2_path: str) -> int:
    run1 = load_json(Path(run1_path))
    run2 = load_json(Path(run2_path))
    if run1.get("cases", {}).keys() != run2.get("cases", {}).keys():
        print("FAIL: hai lần chạy không cùng bộ case")
        return 2
    max_diff = 0.0
    for case, metrics1 in run1["cases"].items():
        metrics2 = run2["cases"][case]
        for key, value1 in metrics1.items():
            if key == "build_s" or key not in metrics2:
                continue
            value2 = metrics2[key]
            if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                diff = abs(float(value1) - float(value2))
                max_diff = max(max_diff, diff)
                if diff >= 0.01:
                    print(f"FAIL: {case}.{key} lệch {diff:.4f} (run1={value1}, run2={value2})")
    if max_diff >= 0.01:
        print(f"FAIL: sai khác lớn nhất {max_diff:.4f} >= 0.01 cm; không ghi baseline")
        return 2
    baseline = {
        "schema": 1,
        "step": 1,
        "cases": run1["cases"],
        "verification": {
            "runs": [str(run1_path), str(run2_path)],
            "max_diff_cm": round(max_diff, 6),
            "epsilon_cm": 0.01,
            "build_s_excluded_from_diff": True,
        },
    }
    BASELINE.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PASS: sai khác lớn nhất {max_diff:.6f} < 0.01 cm; đã ghi {BASELINE}")
    return 0


def _compare(current: float, baseline: float, op: str, value) -> tuple[bool, str]:
    if op == "max":
        return current <= value, f"{current:.3f} <= {value}"
    if op == "min":
        return current >= value, f"{current:.3f} >= {value}"
    if op == "between":
        low, high = value
        return low <= current <= high, f"{low} <= {current:.3f} <= {high}"
    if op == "eq":
        return abs(current - value) <= 1e-9, f"{current:.3f} == {value}"
    if op == "ratio_max_vs_baseline":
        if baseline == 0:
            return False, "baseline=0"
        ratio = current / baseline
        return ratio <= value, f"ratio={ratio:.3f} <= {value} (baseline={baseline:.3f})"
    if op == "ratio_min_vs_baseline":
        if baseline == 0:
            return False, "baseline=0"
        ratio = current / baseline
        return ratio >= value, f"ratio={ratio:.3f} >= {value} (baseline={baseline:.3f})"
    return False, f"unknown op {op}"


def check(current_path: str | None = None) -> int:
    baseline = load_json(BASELINE)
    thresholds = load_json(THRESHOLDS)
    current = load_json(Path(current_path)) if current_path else baseline

    passed = failed = skipped = 0
    for check in thresholds.get("checks", []):
        cases = list(baseline["cases"]) if check.get("case") == "*" else [check["case"]]
        for case in cases:
            metric = check["metric"]
            base_value = (baseline["cases"].get(case) or {}).get(metric)
            current_value = (current["cases"].get(case) or {}).get(metric)
            label = f"step{check['step']} {metric}@{case}"
            if current_value is None or base_value is None:
                print(f"[SKIP] {label}: thiếu metric")
                skipped += 1
                continue
            ok, detail = _compare(float(current_value), float(base_value), check["op"], check["value"])
            print(f"[{'PASS' if ok else 'FAIL'}] {label}: {detail}")
            if ok:
                passed += 1
            else:
                failed += 1
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--make-baseline", nargs=2, metavar=("RUN1", "RUN2"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--current", default=None, help="metrics JSON to compare with baseline")
    args = parser.parse_args()

    if args.make_baseline:
        return make_baseline(args.make_baseline[0], args.make_baseline[1])
    if args.check:
        return check(args.current)
    detailed_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
