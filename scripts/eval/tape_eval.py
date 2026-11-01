"""Đối chiếu số đo pipeline với tape của một người, in bảng sai số.

Dùng khi có ảnh + số đo thước dây. Mục đích là biết lệch bao nhiêu và ở đâu,
không phải "chỉnh cho khớp": script chỉ đọc, không sửa pipeline.

    backend/.venv/Scripts/python.exe scripts/eval/tape_eval.py \
        --front backend/data/pilot_selfie/P01b_front.png \
        --side  backend/data/pilot_selfie/P01b_second.png \
        --height 156 --sex female \
        --tape chest_cm=80 waist_cm=60 hip_cm=92 shoulder_width_cm=40 bicep_cm=23 forearm_cm=20 thigh_cm=40.5 calf_cm=33
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.images import decode_photo  # noqa: E402
from app.reconstruction import close_detector, reconstruct  # noqa: E402

# Số đo pipeline có khái niệm tương ứng; các khoá khác chỉ được báo là "chưa đo".
MEASURED = {
    "chest_cm": "vòng ngực",
    "waist_cm": "vòng eo",
    "hip_cm": "vòng mông",
    "shoulder_width_cm": "rộng vai",
    "arm_length_cm": "dài tay",
    "bicep_cm": "bắp tay",
    "forearm_cm": "cẳng tay",
    "thigh_cm": "đùi",
    "calf_cm": "bắp chân",
}


def parse_tape(pairs: list[str]) -> dict[str, float]:
    tape: dict[str, float] = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        if not _:
            raise SystemExit(f"tape phải có dạng key=value, nhận được: {pair}")
        tape[key.strip()] = float(value)
    return tape


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--front", required=True, type=Path)
    parser.add_argument("--side", required=True, type=Path)
    parser.add_argument("--height", required=True, type=float)
    parser.add_argument("--sex", default="auto")
    parser.add_argument("--mode", default="full_body", choices=["full_body", "upper_body"])
    parser.add_argument("--tape", nargs="+", required=True)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    tape = parse_tape(args.tape)
    out = Path(tempfile.mkdtemp()) / "eval.glb"
    _steps, measurements, profile = reconstruct(
        decode_photo(args.front.read_bytes()),
        decode_photo(args.side.read_bytes()),
        args.height,
        out,
        lambda *_a, **_k: None,
        capture_mode=args.mode,
        sex=args.sex,
    )
    close_detector()

    rows = []
    mismatches = 0
    for key, label in MEASURED.items():
        value = measurements.get(key)
        truth = tape.get(key)
        if value is None and truth is None:
            continue
        error = None if (value is None or truth is None) else round(float(value) - truth, 1)
        if error is not None and abs(error) > 2.0:
            mismatches += 1
        rows.append((label, key, value, truth, error))

    print(f"{'mốc':10s} {'pipeline':>9s} {'tape':>7s} {'lệch':>7s}  ghi chú")
    for label, key, value, truth, error in rows:
        shown = "—" if value is None else f"{float(value):.1f}"
        truth_shown = "—" if truth is None else f"{truth:.1f}"
        err_shown = "—" if error is None else f"{error:+.1f}"
        if key not in ("chest_cm", "waist_cm", "hip_cm", "shoulder_width_cm", "arm_length_cm", "bicep_cm", "forearm_cm"):
            note = "chưa đo trong pipeline"
        elif value is None:
            if key == "waist_cm":
                note = profile.get("waist_unavailable_reason")
            elif key in ("bicep_cm", "forearm_cm"):
                note = (profile.get("arm_measurements") or {}).get("reason") or "không tách được tay, hoặc bán kính ngoài 2–8 cm"
            else:
                note = "không đủ dữ kiện"
        elif truth is None:
            note = "không có tape"
        elif abs(error) > 2.0:
            note = "lệch > 2 cm"
        else:
            note = ""
        print(f"{label:10s} {shown:>9s} {truth_shown:>7s} {err_shown:>7s}  {textwrap.shorten(note, 60)}")

    print(f"\nmốc lệch > 2 cm: {mismatches}")
    if profile.get("waist_unavailable_reason"):
        print(f"eo: {profile['waist_unavailable_reason']}")

    if args.json:
        import json

        payload = {
            "tape": tape,
            "measurements": {key: measurements.get(key) for key in MEASURED},
            "rows": [
                {"key": key, "pipeline": value, "tape": truth, "error": error}
                for _, key, value, truth, error in rows
            ],
            "shoulder_source": profile.get("shoulder_width_source"),
            "waist_unavailable_reason": profile.get("waist_unavailable_reason"),
        }
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
