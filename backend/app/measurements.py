"""Photo-derived estimates and closed torso sections. No validated anthropometry."""
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.special import ellipe
import trimesh

from .images import InvalidPhoto


class ClothingOrArmMergedError(InvalidPhoto):
    """The fitted section is too far from the avatar's current section.

    The code lets the API/UI distinguish a loose-clothing/arm-merge capture from
    other invalid-photo failures without inventing a measurement.
    """

    code = "CLOTHING_OR_ARM_MERGED"


def scale_lateral(x, scale, radius):
    """Monotone lateral deformation: scale the trunk and translate outer limbs.

    Blending x * scale by a rapidly falling mask can invert vertex order near
    the armpits. This map keeps a positive derivative for our allowed scales.
    """
    radius = np.maximum(radius, .01)
    return x + (scale - 1) * radius / np.tanh(1) * np.tanh(x / radius)


# Calibration hook for the concavity correction: measured perimeter /
# ellipse perimeter, per level. Values are 1.0 on purpose.
#
# They used to be 1/(1-0.0747) = +8.07% (chest), +3.21% (waist), +6.23% (hip),
# invented in-code from no data. On the only subject with tape measurements
# (P01b, tape chest 80 / waist 60 / hip 92) the chest ellipse was already
# 83.1 cm (+3.1) and the factor pushed it to 89.8 cm: +6.7 cm of a +9.8 cm
# error came from the constant, not the silhouette. Removing them brings the
# chest to +3.1 cm on that subject.
#
# Re-enable only with a fitted value from >=8 tape-measured people, and record
# the sample size and fit method next to the number.
ANATOMICAL_SECTION_FACTORS = {
    "chest_cm": 1.0,
    "waist_cm": 1.0,
    "hip_cm": 1.0,
}
SECTION_FACTORS_CALIBRATED = False

# Natural-waist rule: the narrowest row between the chest and the hip rows is the
# waist only when it is visibly narrower than the neighbours the photo actually
# shows. A straight torso (no real taper) used to yield a "waist" from the window
# minimum anyway; on P01b that produced 83.9 cm against a 60 cm tape waist.
#
# 1.5 cm per side was KEPT after the 2026-11-01 diagnosis
# (scripts/eval/waist_diag.py, output/measure-debug/waist_diag_P01b_front_both.json):
# P01b's front silhouette only narrows 0.45 cm (29.0 -> 28.9 cm), inside the
# 0.2-0.6 cm row-to-row noise of that profile, while cases with a real visible
# waist (3 synthetic QA archetypes) narrow 7.95-10.68 cm. No sample lies in the
# 0.45-7.95 cm gap, so lowering the threshold to accept P01b would be fitting a
# constant to one unmeasurable photo (loose sweatshirt), not calibration.
WAIST_MIN_TAPER_CM = 1.5
# A measured waist depth must be the minimum of the photo-observed neighbours;
# no cm margin is imposed because the frontal width, not the side view, locates
# the row. On the female-slim QA render the side profile bottoms out 0.7 cm
# below the hip, and a fixed 1 cm margin rejected a valid waist.
DEPTH_FLAT_CM = 2.0

WAIST_REFUSAL_GUIDANCE = {
    "NO_TORSO": (
        "Không đọc được vòng eo: ảnh không có hàng nào giữa mốc ngực và mốc hông. "
        "Hãy đứng thẳng, chụp đủ thân và để camera ngang eo."
    ),
    "NO_NARROWING": (
        "Không đọc được vòng eo: bề rộng mặt trước gần như thẳng, không thon hơn ngực/hông "
        f"≥{WAIST_MIN_TAPER_CM:.1f} cm. Hãy mặc áo bó hơn, đứng thẳng và để tay rời thân rồi quét lại."
    ),
    "DEPTH_FLAT": (
        "Không đọc được vòng eo: ảnh nghiêng không lộ phần thon eo (tay che thân hoặc chưa xoay đủ 90°). "
        "Hãy đưa tay ra trước và chụp lại ảnh nghiêng."
    ),
    "HIP_FROM_TEMPLATE": (
        "Không đọc được vòng eo: chỉ thấy phần thon so với hông của mô hình, còn ảnh không quan sát được hông "
        "hoặc bề rộng eo không thon hơn ngực. Hãy chụp toàn thân (thấy hông) hoặc mặc áo bó hơn."
    ),
}


def _row_index(fractions, circumferences, low, high, choice):
    """Row of the max/min circumference inside a fraction window."""
    candidates = np.flatnonzero((fractions >= low) & (fractions <= high))
    if not len(candidates):
        raise InvalidPhoto("Không có đủ vùng thân để ước lượng các vòng.")
    local = circumferences[candidates]
    return int(candidates[np.argmax(local) if choice == "max" else np.argmin(local)])


def select_waist_row(
    fractions,
    widths_cm,
    chest_index,
    hip_index,
    *,
    hip_from_template: bool = False,
    photo_max_fraction: float | None = None,
):
    """Narrowest *front-width* row between the chest and hip rows.

    Returns ``(index, info)``. The waist is located by the frontal silhouette
    width, not by a fixed fraction window, and accepted only with a visible
    taper. When the hip row comes from the template (``upper_body``), the search
    is capped at the last photo row (``photo_max_fraction``) and the hip is not
    used as evidence: a template hip cannot confirm or reject a waist.
    """
    low, high = sorted((float(fractions[chest_index]), float(fractions[hip_index])))
    search_high = high
    if hip_from_template and photo_max_fraction is not None:
        search_high = min(high, float(photo_max_fraction))
    candidates = np.flatnonzero((fractions > low) & (fractions < search_high))
    if not len(candidates):
        return None, {
            "accepted": False,
            "code": "NO_TORSO",
            "codes": ["NO_TORSO"],
            "reason": WAIST_REFUSAL_GUIDANCE["NO_TORSO"],
            "hip_from_template": bool(hip_from_template),
        }
    index = int(candidates[int(np.argmin(widths_cm[candidates]))])
    waist = float(widths_cm[index])
    chest = float(widths_cm[chest_index])
    hip = float(widths_cm[hip_index])
    margin_chest = chest - waist
    margin_hip = hip - waist
    hip_confirms = not hip_from_template
    accepted = margin_chest >= WAIST_MIN_TAPER_CM and (
        not hip_confirms or margin_hip >= WAIST_MIN_TAPER_CM
    )
    codes: list[str] = []
    if margin_chest < WAIST_MIN_TAPER_CM:
        codes.append("HIP_FROM_TEMPLATE" if hip_from_template else "NO_NARROWING")
    if hip_confirms and margin_hip < WAIST_MIN_TAPER_CM and "NO_NARROWING" not in codes:
        codes.append("NO_NARROWING")
    info = {
        "accepted": bool(accepted),
        "hip_from_template": bool(hip_from_template),
        "search_high_fraction": round(float(search_high), 4),
        "level_fraction": round(float(fractions[index]), 4),
        "waist_width_cm": round(waist, 2),
        "chest_width_cm": round(chest, 2),
        "hip_width_cm": round(hip, 2),
        "margin_chest_cm": round(margin_chest, 2),
        "margin_hip_cm": round(margin_hip, 2),
    }
    if not accepted:
        code = codes[0] if codes else "NO_NARROWING"
        detail = (
            f"hàng hẹp nhất giữa ngực và hông ({waist:.1f} cm) chỉ nhỏ hơn ngực {margin_chest:.1f} cm"
            + ("" if hip_confirms else " (ảnh không thấy hông để đối chiếu)")
            + f" và hông {margin_hip:.1f} cm; cần hẹp hơn ngực ≥{WAIST_MIN_TAPER_CM:.1f} cm"
            + ("" if hip_confirms else " và không dùng hông mô hình làm bằng chứng")
            + "."
        )
        info["code"] = code
        info["codes"] = codes or ["NO_NARROWING"]
        info["reason"] = f"{WAIST_REFUSAL_GUIDANCE[code]} ({detail})"
    return index, info


def resolve_waist_depth(
    fractions,
    depths_cm,
    chest_index,
    waist_index,
    hip_index,
    *,
    hip_from_template: bool = False,
):
    """Depth at the waist row, or a refusal reason when it cannot be trusted.

    When the side profile is flat (``spread < DEPTH_FLAT_CM``) but the frontal
    width shows a real waist, the depth is interpolated linearly between the
    chest and hip rows by the waist row's position (``t`` computed from the
    fractions, not fitted). The result is ``photo_with_prior`` with an
    uncertainty of half the chest-to-hip depth difference. If the hip depth is
    template-only, interpolation would need a template endpoint, so the waist
    stays unavailable with ``HIP_FROM_TEMPLATE``.
    """
    chest = float(depths_cm[chest_index])
    waist = float(depths_cm[waist_index])
    hip = float(depths_cm[hip_index])
    values = (chest, waist, hip)
    spread = max(values) - min(values)
    base = {"depth_spread_cm": round(spread, 2), "hip_from_template": bool(hip_from_template)}
    if not np.isfinite(values).all() or min(values) <= 0:
        return None, {
            "accepted": False,
            "code": "DEPTH_FLAT",
            "codes": ["DEPTH_FLAT"],
            "reason": WAIST_REFUSAL_GUIDANCE["DEPTH_FLAT"],
            **base,
        }
    if spread >= DEPTH_FLAT_CM:
        # A template hip is not an observed depth: compare the waist to the chest
        # only, exactly like the width rule. Otherwise require a dip below both
        # photo-observed neighbours.
        if hip_from_template:
            body_like = waist < chest
            refusal_code = "HIP_FROM_TEMPLATE"
        else:
            body_like = waist < min(chest, hip)
            refusal_code = "DEPTH_FLAT"
        if not body_like:
            return None, {
                "accepted": False,
                "code": refusal_code,
                "codes": [refusal_code],
                "reason": (
                    "Không đọc được vòng eo: ảnh nghiêng có thay đổi bề dày nhưng không thon ở hàng eo "
                    f"(eo {waist:.1f} cm, ngực {chest:.1f}, hông {hip:.1f}). Hãy đưa tay ra trước và chụp lại ảnh nghiêng."
                ),
                **base,
            }
        return waist, {"accepted": True, "source": None, **base}
    if hip_from_template:
        return None, {
            "accepted": False,
            "code": "HIP_FROM_TEMPLATE",
            "codes": ["HIP_FROM_TEMPLATE"],
            "reason": WAIST_REFUSAL_GUIDANCE["HIP_FROM_TEMPLATE"],
            **base,
        }
    chest_frac = float(fractions[chest_index])
    waist_frac = float(fractions[waist_index])
    hip_frac = float(fractions[hip_index])
    t = (waist_frac - chest_frac) / max(hip_frac - chest_frac, 1e-9)
    prior = chest + t * (hip - chest)
    return prior, {
        "accepted": True,
        "source": "photo_with_prior",
        "prior_t": round(float(t), 4),
        "uncertainty_cm": round(abs(hip - chest) / 2, 2),
        **base,
    }


def ellipse_perimeter(width: float, depth: float) -> float:
    """Full diameters and perimeter in the same unit (SciPy elliptic integral)."""
    if not np.isfinite([width, depth]).all() or min(width, depth) <= 0:
        raise InvalidPhoto("Không đủ đường viền để ước lượng số đo.")
    a, b = max(width, depth) / 2, min(width, depth) / 2
    return float(4 * a * ellipe(1 - (b / a) ** 2))


def anatomical_perimeter(width: float, depth: float, key: str | None = None) -> float:
    """Calibrated torso perimeter compensating for non-elliptical anatomical concavities."""
    base = ellipse_perimeter(width, depth)
    if key and key in ANATOMICAL_SECTION_FACTORS:
        return float(base * ANATOMICAL_SECTION_FACTORS[key])
    return base


def estimate_from_profiles(fractions, widths, depths, height_cm, shoulder_ratio, apply_anatomical_calibration: bool = True, shoulder_level: float = .805, hip_level: float = .515, diagnostics: dict | None = None, *, hip_from_template: bool = False, photo_max_fraction: float | None = None):
    """Corresponding shoulder-to-hip rows; circumference uses calibrated anatomical sections.

    ``shoulder_level``/``hip_level`` are the mesh's own skeletal landmarks in
    normalised height, so sections sit on real joints instead of fixed constants.
    ``diagnostics`` optionally receives ``waist_selection`` so the caller can
    report why a waist was not accepted.

    ``hip_from_template``/``photo_max_fraction`` mark an ``upper_body`` capture:
    rows past ``photo_max_fraction`` are reconstructed from the template, so the
    waist search stops at the last photo row and the template hip is never used
    to accept or reject the waist.
    """
    height_cm = float(height_cm)
    widths_cm = np.asarray(widths, dtype=float) * height_cm
    depths_cm = np.asarray(depths, dtype=float) * height_cm
    base_circumferences = np.array([
        ellipse_perimeter(w, d) for w, d in zip(widths_cm, depths_cm)
    ])
    # Hip: search 0.95–1.02 of the shoulder-hip span, not 1.12. With the
    # template landmarks (0.805/0.534) this is ~0.528–0.547 H, i.e. the pelvic
    # band around hip_level ±0.03 H; 1.12 slid down onto the upper thigh.
    definitions = [("chest_cm", "Ngực", .30, .44, "max"), ("waist_cm", "Eo", .52, .78, "min"), ("hip_cm", "Mông", .95, 1.02, "max")]
    values = {"height_cm": round(height_cm, 1), "shoulder_width_cm": round(shoulder_ratio * height_cm, 1), "inseam_cm": None}
    chest_index = _row_index(fractions, base_circumferences, .30, .44, "max")
    hip_index = _row_index(fractions, base_circumferences, .95, 1.02, "max")
    waist_index, waist_info = select_waist_row(
        fractions,
        widths_cm,
        chest_index,
        hip_index,
        hip_from_template=hip_from_template,
        photo_max_fraction=photo_max_fraction,
    )
    if waist_index is None:
        # Degenerate profile: keep three sections for the avatar, report no waist.
        waist_index = _row_index(fractions, base_circumferences, .52, .78, "min")
    waist_depth_cm = float(depths_cm[waist_index])
    waist_source: str | None = None
    waist_uncertainty_cm: float | None = None
    if waist_info.get("accepted"):
        resolved, depth_info = resolve_waist_depth(
            fractions,
            depths_cm,
            chest_index,
            waist_index,
            hip_index,
            hip_from_template=hip_from_template,
        )
        waist_info.update(depth_info)
        if resolved is None:
            waist_info["accepted"] = False
        else:
            waist_depth_cm = float(resolved)
            waist_source = depth_info.get("source")
            waist_uncertainty_cm = depth_info.get("uncertainty_cm")
    waist_info["waist_depth_cm"] = round(waist_depth_cm, 2)
    waist_info["source"] = waist_source
    waist_info["uncertainty_cm"] = waist_uncertainty_cm
    if not waist_info.get("accepted"):
        # List every independent blocker, not just the first one that fired:
        # P01b has both a flat front width and a flat side depth.
        spread_all = max(depths_cm[[chest_index, waist_index, hip_index]]) - min(
            depths_cm[[chest_index, waist_index, hip_index]]
        )
        codes = list(waist_info.get("codes") or [])
        if spread_all < DEPTH_FLAT_CM and "DEPTH_FLAT" not in codes:
            codes.append("DEPTH_FLAT")
        waist_info["codes"] = codes
    selected = {"chest_cm": chest_index, "waist_cm": waist_index, "hip_cm": hip_index}
    targets = []
    for key, title, low, high, choice in definitions:
        i = selected[key]
        k_factor = ANATOMICAL_SECTION_FACTORS.get(key, 1.0) if apply_anatomical_calibration else 1.0
        width_cm = float(widths_cm[i])
        depth_cm = float(depths_cm[i])
        ellipse_cm = float(base_circumferences[i])
        if key == "waist_cm" and waist_info.get("accepted"):
            # Depth may come from the interpolation prior; the perimeter formula
            # itself is unchanged (still an ellipse of the same width/depth).
            depth_cm = float(waist_depth_cm)
            ellipse_cm = ellipse_perimeter(width_cm, depth_cm)
        value = float(ellipse_cm * k_factor)
        accepted = key != "waist_cm" or waist_info.get("accepted", True)
        values[key] = round(value, 1) if accepted else None
        targets.append({
            "key": key,
            "label": title,
            "target_cm": value,
            "ellipse_cm": ellipse_cm,
            "k_anatomy": round(float(k_factor), 5),
            "level": float(shoulder_level - fractions[i] * (shoulder_level - hip_level)),
            "width_cm": width_cm,
            "depth_cm": depth_cm,
            "depth_source": waist_source if key == "waist_cm" else None,
        })
    if diagnostics is not None:
        diagnostics["waist_selection"] = waist_info
    return values, targets


def closed_torso_section(mesh, level_m, center_x_m=None):
    """Select a whole closed central loop, excluding detached arm/leg loops.

    Never trim segments by x: that creates an open curve and a false perimeter.
    Round only graph keys; retain full coordinates for length and rendering.
    """
    segments = trimesh.intersections.mesh_plane(mesh, [0, 1, 0], [0, level_m, 0])
    points, graph = {}, {}
    for segment in segments:
        a, b = (tuple(np.round(p, 6)) for p in segment)
        if a == b:
            continue
        points[a], points[b] = segment[0], segment[1]
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    visited, loops = set(), []
    for start in graph:
        if start in visited:
            continue
        component, pending = set(), [start]
        while pending:
            node = pending.pop()
            if node in component:
                continue
            component.add(node)
            pending.extend(graph[node] - component)
        visited.update(component)
        if any(len(graph[n]) != 2 for n in component):
            continue
        ordered, previous, node = [start], None, start
        for _ in range(len(component)):
            next_node = next(n for n in graph[node] if n != previous)
            if next_node == start:
                break
            ordered.append(next_node)
            previous, node = node, next_node
        if len(ordered) != len(component):
            continue
        curve = np.array([points[n] for n in ordered + [start]])
        # A torso loop spans the body's midline; isolated arms do not.
        if center_x_m is None and (curve[:, 0].min() >= 0 or curve[:, 0].max() <= 0):
            continue
        area = abs(np.sum(curve[:-1, 0] * curve[1:, 2] - curve[1:, 0] * curve[:-1, 2])) / 2
        loops.append((area, curve))
    if not loops:
        raise InvalidPhoto("Không tìm được vòng thân kín trên mô hình. Hãy chụp lại, tay tách khỏi thân.")
    curve = max(loops, key=lambda item: item[0])[1] if center_x_m is None else min(loops, key=lambda item: abs(np.mean(item[1][:,0])-center_x_m))[1]
    perimeter_cm = float(np.linalg.norm(np.diff(curve, axis=0), axis=1).sum() * 100)
    return perimeter_cm, curve


def validate_glb_mesh(mesh: trimesh.Trimesh, height_cm: float, sections: list[dict]) -> dict:
    """Validate exported .glb mesh geometry, metre scale, coordinate frame, and section loops."""
    from scipy.spatial import cKDTree

    vertices = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=int)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) == 0 or len(faces) == 0:
        raise InvalidPhoto("Mô hình 3D rỗng hoặc sai cấu trúc hình học.")
    if not np.isfinite(vertices).all():
        raise InvalidPhoto("Mô hình 3D chứa tọa độ đỉnh không hợp lệ (NaN/Inf).")
    normals = np.asarray(mesh.vertex_normals, dtype=float)
    face_normals = np.asarray(mesh.face_normals, dtype=float)
    if not np.isfinite(normals).all() or not np.isfinite(face_normals).all():
        raise InvalidPhoto("Mô hình 3D chứa pháp tuyến không hợp lệ (NaN/Inf).")

    areas = np.asarray(mesh.area_faces, dtype=float)
    degenerate_faces = int(np.sum(~np.isfinite(areas) | (areas <= 1e-12)))
    if degenerate_faces > 0:
        raise InvalidPhoto(f"Mô hình 3D có {degenerate_faces} mặt suy biến diện tích bằng 0.")

    expected_height_m = float(height_cm) / 100.0
    actual_height_m = float(mesh.extents[1])
    height_error_m = abs(actual_height_m - expected_height_m)
    if height_error_m >= 0.015:
        raise InvalidPhoto(
            f"Chiều cao mô hình 3D ({actual_height_m:.4f} m) lệch quá mức cho phép so với {expected_height_m:.4f} m."
        )

    bounds = np.asarray(mesh.bounds, dtype=float)
    min_y_m = float(bounds[0, 1])
    max_y_m = float(bounds[1, 1])
    center_x_m = float(0.5 * (bounds[0, 0] + bounds[1, 0]))
    center_z_m = float(0.5 * (bounds[0, 2] + bounds[1, 2]))
    if abs(min_y_m) >= 0.01:
        raise InvalidPhoto(f"Chân mô hình 3D không đặt tại mặt sàn y=0 (min_y={min_y_m:.4f} m).")
    if abs(max_y_m - expected_height_m) >= 0.015:
        raise InvalidPhoto(f"Đỉnh đầu mô hình 3D không khớp chiều cao mục tiêu (max_y={max_y_m:.4f} m).")
    if abs(center_x_m) >= 0.08 * expected_height_m or abs(center_z_m) >= 0.15 * expected_height_m:
        raise InvalidPhoto("Tâm ngang X/Z của mô hình 3D bị lệch trục tọa độ chuẩn.")

    tree = cKDTree(vertices) if sections else None
    section_checks = []
    for sec in sections:
        pts = np.asarray(sec.get("points_m", []), dtype=float)
        if pts.ndim != 2 or pts.shape[1] != 3 or len(pts) < 4 or not np.isfinite(pts).all():
            raise InvalidPhoto(f"Đường đo {sec.get('key')} không hợp lệ hoặc chứa NaN/Inf.")
        y_mean = float(np.mean(pts[:, 1]))
        y_span = float(np.ptp(pts[:, 1]))
        if not (0.45 * expected_height_m <= y_mean <= 0.82 * expected_height_m) or y_span > 1e-3:
            raise InvalidPhoto(f"Đường đo {sec.get('key')} nằm ngoài vùng giải phẫu thân (y={y_mean:.3f} m).")
        closure_gap_m = float(np.linalg.norm(pts[0] - pts[-1]))
        if closure_gap_m > 1e-3:
            raise InvalidPhoto(f"Đường đo {sec.get('key')} không khép kín (gap={closure_gap_m:.4f} m).")
        signed_area_xz = 0.5 * float(np.sum(pts[:-1, 0] * pts[1:, 2] - pts[1:, 0] * pts[:-1, 2]))
        if abs(signed_area_xz) < 1e-4:
            raise InvalidPhoto(f"Mặt cắt {sec.get('key')} bị suy biến hoặc lật ngược.")
        dists, _ = tree.query(pts)
        max_surface_dist_m = float(np.max(dists))
        if max_surface_dist_m > 0.05:
            raise InvalidPhoto(f"Đường đo {sec.get('key')} lệch khỏi bề mặt lưới ({max_surface_dist_m:.4f} m).")
        section_checks.append({
            "key": sec.get("key"),
            "y_m": round(y_mean, 4),
            "max_vertex_dist_m": round(max_surface_dist_m, 5),
            "area_m2": round(abs(signed_area_xz), 5),
        })

    return {
        "valid": True,
        "unit": "m",
        "expected_height_m": round(expected_height_m, 4),
        "actual_height_m": round(actual_height_m, 4),
        "height_error_m": round(height_error_m, 5),
        "min_y_m": round(min_y_m, 5),
        "max_y_m": round(max_y_m, 5),
        "center_x_m": round(center_x_m, 5),
        "center_z_m": round(center_z_m, 5),
        "vertex_count": int(len(vertices)),
        "face_count": int(len(faces)),
        "degenerate_face_count": degenerate_faces,
        "finite_geometry": True,
        "sections_validated": len(section_checks),
        "section_checks": section_checks,
    }


FIT_MAX_ITERATIONS = 12
FIT_TOLERANCE_CM = 0.05
RING_MAX_DELTA = 0.20


def _smooth_scale_field(y: np.ndarray, levels, factors) -> np.ndarray:
    """Gaussian RBF through the ring factors, then 1.0 outside the torso.

    The interpolation is exact at each ring, so one fit pass normally reaches the
    target. ``sigma`` is widened until adjacent ring scales differ by at most
    ``RING_MAX_DELTA``; the unnormalised basis returns to 1.0 away from the rings.
    """
    centers = np.asarray(levels, dtype=float)
    amps = np.asarray(factors, dtype=float) - 1.0
    span = max(float(centers.max() - centers.min()), .10)
    sigma = max(.06, .45 * span)
    weights = amps.copy()
    for _ in range(6):
        overlap = np.exp(-((centers[:, None] - centers[None, :]) / sigma) ** 2)
        overlap = overlap + np.eye(len(centers)) * 1e-6
        try:
            weights = np.linalg.solve(overlap, amps)
        except np.linalg.LinAlgError:
            weights = amps.copy()
        ring = 1.0 + overlap @ weights
        deltas = np.abs(np.diff(ring))
        if deltas.size == 0 or float(deltas.max()) <= RING_MAX_DELTA:
            break
        sigma *= 1.25
    basis = np.exp(-((y[:, None] - centers[None, :]) / sigma) ** 2)
    return 1.0 + basis @ weights


def measure_target_sections(mesh, targets, height_cm, fit_mode: str = "pchip", iterations: int = 0):
    """Measure every target on the mesh and return the provenance profile."""
    h = height_cm / 100
    sections, errors = [], []
    for target in targets:
        actual, curve = closed_torso_section(mesh, target["level"] * h)
        error = abs(actual - target["target_cm"])
        errors.append(error)
        sections.append({
            "key": target["key"],
            "label": target["label"],
            "target_cm": round(target["target_cm"], 1),
            "model_cm": round(actual, 1),
            "fit_error_cm": round(error, 2),
            "points_m": np.round(curve, 5).tolist(),
        })
    mesh.fix_normals()
    fit_status = "matched" if max(errors) <= 1.5 else "approximate"
    profile = {
        "fit_status": fit_status,
        "max_fit_error_cm": round(max(errors), 2),
        "fit_mode": fit_mode,
        "fit_iterations": iterations,
        "sections": sections,
        "measurement_method": "two_photo_anatomical_calibrated_v2",
        "validation": "not_validated",
        "uncertainty_cm": None,
        "note": "Sai lệch fit chỉ so avatar với số ước lượng từ ảnh, không phải sai số so với cơ thể thật.",
    }
    try:
        profile["mesh_validation"] = validate_glb_mesh(mesh, height_cm, sections)
    except InvalidPhoto:
        pass
    return mesh, profile


def fit_measurement_targets(mesh, targets, height_cm, width_targets=None, fit_mode: str = "pchip"):
    """Fit the avatar to the photo estimates; report fit residual, not accuracy.

    ``width_targets`` optionally constrain lateral breadths that are not
    circumferences (e.g. biacromial shoulder width) without adding report rows.
    Each entry: ``{key, label, kind: "width", level, target_cm, width_cm, blend}``.

    ``fit_mode="pchip"`` keeps the historical piecewise interpolation.
    ``fit_mode="smooth"`` uses a Gaussian ring field with limited adjacent-ring
    scale differences. Both stop when every circumference is within
    ``FIT_TOLERANCE_CM`` or after ``FIT_MAX_ITERATIONS``.
    """
    if fit_mode not in {"pchip", "smooth"}:
        raise ValueError(f"Unknown fit_mode: {fit_mode!r}")
    mesh = mesh.copy()
    h = height_cm / 100
    width_targets = [dict(target) for target in (width_targets or [])]
    for target in width_targets:
        blend = float(target.get("blend", 1.0))
        if blend < 1.0:
            # Blend once against the current breadth; blending inside the loop
            # would converge to the raw landmark value after four iterations.
            _, curve = closed_torso_section(mesh, target["level"] * h)
            current = float(np.ptp(curve[:, 0]) * 100)
            target["target_cm"] = current + blend * (target["target_cm"] - current)
            target["width_cm"] = target["target_cm"]
    ordered = sorted(list(targets) + width_targets, key=lambda t: t["level"])
    iterations = 0
    for iteration in range(FIT_MAX_ITERATIONS):
        factors_x, factors_z, centers_z, errors_now = [], [], [], []
        for target in ordered:
            current, curve = closed_torso_section(mesh, target["level"] * h)
            centers_z.append((curve[:, 2].min() + curve[:, 2].max()) / 2)
            if target.get("kind") == "width":
                raw = target["target_cm"] / max(float(np.ptp(curve[:, 0]) * 100), 1e-4)
                factors_x.append(float(np.clip(raw, .80, 1.25)))
                factors_z.append(1.0)
                continue
            errors_now.append(abs(current - target["target_cm"]))
            factor = target["target_cm"] / current
            if not .70 <= factor <= 1.40:
                error = ClothingOrArmMergedError(
                    "Ảnh có vẻ mặc đồ rộng hoặc tay dính thân, hãy mặc đồ ôm và tách tay khỏi người."
                )
                error.code = "CLOTHING_OR_ARM_MERGED"
                error.factor = round(float(factor), 3)
                error.target_key = target["key"]
                raise error
            if target.get("depth_cm") is not None and target.get("depth_cm", 0) > 0:
                cur_w = float(np.ptp(curve[:, 0]) * 100)
                cur_d = float(np.ptp(curve[:, 2]) * 100)
                target_ratio = target["depth_cm"] / max(target["width_cm"], 1e-4)
                cur_ratio = cur_d / max(cur_w, 1e-4)
                aspect_corr = float(np.sqrt(np.clip(target_ratio / max(cur_ratio, 1e-4), 0.85, 1.18)))
                factor_x = float(factor / aspect_corr)
                factor_z = float(factor * aspect_corr)
            else:
                factor_x = factor_z = float(factor)
            factors_x.append(factor_x)
            factors_z.append(factor_z)
        # Stop before another adjustment once the measured circumferences agree.
        if iteration > 0 and (not errors_now or max(errors_now) <= FIT_TOLERANCE_CM):
            break
        y = mesh.vertices[:, 1] / h
        if fit_mode == "pchip":
            knots = [0, .38] + [t["level"] for t in ordered] + [.84, 1]
            scale_x = PchipInterpolator(knots, [1, 1] + factors_x + [1, 1])(y)
            scale_z = PchipInterpolator(knots, [1, 1] + factors_z + [1, 1])(y)
        else:
            levels = [t["level"] for t in ordered]
            scale_x = _smooth_scale_field(y, levels, factors_x)
            scale_z = _smooth_scale_field(y, levels, factors_z)
        vertices = mesh.vertices.copy()
        # Constant offset on outer arms preserves their thickness instead of scaling them.
        torso_edge = np.interp(y, [t["level"] for t in ordered], [t["width_cm"] / height_cm / 2 for t in ordered]) * h
        weight = np.clip((torso_edge * 1.15 - np.abs(vertices[:, 0])) / (.025 * h), 0, 1)
        vertices[:, 0] = scale_lateral(vertices[:, 0], scale_x, torso_edge)
        center_z = np.interp(y, [t["level"] for t in ordered], centers_z)
        vertices[:, 2] = center_z + (vertices[:, 2] - center_z) * (1 + (scale_z - 1) * weight)
        mesh.vertices = vertices
        iterations += 1
    return measure_target_sections(mesh, targets, height_cm, fit_mode=fit_mode, iterations=iterations)
