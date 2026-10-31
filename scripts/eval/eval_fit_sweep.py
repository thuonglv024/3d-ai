"""Chest-fit sweep for the flat A03 schema (read-only; no fitmap changes here)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
OUT = ROOT / "output" / "eval_pilot"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(BACKEND))

from app.garment_fit import compute_chest_fit, load_spec, recommend_size  # noqa: E402

SPEC_PATH = BACKEND / "data" / "pilot_selfie" / "garment_spec.json"


def main() -> int:
    spec = load_spec(SPEC_PATH)
    bodies = list(range(80, 113, 4))
    rows = []
    print("body | size | circ | ease | label      | borderline")
    print("-----+------+------+------+------------+-----------")
    for body in bodies:
        fit = compute_chest_fit(body, "tape", spec)
        for size in fit["sizes"]:
            rows.append({
                "body_chest_cm": body,
                "size": size["size"],
                "chest_circumference_cm": size["chest_circumference_cm"],
                "ease_cm": size["ease_cm"],
                "label": size["label"],
                "is_borderline": size["is_borderline"],
                "uncertainty_cm": size["uncertainty_cm"],
            })
            mark = "Y" if size["is_borderline"] else "-"
            print(
                f"{body:4d} | {size['size']:4s} | {size['chest_circumference_cm']:4.0f} | "
                f"{size['ease_cm']:4.0f} | {size['label']:10s} | {mark}"
            )

    pilot = recommend_size(80, "tape", 156, None, spec)
    print("\nPilot P01 (chest 80 tape, height 156, weight null):")
    print("  by_ease:", pilot["by_ease"]["status"], "|", pilot["by_ease"]["message"])
    print("  by_height_weight:", pilot["by_height_weight"]["status"], "|",
          pilot["by_height_weight"].get("size") or pilot["by_height_weight"].get("sizes"))
    print("  conflict:", pilot["conflict"], "|", pilot["conflict_reason"])
    print("  S hem from shoulder:", pilot["fit"]["sizes"][0]["hem_height_cm_from_shoulder"],
          "|", pilot["fit"]["sizes"][0]["hem_measurement_point"])

    report = {
        "spec": str(SPEC_PATH.relative_to(ROOT)),
        "body_source": "tape",
        "bodies_cm": bodies,
        "rows": rows,
        "pilot": pilot,
    }
    (OUT / "fit_sweep.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[saved] {OUT / 'fit_sweep.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
