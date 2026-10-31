"""Evaluate the existing MORPH pipeline on the P01b real-subject pilot photos.

Read-only with respect to ``backend/app``.  This script imports the production
functions and writes artefacts under ``output/eval_pilot/`` only.

Two layers are recorded separately so the pipeline failure stays visible:
  * ``reconstruct()`` - the production call, including its own guards;
  * measurement stage - observe -> scale fusion -> torso profile -> ellipse
    estimates, i.e. the exact code reconstruct runs before the avatar fit.

Run:
    backend/.venv/Scripts/python.exe scripts/eval/eval_pilot.py
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
PILOT = BACKEND / "data" / "pilot_selfie"
OUT = ROOT / "output" / "eval_pilot"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(BACKEND))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import anny_body  # noqa: E402
from app.camera_fusion import aligned_torso_landmarks, fuse_camera_scale  # noqa: E402
from app.catalog_seed_data import TOP_CHART_ROWS  # noqa: E402
from app.fitmap import compute_fit_map  # noqa: E402
from app.measurements import closed_torso_section, estimate_from_profiles  # noqa: E402
from app.reconstruction import (  # noqa: E402
    build_from_measurements,
    close_detector,
    get_detector,
    observe,
    reconstruct,
    torso_profile,
)
from app.torso_mask import clothing_looseness, more_visible_arm_side, row_arm_merged  # noqa: E402

FRONT_PATH = PILOT / "P01b_front.png"
SIDE_PATH = PILOT / "P01b_second.png"
GT_PATH = PILOT / "ground_truth.json"
A03_PATH = PILOT / "garment_spec.json"

HEIGHT_CM = 156.0
CROP_PAD_X = 100
SIZES = ["S", "M", "L", "XL", "XXL"]
A03_SIZES = {r["size"]: r for r in json.loads(A03_PATH.read_text(encoding="utf-8"))["sizes"]}
GT = json.loads(GT_PATH.read_text(encoding="utf-8"))
GT_M = GT["measurements_cm"]
TAPE = {
    "height_cm": GT["height_cm"],
    "shoulder_width_cm": GT_M["shoulder_width_cm"],
    "chest_cm": GT_M["chest_cm"],
    "waist_cm": GT_M["waist_cm"],
    "hip_cm": GT_M["hip_cm"],
}
METRIC_LABEL = {
    "height_cm": "Chiều cao",
    "shoulder_width_cm": "Rộng vai",
    "chest_cm": "Ngực",
    "waist_cm": "Eo",
    "hip_cm": "Hông",
}
ROW_COLOR = {"chest_cm": (255, 210, 0), "waist_cm": (0, 210, 255), "hip_cm": (255, 80, 220)}


# --------------------------------------------------------------------------- #
# Image I/O and crop
# --------------------------------------------------------------------------- #
def load_rgb_white(path: Path) -> np.ndarray:
    image = Image.open(path)
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        image = Image.alpha_composite(background, rgba)
    return np.ascontiguousarray(image.convert("RGB"))


def crop_upper_body(rgb: np.ndarray, obs, pad_x: int = CROP_PAD_X):
    """Portrait-style crop: above the head to the hip, subject horizontally padded.

    The full 941-px-wide frame makes MediaPipe miss the side pose; the app's
    webcam frame is portrait, so padding the subject bbox reproduces that.
    """
    ys, xs = np.where(obs.mask)
    shoulder_y = float(obs.points[[11, 12], 1].mean())
    hip_y = float(obs.points[[23, 24], 1].mean())
    torso = max(hip_y - shoulder_y, 1.0)
    y0 = max(0, int(round(obs.top - 0.10 * torso)))
    y1 = min(rgb.shape[0], int(round(hip_y + 0.10 * torso)))
    x0 = max(0, int(xs.min()) - pad_x)
    x1 = min(rgb.shape[1], int(xs.max()) + pad_x)
    return np.ascontiguousarray(rgb[y0:y1, x0:x1]), (int(y0), int(y1), int(x0), int(x1))


# --------------------------------------------------------------------------- #
# The measurement stage reconstruct() runs before building the avatar
# --------------------------------------------------------------------------- #
def measurement_stage(front, side, height_cm: float, capture_mode: str, detector) -> dict:
    frontal = observe(front, detector, "chính diện", capture_mode)
    lateral = observe(side, detector, "góc nghiêng", capture_mode)
    shared_height = fuse_camera_scale(frontal, lateral)
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
    shoulder_ratio = abs(frontal.points[11, 0] - frontal.points[12, 0]) / frontal.height
    measurements, targets = estimate_from_profiles(
        fractions, widths, depths, height_cm, shoulder_ratio, True, 0.805, 0.534
    )
    phenotype_measurements = dict(measurements)
    if capture_mode == "upper_body":
        measurements["hip_cm"] = None
    sex, sex_source = "female", "auto"
    weight, muscle = anny_body.phenotype_from_measurements(phenotype_measurements, height_cm)
    base_mesh = anny_body.build(sex, weight, muscle, height_cm)
    bases, factors = {}, {}
    for target in targets:
        current = float(closed_torso_section(base_mesh, target["level"] * height_cm / 100)[0])
        bases[target["key"]] = round(current, 1)
        factors[target["key"]] = round(float(target["target_cm"]) / current, 3)
    merged_rows = {}
    depth_keys = ("chest_cm", "waist_cm") if capture_mode == "upper_body" else ("chest_cm", "waist_cm", "hip_cm")
    f_shoulder, f_hip = aligned_torso_landmarks(frontal)
    shoulder_span_px = float(abs(frontal.points[11, 0] - frontal.points[12, 0]))
    for target in targets:
        if target["key"] not in depth_keys:
            continue
        frac = target_fraction(target, {"shoulder": 0.805, "hip": 0.534})
        row_y = f_shoulder[1] + frac * (f_hip[1] - f_shoulder[1])
        center_x = f_shoulder[0] + frac * (f_hip[0] - f_shoulder[0])
        merged_rows[target["key"]] = row_arm_merged(
            frontal.mask, row_y, center_x, shoulder_span_px, float(frontal.height)
        )
    chest_target = next((t for t in targets if t["key"] == "chest_cm"), None)
    flag, reasons = clothing_looseness(
        float(chest_target["width_cm"]) if chest_target else None,
        measurements.get("shoulder_width_cm"),
        [float(t["depth_cm"]) for t in targets if t["key"] in depth_keys],
        merged_rows,
    )
    return {
        "frontal": frontal,
        "lateral": lateral,
        "shared_height_px": float(shared_height),
        "front_cm_per_px": height_cm / max(float(frontal.height), 1e-9),
        "side_cm_per_px": height_cm / max(float(lateral.height), 1e-9),
        "height_diff_ratio": abs(float(frontal.height) - float(lateral.height)) / max(float(frontal.height), 1e-9),
        "fractions": fractions,
        "widths": widths,
        "depths": depths,
        "measurements": measurements,
        "targets": {t["key"]: t for t in targets},
        "sex": sex,
        "sex_source": sex_source,
        "phenotype": {"weight": round(float(weight), 3), "muscle": round(float(muscle), 3)},
        "anny_base_cm": bases,
        "fit_factor": factors,
        "base_mesh": base_mesh,
        "arm_merged_rows": merged_rows,
        "clothing_looseness_flag": flag,
        "clothing_looseness_reasons": reasons,
        "arm_removal": {
            "front_radius_px": getattr(frontal, "arm_radius_px", {}),
            "side_radius_px": getattr(lateral, "arm_radius_px", {}),
            "warnings": list(getattr(frontal, "arm_removal_warnings", [])) + list(getattr(lateral, "arm_removal_warnings", [])),
        },
    }


def target_fraction(target: dict, levels: dict) -> float:
    shoulder, hip = float(levels["shoulder"]), float(levels["hip"])
    return (shoulder - float(target["level"])) / max(shoulder - hip, 1e-9)


def row_runs(mask: np.ndarray, y: float, center: float) -> dict:
    row = mask[int(np.clip(round(y), 0, mask.shape[0] - 1))]
    padded = np.empty(len(row) + 2, dtype=bool)
    padded[0] = padded[-1] = False
    padded[1:-1] = row
    idx = np.flatnonzero(padded[1:] != padded[:-1])
    starts, ends = idx[0::2], idx[1::2]
    runs = [[int(a), int(b)] for a, b in zip(starts, ends)]
    if not len(runs):
        return {"runs": [], "n_runs": 0, "center_run_px": None, "total_extent_px": None}
    containing = [r for r in runs if r[0] <= center < r[1]]
    chosen = containing[0] if containing else min(runs, key=lambda r: abs((r[0] + r[1]) / 2 - center))
    return {
        "runs": runs,
        "n_runs": len(runs),
        "center_run_px": float(chosen[1] - chosen[0]),
        "total_extent_px": float(runs[-1][1] - runs[0][0]),
    }


def build_diagnostics(stage: dict, levels: dict, height_cm: float, capture_mode: str) -> list[dict]:
    frontal, lateral = stage["frontal"], stage["lateral"]
    front_cm_per_px = stage["front_cm_per_px"]
    side_cm_per_px = stage["side_cm_per_px"]
    f_shoulder, f_hip = aligned_torso_landmarks(frontal)
    s_shoulder, s_hip = aligned_torso_landmarks(lateral, reference_obs=frontal)
    shoulder_span_px = float(abs(frontal.points[11, 0] - frontal.points[12, 0]))
    keys = ["chest_cm", "waist_cm"] if capture_mode == "upper_body" else ["chest_cm", "waist_cm", "hip_cm"]
    out = []
    for key in keys:
        target = stage["targets"].get(key)
        if not target:
            continue
        frac = target_fraction(target, levels)
        y_front = float(f_shoulder[1] + frac * (f_hip[1] - f_shoulder[1]))
        y_side = float(s_shoulder[1] + frac * (s_hip[1] - s_shoulder[1]))
        front_center = float(f_shoulder[0] + frac * (f_hip[0] - f_shoulder[0]))
        side_center = float(s_shoulder[0] + frac * (s_hip[0] - s_shoulder[0]))
        width_px = float(target["width_cm"] / max(front_cm_per_px, 1e-9))
        depth_px = float(target["depth_cm"] / max(side_cm_per_px, 1e-9))
        out.append({
            "key": key,
            "fraction": round(frac, 4),
            "row_front_px": round(y_front, 1),
            "row_side_px": round(y_side, 1),
            "width_px": round(width_px, 1),
            "depth_px": round(depth_px, 1),
            "width_cm": round(float(target["width_cm"]), 1),
            "depth_cm": round(float(target["depth_cm"]), 1),
            "shoulder_span_px": round(shoulder_span_px, 1),
            "excess_over_shoulder_span_cm": round((width_px - shoulder_span_px) * front_cm_per_px, 1),
            "front_runs": row_runs(frontal.mask, y_front, front_center),
            "side_runs": row_runs(lateral.mask, y_side, side_center),
            "arm_merged": row_arm_merged(
                frontal.mask, y_front, front_center, shoulder_span_px, float(frontal.height)
            ),
            "removed_arm_px_front": int(getattr(frontal, "arm_mask", np.zeros_like(frontal.mask)).sum()),
            "removed_arm_px_side": int(getattr(lateral, "arm_mask", np.zeros_like(lateral.mask)).sum()),
        })
    return out


# --------------------------------------------------------------------------- #
# Overlays and mesh rendering
# --------------------------------------------------------------------------- #
def draw_overlay(rgb, obs, diagnostics, path: Path, view: str):
    image = Image.fromarray(rgb.copy())
    draw = ImageDraw.Draw(image)
    edge = obs.mask & ~binary_erosion(obs.mask, iterations=1)
    for y, x in zip(*np.where(edge)):
        image.putpixel((int(x), int(y)), (40, 220, 120))
    arm_mask = getattr(obs, "arm_mask", None)
    if arm_mask is not None and arm_mask.any():
        arm_edge = arm_mask & ~binary_erosion(arm_mask, iterations=1)
        for y, x in zip(*np.where(arm_edge)):
            image.putpixel((int(x), int(y)), (255, 140, 0))
    for i, (x, y) in enumerate(obs.points):
        r = 3 if i in (0, 11, 12, 23, 24, 27, 28) else 2
        draw.ellipse([x - r, y - r, x + r, y + r], outline=(255, 40, 40), width=1)
        if i in (0, 11, 12, 23, 24, 27, 28):
            draw.text((x + 4, y - 8), str(i), fill=(255, 40, 40))
    for d in diagnostics:
        color = ROW_COLOR.get(d["key"], (255, 255, 0))
        row_y = d["row_front_px"] if view == "front" else d["row_side_px"]
        draw.line([(0, row_y), (image.width - 1, row_y)], fill=color, width=2)
        label = f"{d['key']}: w={d['width_px']}px d={d['depth_px']}px"
        if d.get("arm_merged"):
            label += " ARM_MERGED"
        draw.rectangle([4, row_y - 28, 360, row_y - 14], fill=(0, 0, 0))
        draw.text((6, row_y - 27), label, fill=color)
    draw.rectangle([4, 4, 430, 18], fill=(0, 0, 0))
    draw.text((6, 5), "green=clean mask, orange=removed arm capsule", fill=(255, 255, 255))
    image.save(path)
    return path


def render_mesh(mesh, destination: Path, width: int = 420, height: int = 720, view: str = "front"):
    vertices = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=int)
    y = vertices[:, 1]
    if view == "front":
        u, depth_axis = vertices[:, 0], -vertices[:, 2]
    else:
        u, depth_axis = vertices[:, 2], -vertices[:, 0]
    scale = (height * 0.94) / max(float(np.ptp(y)), 1e-9)
    center_u = (float(u.min()) + float(u.max())) / 2.0
    uu = (u - center_u) * scale + width / 2.0
    vv = height * 0.97 - (y - y.min()) * scale
    tri = np.stack([uu, vv], axis=1)[faces]
    p0, p1, p2 = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
    normals = np.cross(p1 - p0, p2 - p0)
    normals = normals / np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
    light = np.array([0.35, 0.55, 0.76])
    light = light / np.linalg.norm(light)
    shade = np.clip(0.30 + 0.70 * np.abs(normals @ light), 0, 1)
    colors = np.stack([shade * 235, shade * 240, shade * 245], axis=1).astype(np.uint8)
    depths = depth_axis[faces]
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    zbuf = np.full((height, width), np.inf, dtype=np.float32)
    for t, z, color in zip(tri, depths, colors):
        x0 = max(int(np.floor(t[:, 0].min())), 0)
        x1 = min(int(np.ceil(t[:, 0].max())), width - 1)
        y0 = max(int(np.floor(t[:, 1].min())), 0)
        y1 = min(int(np.ceil(t[:, 1].max())), height - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs = np.arange(x0, x1 + 1)
        ys = np.arange(y0, y1 + 1)
        X, Y = np.meshgrid(xs, ys)
        (ax, ay), (bx, by), (cx, cy) = t
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        w1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        w2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        w3 = 1.0 - w1 - w2
        inside = (w1 >= -1e-6) & (w2 >= -1e-6) & (w3 >= -1e-6)
        if not inside.any():
            continue
        zz = w1 * z[0] + w2 * z[1] + w3 * z[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        update = inside & (zz < sub)
        if update.any():
            sub[update] = zz[update]
            canvas[y0:y1 + 1, x0:x1 + 1][update] = color
    Image.fromarray(canvas).save(destination)
    return destination


def make_comparison(real_front, real_side, mask_front, mask_side, render_front, render_side, path: Path, labels):
    def crop_subject(rgb, mask, pad=40):
        ys, xs = np.where(mask)
        y0, y1 = max(0, int(ys.min()) - pad), min(rgb.shape[0], int(ys.max()) + pad)
        x0, x1 = max(0, int(xs.min()) - pad), min(rgb.shape[1], int(xs.max()) + pad)
        return Image.fromarray(rgb[y0:y1, x0:x1])

    panels = [crop_subject(real_front, mask_front), Image.open(render_front).convert("RGB"),
              crop_subject(real_side, mask_side), Image.open(render_side).convert("RGB")]
    height = 720
    panels = [p.resize((max(1, int(p.width * height / p.height)), height)) for p in panels]
    gap = 12
    canvas = Image.new("RGB", (sum(p.width for p in panels) + gap * (len(panels) - 1), height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    x = 0
    for label, panel in zip(labels, panels):
        canvas.paste(panel, (x, 0))
        draw.text((x + 6, 4), label, fill=(0, 0, 0))
        x += panel.width + gap
    canvas.save(path)
    return path


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
def build_table(stage: dict, profile: dict | None, capture_mode: str) -> list[dict]:
    sections = {s["key"]: s for s in (profile or {}).get("sections", [])}
    rows = []
    for key in ("height_cm", "shoulder_width_cm", "chest_cm", "waist_cm", "hip_cm"):
        tape = TAPE.get(key)
        if key == "height_cm":
            rows.append({
                "metric": key, "label": METRIC_LABEL[key], "tape_cm": tape,
                "ellipse_cm": None, "pipeline_cm": stage["measurements"].get(key),
                "mesh_cut_cm": round(HEIGHT_CM, 1) if profile else None,
                "mesh_error_cm": 0.0 if profile else None,
                "mesh_error_pct": 0.0 if profile else None,
                "note": "height is the user input scale, not a silhouette measurement",
            })
            continue
        if key == "shoulder_width_cm":
            pipe = stage["measurements"].get(key)
            rows.append({
                "metric": key, "label": METRIC_LABEL[key], "tape_cm": tape,
                "ellipse_cm": None, "pipeline_cm": pipe,
                "mesh_cut_cm": None,
                "mesh_error_cm": round(pipe - tape, 1) if pipe is not None and tape is not None else None,
                "mesh_error_pct": round((pipe - tape) / tape * 100, 1) if pipe is not None and tape is not None else None,
                "note": "landmark breadth (MediaPipe 11-12); no mesh-cut equivalent",
            })
            continue
        target = stage["targets"].get(key)
        pipe = stage["measurements"].get(key)
        mesh = sections.get(key, {}).get("model_cm")
        template_only = key == "hip_cm" and capture_mode == "upper_body"
        rows.append({
            "metric": key, "label": METRIC_LABEL[key], "tape_cm": tape,
            "ellipse_cm": round(float(target["ellipse_cm"]), 1) if target else None,
            "pipeline_cm": pipe,
            "mesh_cut_cm": mesh,
            "mesh_error_cm": round(mesh - tape, 1) if mesh is not None and not template_only and tape is not None else None,
            "mesh_error_pct": round((mesh - tape) / tape * 100, 1) if mesh is not None and not template_only and tape is not None else None,
            "ellipse_error_cm": round(float(target["ellipse_cm"]) - tape, 1) if target and tape is not None else None,
            "ellipse_error_pct": round((float(target["ellipse_cm"]) - tape) / tape * 100, 1) if target and tape is not None else None,
            "source": "template_model" if template_only else ("photo_estimate" if capture_mode == "full_body" else "photo_with_prior"),
            "note": ("hip is template-only in upper_body; excluded from error" if template_only else ""),
        })
    return rows


# --------------------------------------------------------------------------- #
# One mode
# --------------------------------------------------------------------------- #
def run_mode(name: str, front: np.ndarray, side: np.ndarray, height_cm: float,
             capture_mode: str, detector, make_overlays: bool) -> dict:
    print(f"[run] {name}: capture_mode={capture_mode} height={height_cm}")
    destination = OUT / f"{name}.glb"
    started = time.perf_counter()
    profile, measurements, pipeline_error = None, None, None
    try:
        _, measurements, profile = reconstruct(
            front, side, height_cm, destination, lambda stage: None, capture_mode, "auto"
        )
    except Exception as exc:  # noqa: BLE001 - record the production guard verbatim
        pipeline_error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    elapsed = time.perf_counter() - started

    stage = measurement_stage(front, side, height_cm, capture_mode, detector)
    if measurements is None:
        measurements = dict(stage["measurements"])
    levels = {"shoulder": 0.805, "hip": 0.534}
    diagnostics = build_diagnostics(stage, levels, height_cm, capture_mode)
    result = {
        "mode": name,
        "capture_mode": capture_mode,
        "requested_height_cm": height_cm,
        "elapsed_s": round(elapsed, 2),
        "sex": stage["sex"],
        "sex_source": stage["sex_source"],
        "body_model": "anny",
        "phenotype": stage["phenotype"],
        "fit_status": (profile or {}).get("fit_status"),
        "max_fit_error_cm": (profile or {}).get("max_fit_error_cm"),
        "scale_method": (profile or {}).get("scale_method"),
        "shared_height_px": round(stage["shared_height_px"], 1),
        "front_body_px": round(stage["frontal"].height, 1),
        "side_body_px": round(stage["lateral"].height, 1),
        "measurements": measurements,
        "table": build_table(stage, profile, capture_mode),
        "diagnostics": diagnostics,
        "anny_base_cm": stage["anny_base_cm"],
        "fit_factor": stage["fit_factor"],
        "pipeline_error": pipeline_error,
        "glb": str(destination.relative_to(ROOT)) if profile is not None else None,
        "warnings": (profile or {}).get("warnings", []),
        "clothing_looseness_flag": (profile or {}).get("clothing_looseness_flag", stage["clothing_looseness_flag"]),
        "clothing_looseness_reasons": (profile or {}).get("clothing_looseness_reasons", stage["clothing_looseness_reasons"]),
        "arm_merged_rows": (profile or {}).get("arm_merged_rows", stage["arm_merged_rows"]),
        "arm_removal": (profile or {}).get("arm_removal", stage["arm_removal"]),
        "per_image_scale": (profile or {}).get("per_image_scale", {
            "front_cm_per_px": round(stage["front_cm_per_px"], 5),
            "side_cm_per_px": round(stage["side_cm_per_px"], 5),
            "height_diff_ratio": round(stage["height_diff_ratio"], 4),
        }),
    }
    if make_overlays:
        draw_overlay(front, stage["frontal"], diagnostics, OUT / f"overlay_{name}_front_after.png", "front")
        draw_overlay(side, stage["lateral"], diagnostics, OUT / f"overlay_{name}_side_after.png", "side")
        result["overlay_front"] = str((OUT / f"overlay_{name}_front_after.png").relative_to(ROOT))
        result["overlay_side"] = str((OUT / f"overlay_{name}_side_after.png").relative_to(ROOT))
    print(f"[done] {name}: {elapsed:.1f}s error={pipeline_error['message'] if pipeline_error else 'none'} "
          f"chest={measurements.get('chest_cm')} waist={measurements.get('waist_cm')} "
          f"flag={result['clothing_looseness_flag']}")
    return result


def sensitivity_row(stage: dict, height_cm: float) -> dict:
    m, t = stage["measurements"], stage["targets"]
    return {
        "height_cm": height_cm,
        "chest_ellipse_cm": round(float(t["chest_cm"]["ellipse_cm"]), 1),
        "waist_ellipse_cm": round(float(t["waist_cm"]["ellipse_cm"]), 1),
        "hip_ellipse_cm": round(float(t["hip_cm"]["ellipse_cm"]), 1),
        "chest_reported_cm": m.get("chest_cm"),
        "waist_reported_cm": m.get("waist_cm"),
        "hip_reported_cm": m.get("hip_cm"),
        "chest_fit_factor": stage["fit_factor"].get("chest_cm"),
        "waist_fit_factor": stage["fit_factor"].get("waist_cm"),
        "hip_fit_factor": stage["fit_factor"].get("hip_cm"),
    }


# --------------------------------------------------------------------------- #
# A03 ease with the current fitmap logic
# --------------------------------------------------------------------------- #
def a03_fitmap(measurements: dict) -> dict:
    chart_rows = [dict(row) for row in TOP_CHART_ROWS if row["size"] in SIZES]
    chart = {
        "name": "A03 eval (generic top body chart)",
        "garment": "top",
        "source": "illustrative",
        "measurement_basis": "body_cm",
        "rows": chart_rows,
    }

    def variant(multiplier: float) -> list[dict]:
        specs = [{"size": size, "chest_cm": A03_SIZES[size]["chest_flat_cm"] * multiplier} for size in SIZES]
        product = {"chart": chart, "garment_specs": specs, "material": "cotton", "fit": "boxy"}
        out = []
        for size in SIZES:
            result = compute_fit_map(product, size, measurements)
            chest = next((r for r in result["regions"] if r["key"] == "chest_cm"), {})
            out.append({
                "size": size,
                "flat_width_cm": A03_SIZES[size]["chest_flat_cm"],
                "chest_cm_used_by_fitmap": chest.get("garment_estimate_cm"),
                "body_chest_cm": chest.get("body_cm"),
                "ease_cm": chest.get("ease_cm"),
                "verdict": chest.get("verdict"),
                "basis": chest.get("basis"),
                "confidence": result.get("confidence"),
            })
        return out

    tape_measurements = {"chest_cm": 80.0, "waist_cm": 60.0}
    return {
        "height_cm": HEIGHT_CM,
        "pipeline_measurements_used": {"chest_cm": measurements.get("chest_cm"), "waist_cm": measurements.get("waist_cm")},
        "chart_rows_source": "catalog_seed_data.TOP_CHART_ROWS (generic body chart; A03 has no body chest/waist ranges)",
        "fitmap_semantics": (
            "fitmap.py:145-153 assigns garment_cm = size_spec['chest_cm'] directly; "
            "it treats chest_cm as a full garment circumference, not a flat width."
        ),
        "pipeline_body_chest_raw_flat_in_chest_cm": variant(1.0),
        "pipeline_body_chest_doubled_in_chest_cm": variant(2.0),
        "with_tape_chest_80_doubled_in_chest_cm": a03_fitmap_with_tape(tape_measurements, chart),
        "waist_note": "A03 has no waist spec; fitmap's waist row falls back to the generic chart midpoint + boxy ease and is not an A03 value.",
    }


def a03_fitmap_with_tape(measurements: dict, chart: dict) -> list[dict]:
    specs = [{"size": size, "chest_cm": A03_SIZES[size]["chest_flat_cm"] * 2.0} for size in SIZES]
    product = {"chart": chart, "garment_specs": specs, "material": "cotton", "fit": "boxy"}
    out = []
    for size in SIZES:
        result = compute_fit_map(product, size, measurements)
        chest = next((r for r in result["regions"] if r["key"] == "chest_cm"), {})
        out.append({"size": size, "chest_cm_used_by_fitmap": chest.get("garment_estimate_cm"),
                    "body_chest_cm": chest.get("body_cm"), "ease_cm": chest.get("ease_cm"),
                    "verdict": chest.get("verdict"), "basis": chest.get("basis")})
    return out


# --------------------------------------------------------------------------- #
# Before / after comparison (previous JSON is preserved before rerun)
# --------------------------------------------------------------------------- #
def compare_before_after(before_path: Path, after_report: dict) -> dict:
    if not before_path.is_file():
        return {}
    before = json.loads(before_path.read_text(encoding="utf-8"))
    rows = []
    for mode in ("A", "B"):
        b, a = before.get("modes", {}).get(mode), after_report.get("modes", {}).get(mode)
        if not b or not a:
            continue
        bt = {row["metric"]: row for row in b.get("table", [])}
        at = {row["metric"]: row for row in a.get("table", [])}
        bd = {row["key"]: row for row in b.get("diagnostics", [])}
        ad = {row["key"]: row for row in a.get("diagnostics", [])}
        b_merged_rows = {
            key: bool(diag.get("front_runs", {}).get("n_runs") == 1
                      and (diag.get("width_px") or 0) > 1.30 * (diag.get("shoulder_span_px") or 0))
            for key, diag in bd.items()
        }
        b_chest = bd.get("chest_cm", {}).get("width_cm")
        b_shoulder = b.get("measurements", {}).get("shoulder_width_cm")
        b_depths = [bd[k]["depth_cm"] for k in ("chest_cm", "waist_cm", "hip_cm") if k in bd]
        b_flag, b_reasons = clothing_looseness(b_chest, b_shoulder, b_depths, b_merged_rows)
        for metric in ("chest_cm", "waist_cm", "hip_cm"):
            if metric not in bt or metric not in at:
                continue
            bm, am = bd.get(metric, {}), ad.get(metric, {})
            rows.append({
                "mode": mode,
                "metric": metric,
                "before": {
                    "width_cm": bm.get("width_cm"), "depth_cm": bm.get("depth_cm"),
                    "ellipse_cm": bt[metric].get("ellipse_cm"),
                    "pipeline_cm": bt[metric].get("pipeline_cm"),
                    "mesh_cut_cm": bt[metric].get("mesh_cut_cm"),
                    "ellipse_error_cm": bt[metric].get("ellipse_error_cm"),
                    "arm_merged": b_merged_rows.get(metric),
                    "clothing_looseness_flag": b_flag,
                    "flag_reasons": b_reasons,
                    "flag_note": "retrospective: old run had no flag",
                },
                "after": {
                    "width_cm": am.get("width_cm"), "depth_cm": am.get("depth_cm"),
                    "ellipse_cm": at[metric].get("ellipse_cm"),
                    "pipeline_cm": at[metric].get("pipeline_cm"),
                    "mesh_cut_cm": at[metric].get("mesh_cut_cm"),
                    "ellipse_error_cm": at[metric].get("ellipse_error_cm"),
                    "mesh_error_cm": at[metric].get("mesh_error_cm"),
                    "mesh_error_pct": at[metric].get("mesh_error_pct"),
                    "arm_merged": am.get("arm_merged"),
                    "clothing_looseness_flag": a.get("clothing_looseness_flag"),
                    "flag_reasons": a.get("clothing_looseness_reasons"),
                },
            })
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    print(f"pipeline import OK; output -> {OUT}")
    front_rgb = load_rgb_white(FRONT_PATH)
    side_rgb = load_rgb_white(SIDE_PATH)
    detector = get_detector()

    report = {
        "meta": {
            "subject_id": GT.get("subject_id", "P01"),
            "height_cm": HEIGHT_CM,
            "ground_truth": {"height_cm": TAPE["height_cm"], "shoulder_width_cm": TAPE["shoulder_width_cm"],
                             "chest_cm": TAPE["chest_cm"], "waist_cm": TAPE["waist_cm"],
                             "hip_cm": TAPE["hip_cm"], "weight_kg": GT.get("weight_kg"), "sex": GT.get("sex")},
            "engine": "existing backend/app/reconstruction.reconstruct (not modified)",
        },
        "alpha_handling": {
            "source_images": "PNG RGBA",
            "alpha_extrema": "255..255 (fully opaque), so white compositing is pixel-identical here",
            "pipeline_decode": "backend/app/images.py:25 ImageOps.exif_transpose(original).convert('RGB') — alpha is dropped, not composited",
            "pipeline_observe": "backend/app/reconstruction.py:167-169 image[:, :, :3] — alpha channel ignored",
            "eval_preprocess": "RGBA composited over white before calling reconstruct()",
        },
        "modes": {},
        "sensitivity": {},
        "fitmap_a03": {},
        "diagnostic_mesh_from_tape": {},
        "before_after": {},
        "errors": {},
    }

    full_front = observe(front_rgb, detector, "chính diện", "full_body")
    full_side = observe(side_rgb, detector, "góc nghiêng", "full_body")
    crop_front, crop_box_front = crop_upper_body(front_rgb, full_front)
    crop_side, crop_box_side = crop_upper_body(side_rgb, full_side)
    Image.fromarray(crop_front).save(OUT / "mode_b_front_crop.png")
    Image.fromarray(crop_side).save(OUT / "mode_b_side_crop.png")
    report["upper_body_crop"] = {
        "front_yxyx_px": crop_box_front,
        "side_yxyx_px": crop_box_side,
        "rule": "head top - 10% torso to hip landmark + 10% torso; x = mask bbox +- 100 px",
    }

    jobs = [
        ("A", front_rgb, side_rgb, HEIGHT_CM, "full_body", True),
        ("B", crop_front, crop_side, HEIGHT_CM, "upper_body", True),
    ]
    for name, f, s, h, mode, overlays in jobs:
        try:
            report["modes"][name] = run_mode(name, f, s, h, mode, detector, overlays)
        except Exception as exc:  # noqa: BLE001
            report["errors"][name] = {"type": type(exc).__name__, "message": str(exc),
                                      "traceback": traceback.format_exc()}
            print(f"[error] {name}: {type(exc).__name__}: {exc}")

    # Height sensitivity, mode B: full reconstruct at each height (the fit guard
    # no longer rejects this subject after per-image scale + arm removal).
    sens = {"heights_cm": [153.0, 156.0, 159.0], "rows": {},
            "note": "upper-body reconstruct at each height; hip remains template-only"}
    for height in (153.0, 156.0, 159.0):
        stage = measurement_stage(crop_front, crop_side, height, "upper_body", detector)
        row = sensitivity_row(stage, height)
        try:
            _, sens_measurements, sens_profile = reconstruct(
                crop_front, crop_side, height, OUT / f"B_{int(height)}.glb",
                lambda _stage: None, "upper_body", "auto",
            )
            sections = {s["key"]: s["model_cm"] for s in sens_profile.get("sections", [])}
            row.update({
                "reconstruct": "ok",
                "mesh_chest_cm": sections.get("chest_cm"),
                "mesh_waist_cm": sections.get("waist_cm"),
                "mesh_hip_cm": sections.get("hip_cm"),
                "mesh_error_chest_cm": round(sections["chest_cm"] - TAPE["chest_cm"], 1) if sections.get("chest_cm") else None,
                "mesh_error_waist_cm": round(sections["waist_cm"] - TAPE["waist_cm"], 1) if sections.get("waist_cm") else None,
                "clothing_looseness_flag": sens_profile.get("clothing_looseness_flag"),
                "arm_merged_rows": sens_profile.get("arm_merged_rows"),
                "reported": sens_measurements,
            })
        except Exception as exc:  # noqa: BLE001
            row["reconstruct"] = f"{type(exc).__name__}: {exc}"
        sens["rows"][str(int(height))] = row
    base = sens["rows"]["156"]
    for key in ("153", "159"):
        sens["rows"][key]["delta_vs_156_cm"] = {
            metric: round(sens["rows"][key][f"{metric}_ellipse_cm"] - base[f"{metric}_ellipse_cm"], 2)
            for metric in ("chest", "waist", "hip")
        }
        sens["rows"][key]["mesh_delta_vs_156_cm"] = {
            metric: round(sens["rows"][key].get(f"mesh_{metric}_cm") - base.get(f"mesh_{metric}_cm"), 2)
            if sens["rows"][key].get(f"mesh_{metric}_cm") is not None and base.get(f"mesh_{metric}_cm") is not None else None
            for metric in ("chest", "waist", "hip")
        }
    report["sensitivity"] = sens

    if "B" in report["modes"]:
        report["fitmap_a03"] = a03_fitmap(report["modes"]["B"]["measurements"])

    # Diagnostic only: the mesh basis fitted to tape values, to separate the
    # template's fidelity from the photo-estimate error. Not a scan output.
    tape_measurements = {"chest_cm": 80.0, "waist_cm": 60.0, "hip_cm": 92.0,
                         "shoulder_width_cm": 40.0, "height_cm": 156.0}
    try:
        tape_profile = build_from_measurements(tape_measurements, HEIGHT_CM, "female", "upper_body",
                                               OUT / "diagnostic_tape_fit.glb")
        report["diagnostic_mesh_from_tape"] = {
            "label": "diagnostic only: Anny mesh fitted to tape values, not a scan result",
            "fit_status": tape_profile.get("fit_status"),
            "max_fit_error_cm": tape_profile.get("max_fit_error_cm"),
            "phenotype": tape_profile.get("body_model_prior"),
            "sections": [{k: s[k] for k in ("key", "target_cm", "model_cm", "fit_error_cm")}
                         for s in tape_profile.get("sections", [])],
        }
    except Exception as exc:  # noqa: BLE001
        report["diagnostic_mesh_from_tape"] = {"error": f"{type(exc).__name__}: {exc}"}
        tape_profile = None

    # Meshes for visual comparison: the pre-fit Anny prior and the tape-fit.
    prior = report["modes"].get("B", {}).get("phenotype") or {"weight": 0.5, "muscle": 0.45}
    prior_mesh = anny_body.build("female", float(prior["weight"]), float(prior["muscle"]), HEIGHT_CM)
    render_mesh(prior_mesh, OUT / "mesh_prior_front.png", view="front")
    render_mesh(prior_mesh, OUT / "mesh_prior_side.png", view="side")
    crop_front_obs = observe(crop_front, detector, "chính diện", "upper_body")
    crop_side_obs = observe(crop_side, detector, "góc nghiêng", "upper_body")
    if "B" in report["modes"]:
        make_comparison(
            crop_front, crop_side, crop_front_obs.mask, crop_side_obs.mask,
            OUT / "mesh_prior_front.png", OUT / "mesh_prior_side.png",
            OUT / "mesh_vs_photo_B_prior.png",
            ["photo front", "Anny prior front", "photo side", "Anny prior side"],
        )
        report["modes"]["B"]["mesh_comparison_prior"] = str((OUT / "mesh_vs_photo_B_prior.png").relative_to(ROOT))
    if "A" in report["modes"]:
        make_comparison(
            front_rgb, side_rgb, full_front.mask, full_side.mask,
            OUT / "mesh_prior_front.png", OUT / "mesh_prior_side.png",
            OUT / "mesh_vs_photo_A_prior.png",
            ["photo front", "Anny prior front", "photo side", "Anny prior side"],
        )
        report["modes"]["A"]["mesh_comparison_prior"] = str((OUT / "mesh_vs_photo_A_prior.png").relative_to(ROOT))
    if tape_profile is not None:
        import trimesh
        tape_mesh = trimesh.load(OUT / "diagnostic_tape_fit.glb", force="mesh")
        render_mesh(tape_mesh, OUT / "mesh_tape_front.png", view="front")
        render_mesh(tape_mesh, OUT / "mesh_tape_side.png", view="side")
        make_comparison(
            crop_front, crop_side, crop_front_obs.mask, crop_side_obs.mask,
            OUT / "mesh_tape_front.png", OUT / "mesh_tape_side.png",
            OUT / "mesh_vs_photo_B_tape.png",
            ["photo front", "tape-fit mesh", "photo side", "tape-fit mesh"],
        )
        report["diagnostic_mesh_from_tape"]["comparison"] = str((OUT / "mesh_vs_photo_B_tape.png").relative_to(ROOT))

    report["before_after"] = compare_before_after(OUT / "eval_pilot_before.json", report)
    for row in report["before_after"].get("rows", []):
        b, a = row["before"], row["after"]
        print(
            f"[before/after] {row['mode']} {row['metric']}: "
            f"w {b['width_cm']}->{a['width_cm']} d {b['depth_cm']}->{a['depth_cm']} "
            f"ellipse {b['ellipse_cm']}->{a['ellipse_cm']} "
            f"mesh {b['mesh_cut_cm']}->{a['mesh_cut_cm']} "
            f"arm_merged {b['arm_merged']}->{a['arm_merged']} "
            f"flag {b['clothing_looseness_flag']}->{a['clothing_looseness_flag']}"
        )

    (OUT / "eval_pilot.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    close_detector()
    print(f"[saved] {OUT / 'eval_pilot.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
