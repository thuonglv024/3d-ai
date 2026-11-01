"""Chẩn đoán vòng eo bị từ chối — chỉ đọc, không sửa pipeline.

Với hai ảnh + chiều cao, in ra từng hàng thân (fractions, width_cm, depth_cm),
dải eo, các ngưỡng từ chối hiện tại và lý do cuối cùng. Mục đích là biết vì sao
`waist_cm` ra None bằng số đo, không phải đoán.

    backend/.venv/Scripts/python.exe scripts/eval/waist_diag.py \
        --front backend/data/pilot_selfie/P01b_front.png \
        --side  backend/data/pilot_selfie/P01b_second.png \
        --height 156 --sex female

Kết quả JSON mặc định nằm ở ``output/measure-debug/waist_diag_<tên>.json``.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.anatomy import template_landmarks  # noqa: E402
from app.camera_fusion import synchronized_torso_profile as torso_profile  # noqa: E402
from app.images import InvalidPhoto, decode_photo  # noqa: E402
from app.measurements import (  # noqa: E402
    DEPTH_FLAT_CM,
    WAIST_MIN_TAPER_CM,
    closed_torso_section,
    ellipse_perimeter,
    estimate_from_profiles,
)
from app.reconstruction import (  # noqa: E402
    TEMPLATE_BLEND_FROM,
    TEMPLATE_PATH,
    close_detector,
    get_detector,
    observe,
    read_template,
    reconstruct,
)
from app.torso_mask import more_visible_arm_side  # noqa: E402


def _arrays_from_profile(profile: dict | None):
    if not profile or not (profile.get("fitting") or {}).get("fractions"):
        return None
    fitting = profile["fitting"]
    return (
        np.asarray(fitting["fractions"], dtype=float),
        np.asarray(fitting["widths"], dtype=float),
        np.asarray(fitting["depths"], dtype=float),
    )


def _arrays_from_photos(front: np.ndarray, side: np.ndarray, height_cm: float, mode: str, sex: str):
    """Dựng lại đúng các mảng mà reconstruct() đưa vào estimate_from_profiles."""
    detector = get_detector()
    frontal = observe(front, detector, "chính diện", mode)
    lateral = observe(side, detector, "góc nghiêng", mode)
    fractions, widths = torso_profile(frontal, reference_obs=None, norm_height=frontal.height)
    if getattr(frontal, "arm_radius_px", None):
        lateral.arm_radius_hint = (
            float(np.mean(list(frontal.arm_radius_px.values())))
            * float(lateral.height) / max(float(frontal.height), 1.0)
        )
    _, depths = torso_profile(
        lateral,
        reference_obs=frontal,
        norm_height=lateral.height,
        arm_sides=(more_visible_arm_side(lateral.points, lateral.visibility),),
    )
    landmarks = template_landmarks(str(TEMPLATE_PATH))
    shoulder_level = float(landmarks.get("shoulder", .805))
    hip_level = float(landmarks.get("hip", .515))
    if mode == "upper_body":
        template = read_template()
        for i in np.flatnonzero(fractions > TEMPLATE_BLEND_FROM):
            level = float(shoulder_level - fractions[i] * (shoulder_level - hip_level))
            _, curve = closed_torso_section(template, level)
            blend = min(1., (fractions[i] - TEMPLATE_BLEND_FROM) / .17)
            widths[i] = widths[i] * (1 - blend) + np.ptp(curve[:, 0]) * blend
            depths[i] = depths[i] * (1 - blend) + np.ptp(curve[:, 2]) * blend
    return fractions, widths, depths, shoulder_level, hip_level


def _target_by_key(targets, key):
    return next((t for t in targets if t["key"] == key), None)


def _fraction_of(target, shoulder_level: float, hip_level: float) -> float:
    return (shoulder_level - float(target["level"])) / max(shoulder_level - hip_level, 1e-9)


def _raw_at(fractions, values, fraction: float) -> float:
    """Value of the array row nearest a target fraction (target levels are exact)."""
    return float(values[int(np.argmin(np.abs(np.asarray(fractions) - fraction)))])


def diagnose(fractions, widths, depths, height_cm, mode: str, shoulder_level: float, hip_level: float):
    diagnostics: dict = {}
    hip_from_template = mode == "upper_body"
    measurements, targets = estimate_from_profiles(
        fractions, widths, depths, height_cm, 0.22, True, shoulder_level, hip_level,
        diagnostics=diagnostics,
        hip_from_template=hip_from_template,
        photo_max_fraction=TEMPLATE_BLEND_FROM if hip_from_template else None,
    )
    waist_selection = diagnostics.get("waist_selection") or {}
    chest = _target_by_key(targets, "chest_cm")
    waist = _target_by_key(targets, "waist_cm")
    hip = _target_by_key(targets, "hip_cm")
    chest_frac = _fraction_of(chest, shoulder_level, hip_level)
    hip_frac = _fraction_of(hip, shoulder_level, hip_level)
    waist_frac = _fraction_of(waist, shoulder_level, hip_level)
    search_high = float(waist_selection.get("search_high_fraction") or max(chest_frac, hip_frac))

    # Raw profile at the three selected rows: this is what the photo actually
    # said before any interpolation, so the flat-depth diagnosis stays visible.
    raw_depths = {
        "chest_cm": _raw_at(fractions, depths, chest_frac) * height_cm,
        "waist_cm": _raw_at(fractions, depths, waist_frac) * height_cm,
        "hip_cm": _raw_at(fractions, depths, hip_frac) * height_cm,
    }
    raw_widths = {
        "chest_cm": _raw_at(fractions, widths, chest_frac) * height_cm,
        "waist_cm": _raw_at(fractions, widths, waist_frac) * height_cm,
        "hip_cm": _raw_at(fractions, widths, hip_frac) * height_cm,
    }
    spread = max(raw_depths.values()) - min(raw_depths.values())
    neighbours = [raw_depths[k] for k in ("chest_cm", "hip_cm")]
    waist_depth_raw = raw_depths["waist_cm"]
    body_like = waist_depth_raw < min(neighbours)
    accepted = waist_selection.get("accepted") is True
    codes = list(waist_selection.get("codes") or [])
    source = (waist_selection.get("source") or ("photo_with_prior" if hip_from_template else "photo_estimate")) if accepted else None

    rows = []
    for frac, width, depth in zip(fractions, widths, depths):
        rows.append({
            "fraction": round(float(frac), 4),
            "level": round(float(shoulder_level - frac * (shoulder_level - hip_level)), 4),
            "width_cm": round(float(width) * height_cm, 2),
            "depth_cm": round(float(depth) * height_cm, 2),
            "ellipse_cm": round(ellipse_perimeter(float(width), float(depth)) * height_cm, 2),
            "in_waist_band": bool(min(chest_frac, hip_frac) < frac < search_high),
            "is_waist_row": bool(abs(frac - waist_frac) < 1e-6),
            "is_chest_row": bool(abs(frac - chest_frac) < 1e-6),
            "is_hip_row": bool(abs(frac - hip_frac) < 1e-6),
        })

    return {
        "mode": mode,
        "height_cm": height_cm,
        "levels": {"shoulder": shoulder_level, "hip": hip_level},
        "rows": rows,
        "band": {
            "chest_fraction": round(chest_frac, 4),
            "hip_fraction": round(hip_frac, 4),
            "waist_fraction": round(waist_frac, 4),
            "search_high_fraction": round(search_high, 4),
            "rows_in_band": int(sum(r["in_waist_band"] for r in rows)),
        },
        "targets": targets,
        "waist_selection": waist_selection,
        "raw_depths_cm": {k: round(v, 2) for k, v in raw_depths.items()},
        "raw_widths_cm": {k: round(v, 2) for k, v in raw_widths.items()},
        "waist_target_depth_cm": round(float(waist.get("depth_cm", 0.0)), 2),
        "depth_spread_cm": round(spread, 2),
        "gates": {
            "refusal_codes": codes,
            "hip_from_template": bool(hip_from_template),
            "taper_required_cm": WAIST_MIN_TAPER_CM,
            "margin_chest_cm": waist_selection.get("margin_chest_cm"),
            "margin_hip_cm": waist_selection.get("margin_hip_cm"),
            "depth_flat_lt_2cm": bool(spread < DEPTH_FLAT_CM),
            "depth_waist_not_below_both": bool(not body_like),
            "source": source,
            "uncertainty_cm": waist_selection.get("uncertainty_cm"),
            "prior_t": waist_selection.get("prior_t"),
        },
        "pipeline_waist_cm": measurements.get("waist_cm"),
        "final_reason": None if accepted else waist_selection.get("reason"),
    }


def _print_report(result: dict, profile: dict | None, recon_error: str | None):
    band = result["band"]
    print(f"\n===== {result['mode']} =====")
    print(
        f"dải eo: fraction {band['chest_fraction']:.3f} (ngực) → {band['hip_fraction']:.3f} (hông), "
        f"tìm trong {band['chest_fraction']:.3f}–{band['search_high_fraction']:.3f}, "
        f"{band['rows_in_band']} hàng; hàng eo chọn {band['waist_fraction']:.3f}"
    )
    print(f"{'frac':>6} {'level':>6} {'width':>7} {'depth':>7} {'C':>7}  dấu")
    for row in result["rows"]:
        marks = []
        if row["is_chest_row"]:
            marks.append("CHEST")
        if row["is_hip_row"]:
            marks.append("HIP" + (" (template)" if result["gates"]["hip_from_template"] else ""))
        if row["is_waist_row"]:
            marks.append("WAIST-SELECTED")
        elif row["in_waist_band"]:
            marks.append("band")
        print(
            f"{row['fraction']:6.3f} {row['level']:6.3f} {row['width_cm']:7.1f} "
            f"{row['depth_cm']:7.1f} {row['ellipse_cm']:7.1f}  {' '.join(marks)}"
        )
    print(
        f"\ndepth thô (cm): {result['raw_depths_cm']}  spread={result['depth_spread_cm']:.1f}; "
        f"depth dùng cho eo={result['waist_target_depth_cm']:.1f}"
    )
    sel = result["waist_selection"]
    print(
        "hàng hẹp nhất trong dải: "
        f"width={sel.get('waist_width_cm')} cm, hẹp hơn ngực {sel.get('margin_chest_cm')} cm, "
        f"hẹp hơn hông {sel.get('margin_hip_cm')} cm "
        f"(cần ≥{WAIST_MIN_TAPER_CM} so ngực"
        + ("" if not result["gates"]["hip_from_template"] else "; bỏ qua hông template")
        + ")"
    )
    print(f"mã từ chối: {result['gates']['refusal_codes'] or '—'}")
    print(
        f"nguồn={result['gates']['source']} ±{result['gates']['uncertainty_cm']} "
        f"(t={result['gates']['prior_t']})"
    )
    print(f"pipeline waist_cm={result['pipeline_waist_cm']!r}")
    print(f"lý do cuối: {result['final_reason']}")
    if recon_error:
        print(f"reconstruct() dừng sớm: {recon_error}")
    if profile:
        print(f"profile.waist_refusal_code: {profile.get('waist_refusal_code')}")
        print(f"profile.waist_unavailable_reason: {profile.get('waist_unavailable_reason')}")
        print(f"profile.clothing_looseness_flag: {profile.get('clothing_looseness_flag')}")
        print(f"profile.clothing_looseness_reasons: {profile.get('clothing_looseness_reasons')}")
        print(f"profile.waist_selection: {json.dumps(profile.get('waist_selection'), ensure_ascii=False)}")
        print("warnings:")
        for warning in profile.get("warnings") or []:
            print(f"  - {warning}")
    else:
        print("profile: không có (reconstruct() raise trước khi trả profile)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--front", required=True, type=Path)
    parser.add_argument("--side", required=True, type=Path)
    parser.add_argument("--height", required=True, type=float)
    parser.add_argument("--sex", default="auto")
    parser.add_argument("--mode", default="both", choices=["full_body", "upper_body", "both"])
    parser.add_argument("--json-dir", type=Path, default=ROOT / "output/measure-debug")
    args = parser.parse_args()

    front = decode_photo(args.front.read_bytes())
    side = decode_photo(args.side.read_bytes())
    modes = ["full_body", "upper_body"] if args.mode == "both" else [args.mode]
    args.json_dir.mkdir(parents=True, exist_ok=True)
    stem = args.front.stem

    payload = {
        "front": str(args.front),
        "side": str(args.side),
        "height_cm": args.height,
        "sex": args.sex,
        "modes": {},
    }
    for mode in modes:
        profile = None
        recon_error = None
        try:
            out = Path(tempfile.mkdtemp()) / "diag.glb"
            _warnings, _measurements, profile = reconstruct(
                front, side, args.height, out, lambda *_a, **_k: None,
                capture_mode=mode, sex=args.sex,
            )
        except InvalidPhoto as error:
            recon_error = str(error)
        arrays = _arrays_from_profile(profile)
        if arrays is None:
            try:
                fractions, widths, depths, shoulder_level, hip_level = _arrays_from_photos(
                    front, side, args.height, mode, args.sex
                )
            except InvalidPhoto as error:
                print(f"\n===== {mode} =====\nkhông dựng được mảng thân: {error}")
                payload["modes"][mode] = {"reconstruct_error": recon_error, "array_error": str(error)}
                continue
        else:
            fractions, widths, depths = arrays
            landmarks = template_landmarks(str(TEMPLATE_PATH))
            shoulder_level = float(landmarks.get("shoulder", .805))
            hip_level = float(landmarks.get("hip", .515))
        result = diagnose(fractions, widths, depths, args.height, mode, shoulder_level, hip_level)
        result["reconstruct_error"] = recon_error
        if profile:
            result["profile"] = {
                "waist_unavailable_reason": profile.get("waist_unavailable_reason"),
                "clothing_looseness_flag": profile.get("clothing_looseness_flag"),
                "clothing_looseness_reasons": profile.get("clothing_looseness_reasons"),
                "waist_selection": profile.get("waist_selection"),
                "warnings": profile.get("warnings"),
            }
        payload["modes"][mode] = result
        _print_report(result, profile, recon_error)

    close_detector()
    suffix = args.mode if args.mode != "both" else "both"
    destination = args.json_dir / f"waist_diag_{stem}_{suffix}.json"
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
