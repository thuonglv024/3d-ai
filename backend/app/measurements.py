"""Photo-derived estimates and closed torso sections. No validated anthropometry."""
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.special import ellipe
import trimesh

from .images import InvalidPhoto


def scale_lateral(x, scale, radius):
    """Monotone lateral deformation: scale the trunk and translate outer limbs.

    Blending x * scale by a rapidly falling mask can invert vertex order near
    the armpits. This map keeps a positive derivative for our allowed scales.
    """
    radius = np.maximum(radius, .01)
    return x + (scale - 1) * radius / np.tanh(1) * np.tanh(x / radius)


ANATOMICAL_SECTION_FACTORS = {
    "chest_cm": 1.0 / (1.0 - 0.074710),  # +8.07% (~7.47% concavity compensation for chest/scapula/sternum)
    "waist_cm": 1.0 / (1.0 - 0.031088),  # +3.21% (~3.11% concavity compensation for waist/lumbar)
    "hip_cm": 1.0 / (1.0 - 0.058685),    # +6.23% (~5.87% concavity compensation for gluteal/hip contour)
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


def estimate_from_profiles(fractions, widths, depths, height_cm, shoulder_ratio, apply_anatomical_calibration: bool = True, shoulder_level: float = .805, hip_level: float = .515):
    """Corresponding shoulder-to-hip rows; circumference uses calibrated anatomical sections.

    ``shoulder_level``/``hip_level`` are the mesh's own skeletal landmarks in
    normalised height, so sections sit on real joints instead of fixed constants.
    """
    base_circumferences = np.array([ellipse_perimeter(w, d) * height_cm for w, d in zip(widths, depths)])
    # Hip: search 0.95–1.02 of the shoulder-hip span, not 1.12. With the
    # template landmarks (0.805/0.534) this is ~0.528–0.547 H, i.e. the pelvic
    # band around hip_level ±0.03 H; 1.12 slid down onto the upper thigh.
    definitions = [("chest_cm", "Ngực", .30, .44, "max"), ("waist_cm", "Eo", .52, .78, "min"), ("hip_cm", "Mông", .95, 1.02, "max")]
    values = {"height_cm": round(height_cm, 1), "shoulder_width_cm": round(shoulder_ratio * height_cm, 1), "inseam_cm": None}
    targets = []
    for key, title, low, high, choice in definitions:
        candidates = np.flatnonzero((fractions >= low) & (fractions <= high))
        if not len(candidates):
            raise InvalidPhoto("Không có đủ vùng thân để ước lượng các vòng.")
        local = base_circumferences[candidates]
        i = int(candidates[np.argmax(local) if choice == "max" else np.argmin(local)])
        k_factor = ANATOMICAL_SECTION_FACTORS.get(key, 1.0) if apply_anatomical_calibration else 1.0
        value = float(base_circumferences[i] * k_factor)
        values[key] = round(value, 1)
        targets.append({
            "key": key,
            "label": title,
            "target_cm": value,
            "ellipse_cm": float(base_circumferences[i]),
            "k_anatomy": round(float(k_factor), 5),
            "level": float(shoulder_level - fractions[i] * (shoulder_level - hip_level)),
            "width_cm": float(widths[i] * height_cm),
            "depth_cm": float(depths[i] * height_cm),
        })
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


def fit_measurement_targets(mesh, targets, height_cm, width_targets=None):
    """Fit the avatar to the photo estimates; report fit residual, not accuracy.

    ``width_targets`` optionally constrain lateral breadths that are not
    circumferences (e.g. biacromial shoulder width) without adding report rows.
    Each entry: ``{key, label, kind: "width", level, target_cm, width_cm, blend}``.
    """
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
    for _ in range(4):
        factors_x, factors_z, centers_z = [], [], []
        for target in ordered:
            current, curve = closed_torso_section(mesh, target["level"] * h)
            centers_z.append((curve[:, 2].min() + curve[:, 2].max()) / 2)
            if target.get("kind") == "width":
                raw = target["target_cm"] / max(float(np.ptp(curve[:, 0]) * 100), 1e-4)
                factors_x.append(float(np.clip(raw, .80, 1.25)))
                factors_z.append(1.0)
                continue
            factor = target["target_cm"] / current
            if not .70 <= factor <= 1.40:
                raise InvalidPhoto("Số đo từ hai góc chưa nhất quán với hình thể. Chụp lại cùng tư thế, tay không che thân.")
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
        y = mesh.vertices[:, 1] / h
        knots = [0, .38] + [t["level"] for t in ordered] + [.84, 1]
        scale_x = PchipInterpolator(knots, [1, 1] + factors_x + [1, 1])(y)
        scale_z = PchipInterpolator(knots, [1, 1] + factors_z + [1, 1])(y)
        vertices = mesh.vertices.copy()
        # Constant offset on outer arms preserves their thickness instead of scaling them.
        torso_edge = np.interp(y, [t["level"] for t in ordered], [t["width_cm"] / height_cm / 2 for t in ordered]) * h
        weight = np.clip((torso_edge * 1.15 - np.abs(vertices[:, 0])) / (.025 * h), 0, 1)
        vertices[:, 0] = scale_lateral(vertices[:, 0], scale_x, torso_edge)
        center_z = np.interp(y, [t["level"] for t in ordered], centers_z)
        vertices[:, 2] = center_z + (vertices[:, 2] - center_z) * (1 + (scale_z - 1) * weight)
        mesh.vertices = vertices
    sections, errors = [], []
    for target in targets:
        actual, curve = closed_torso_section(mesh, target["level"] * h)
        error = abs(actual - target["target_cm"])
        errors.append(error)
        sections.append({"key": target["key"], "label": target["label"], "target_cm": round(target["target_cm"], 1), "model_cm": round(actual, 1), "fit_error_cm": round(error, 2), "points_m": np.round(curve, 5).tolist()})
    mesh.fix_normals()
    fit_status = "matched" if max(errors) <= 1.5 else "approximate"
    profile = {
        "fit_status": fit_status,
        "max_fit_error_cm": round(max(errors), 2),
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
