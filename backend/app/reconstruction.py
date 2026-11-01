"""CPU body-shape approximation, NOT SAM/photogrammetry/validated anthropometry.

MediaPipe segments two photos and locates pose landmarks. The central torso
silhouettes control a smooth width/depth deformation of a CC0 MakeHuman mesh.
Head, hands, feet, facial features and much limb anatomy remain template-based.
The output is in metres, scaled to the user's self-reported height.
"""
from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Callable

import numpy as np
from scipy.ndimage import binary_fill_holes, label
from scipy.interpolate import PchipInterpolator
import trimesh

from . import anny_body
from . import proportions
from . import report as _report
from .anatomy import depth_weights, resolve_sex, shape_sex, template_landmarks
from .arm_metrics import arm_length_cm, limb_girth_from_mask
from .camera_fusion import aligned_torso_landmarks, assess_cross_view_quality, fuse_camera_scale, synchronized_torso_profile as torso_profile
from .config import MODELS
from .images import InvalidPhoto
from .measurements import SECTION_FACTORS_CALIBRATED, closed_torso_section, estimate_from_profiles, fit_measurement_targets, measure_target_sections, scale_lateral, validate_glb_mesh
from .torso_mask import MIN_FRAME_COVERAGE, clothing_looseness, frame_coverage, more_visible_arm_side, row_arm_merged, shoulder_span

MODEL_PATH = MODELS / "pose_landmarker_full.task"
TEMPLATE_PATH = MODELS / "body-template.obj"
ENGINE = "mediapipe-two-photo-fit-v7"
# report.py carries a legacy ENGINE constant for direct measurement_report calls;
# keep it on the same version as the pipeline.
_report.ENGINE = ENGINE

HIP_DEFINITION_NOTE = (
    "Mốc hông đổi từ fraction 1.12 (đùi trên) sang 0.95–1.02 (dải xương chậu, "
    "~0.52–0.545 H); số hông có thể giảm 2–5 cm so với engine v6."
)


def _tag_measurement_details(rows):
    """Make every provenance row carry the current engine and the hip change note."""
    for row in rows:
        row["engine_version"] = ENGINE
        row["definition_note"] = HIP_DEFINITION_NOTE
    return rows

_detector = None
_detector_lock = threading.Lock()


def get_detector():
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                import mediapipe as mp
                options = mp.tasks.vision.PoseLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
                    running_mode=mp.tasks.vision.RunningMode.IMAGE,
                    num_poses=2,
                    min_pose_detection_confidence=0.55,
                    min_pose_presence_confidence=0.55,
                    output_segmentation_masks=True,
                )
                _detector = mp.tasks.vision.PoseLandmarker.create_from_options(options)
    return _detector


def close_detector():
    global _detector
    with _detector_lock:
        if _detector is not None:
            try:
                _detector.close()
            except Exception:
                pass
            _detector = None


@dataclass
class Observation:
    mask: np.ndarray
    points: np.ndarray
    visibility: np.ndarray
    top: int
    bottom: int
    height: float
    capture_mode: str = "full_body"


def readiness() -> tuple[bool, str]:
    missing = [p.name for p in (MODEL_PATH, TEMPLATE_PATH) if not p.is_file()]
    if missing:
        return False, "Thiếu dữ liệu model: " + ", ".join(missing) + ". Chạy setup.ps1."
    try:
        import mediapipe  # noqa: F401
    except ImportError:
        return False, "Chưa cài MediaPipe. Chạy setup.ps1 để cài thư viện backend."
    anny_ready, _ = anny_body.available()
    base = "Anny" if anny_ready else "MakeHuman dự phòng"
    return True, f"Dựng hình thể ước lượng từ 2 ảnh bằng CPU (nền {base}); chưa hỗ trợ khuôn mặt hoặc số đo may đo."


def segmentation_mask(array: np.ndarray) -> np.ndarray:
    # MediaPipe versions return either HxW or HxWx1 for a float mask.
    if array.ndim == 3 and array.shape[2] == 1:
        array = array[:, :, 0]
    if array.ndim != 2:
        raise InvalidPhoto("Định dạng mask chưa được hỗ trợ. Kiểm tra phiên bản MediaPipe.")
    return array > 0.55


HEAD_SHOULDER_RATIO = 0.195
TORSO_RATIO = 0.290
UPPER_SPAN_RATIO = 0.485
# Hai mỏ neo chỉ được coi là cùng một thang đo khi lệch nhau ≤ 20%. Ngưỡng này
# lấy từ biên dữ liệu thật/QA hiện có (P01b 15,8%; ảnh QA upper-front 17,8% —
# cùng nằm trong sai lệch hệ thống của mốc đầu/hông), không phải từ một ca riêng.
# Lệch hơn thì không có cơ sở chọn bên nào: trả InvalidPhoto thay vì lấy trung bình.
SCALE_AGREEMENT_TOLERANCE = 0.20


def estimate_upper_body_height(points: np.ndarray, visibility: np.ndarray, top: int, h: int) -> float:
    """Multi-anchor upper-body stature estimation in pixels (Tier 1).

    Two independent estimates must agree before either is used:

    * torso anchor — shoulder to hip, 0.290 H of stature;
    * head anchor — crown (mask top) to shoulder, 0.195 H of stature.

    A disagreement above ``SCALE_AGREEMENT_TOLERANCE`` (20%) means the hồ sơ
    doesn't fit the height model (cropped crown, hip landmarks on the waistband,
    leaning, wrong camera height), so the scan is refused with guidance instead
    of silently averaging the two. When they agree, the bounded tanh fusion keeps
    the head anchor and follows the torso anchor by at most ±1.4%.
    """
    shoulder = points[[11, 12]].mean(axis=0)
    hip = points[[23, 24]].mean(axis=0)
    torso = float(hip[1] - shoulder[1])
    h_torso = float(torso / TORSO_RATIO)
    head_shoulder = float(shoulder[1] - top)
    if top < 3 or torso <= 0 or not np.isfinite([h_torso, head_shoulder]).all():
        # Không có mỏ neo đầu (mask cắt mất đỉnh đầu) thì chỉ còn mỏ neo thân.
        return h_torso
    h_head = head_shoulder / HEAD_SHOULDER_RATIO
    if len(points) > 0 and len(visibility) > 0 and visibility[0] >= 0.6:
        nose_to_shoulder = float(shoulder[1] - points[0, 1])
        if 0.08 * h_head <= nose_to_shoulder <= 0.17 * h_head:
            h_nose = nose_to_shoulder / 0.125
            if abs(h_nose - h_head) <= 0.04 * h_head:
                h_head = 0.85 * h_head + 0.15 * h_nose
    mismatch = abs(h_head - h_torso) / max(h_torso, 1.0)
    if mismatch > SCALE_AGREEMENT_TOLERANCE:
        raise InvalidPhoto(
            "Không xác định được tỉ lệ cơ thể: ước lượng từ đầu–vai và vai–hông lệch nhau "
            f"{mismatch * 100:.0f}% (ngưỡng {SCALE_AGREEMENT_TOLERANCE * 100:.0f}%). Hãy đứng thẳng, "
            "đưa camera ngang tầm ngực, thấy rõ đỉnh đầu và để lộ cạp quần ngang hông rồi quét lại."
        )
    rel_diff = (h_torso - h_head) / max(h_head, 1.0)
    # Giới hạn ảnh hưởng của biến thiên chiều dài lưng / trôi mốc hông trong biên độ ±1.4%
    fused_height = h_head * (1.0 + 0.014 * float(np.tanh(rel_diff / 0.08)))
    return float(fused_height)


def align_mask_width(image: np.ndarray) -> np.ndarray:
    """Pad the right edge to a multiple of 4 before MediaPipe inference.

    MediaPipe's segmentation `numpy_view()` aborts the whole process
    (`image_frame.cc: Check failed: 1 == ChannelSize()`) when the mask width is
    not a multiple of 4. Frames touching the edge are rejected later, so the
    padded columns never contain the body.
    """
    pad = (-image.shape[1]) % 4
    if not pad:
        return image
    return np.ascontiguousarray(np.pad(image, ((0, 0), (0, pad), (0, 0)), mode="edge"))


def observe(image: np.ndarray, detector, name: str, capture_mode: str = "full_body") -> Observation:
    # MediaPipe aborts natively (not a Python exception) if the buffer layout does
    # not match the declared SRGB format, so normalise defensively before detect.
    image = np.asarray(image)
    if image.ndim == 2:
        image = np.repeat(image[:, :, None], 3, axis=2)
    elif image.ndim == 3 and image.shape[2] == 4:
        image = image[:, :, :3]
    if image.ndim != 3 or image.shape[2] != 3:
        raise InvalidPhoto(f"Ảnh {name}: định dạng màu chưa được hỗ trợ. Hãy chụp lại bằng JPG hoặc PNG.")
    image = np.ascontiguousarray(image, dtype=np.uint8)
    # MediaPipe aborts the process in `segmentation_masks[0].numpy_view()` when
    # the image width is not a multiple of 4; padding avoids that crash.
    image = align_mask_width(image)
    brightness = float(np.mean(image)) if image.size else 0.0
    if brightness < 25.0:
        raise InvalidPhoto(f"Ảnh {name}: ánh sáng quá tối (độ sáng trung bình {brightness:.1f}/255). Hãy bật thêm đèn và chụp lại.")
    if brightness > 248.0:
        raise InvalidPhoto(f"Ảnh {name}: bị cháy sáng hoàn toàn (độ sáng trung bình {brightness:.1f}/255). Hãy tránh ngược sáng mạnh và chụp lại.")
    import mediapipe as mp
    result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=image))
    if not result.pose_landmarks or not result.segmentation_masks:
        raise InvalidPhoto(f"Ảnh {name}: chưa nhận diện được toàn thân. Hãy đứng thẳng, đủ sáng và chụp lại.")
    if len(result.pose_landmarks) != 1:
        raise InvalidPhoto(f"Ảnh {name}: chỉ để một người trong khung hình.")
    mask = segmentation_mask(result.segmentation_masks[0].numpy_view())
    components, count = label(mask)
    if not count:
        raise InvalidPhoto(f"Ảnh {name}: không tách được người khỏi nền.")
    sizes = np.bincount(components.ravel()); sizes[0] = 0
    mask = binary_fill_holes(components == int(sizes.argmax()))
    yy, xx = np.where(mask)
    if not len(yy):
        raise InvalidPhoto(f"Ảnh {name}: không tìm thấy cơ thể.")
    top, bottom = int(yy.min()), int(yy.max())
    h, w = mask.shape
    if bottom - top < h * 0.42:
        raise InvalidPhoto(f"Ảnh {name}: người quá nhỏ. Hãy tiến gần camera hơn.")
    if capture_mode == "full_body" and (top < 3 or bottom >= h - 3 or xx.min() < 2 or xx.max() >= w - 2):
        raise InvalidPhoto(f"Ảnh {name}: cơ thể chạm mép ảnh. Chụp lại để đủ đầu, tay và bàn chân.")
    points = np.array([[p.x * w, p.y * h] for p in result.pose_landmarks[0]])
    visibility = np.array([p.visibility for p in result.pose_landmarks[0]])
    if not np.isfinite(points).all():
        raise InvalidPhoto("Không đọc được các mốc cơ thể. Hãy chụp lại.")
    if capture_mode == "full_body":
        # Hông phải thấy và nằm trong khung; nếu không, hàng eo/hông sẽ được
        # ngoại suy từ mô hình mẫu nhưng vẫn báo như số đo từ ảnh.
        hips_visible = max(float(visibility[23]), float(visibility[24]))
        hips_in_frame = all(0 <= points[i, 0] < w and 0 <= points[i, 1] < h for i in (23, 24))
        if hips_visible < 0.55 or not hips_in_frame:
            raise InvalidPhoto(
                f"Ảnh {name}: chưa thấy rõ hông/cạp quần. Hãy đứng lùi để thấy từ đầu đến hông và chân."
            )
    if capture_mode == "upper_body":
        # Missing legs must never be interpreted as the person's full pixel height.
        # Scale is explicitly inferred from the template shoulder-to-hip proportion.
        shoulder = points[[11, 12]].mean(axis=0)
        hip = points[[23, 24]].mean(axis=0)
        torso = hip[1] - shoulder[1]
        visible = visibility[[11, 12, 23, 24]]
        if name == "chính diện":
            reliable = min(visible) >= .55
        else:
            reliable = max(min(visibility[[11, 23]]), min(visibility[[12, 24]])) >= .55
        if not reliable or torso < h * .2 or top < 3 or not .08*h < shoulder[1] < .65*h or not shoulder[1] < hip[1] < h*.98:
            raise InvalidPhoto("Cần thấy đầu, hai vai, eo và cạp quần/hông trên. Không cần chụp chân; lùi máy vừa đủ để thấy cạp quần.")
        if abs(hip[0]-shoulder[0]) > torso*.35:
            raise InvalidPhoto("Giữ thân thẳng và camera ngang thân; tránh cúi hoặc nghiêng người.")
        if name == "chính diện" and abs(points[11,1]-points[12,1]) > torso*.2:
            raise InvalidPhoto("Giữ vai ngang và camera thẳng khi chụp thân trên.")
        # Need visible torso margins, but cropped hands and legs are allowed.
        for fraction in (.3, .65, .78):
            y = int(shoulder[1] + fraction*torso)
            row = mask[y]
            if row[:2].any() or row[-2:].any():
                raise InvalidPhoto("Thân đang chạm cạnh ảnh. Đưa vai và eo vào giữa khung.")
        return Observation(mask, points, visibility, top, bottom, estimate_upper_body_height(points, visibility, top, h), capture_mode)
    # Side-view far limbs can be occluded; inspect the better-visible side only.
    if name == "chính diện":
        required = [11, 12, 23, 24, 25, 26, 27, 28]
        if np.mean(visibility[required]) < 0.65 or np.min(visibility[[27, 28]]) < 0.35:
            raise InvalidPhoto("Ảnh chính diện: cần thấy rõ vai, hông, đầu gối và bàn chân.")
        if abs(points[11, 1] - points[12, 1]) > (bottom - top) * 0.06:
            raise InvalidPhoto("Ảnh chính diện: giữ vai ngang và camera thẳng khi chụp.")
        if max(points[27, 1], points[28, 1]) - np.mean(points[[11, 12], 1]) < (bottom - top) * 0.55:
            raise InvalidPhoto("Hãy đứng thẳng toàn thân; demo chưa hỗ trợ tư thế ngồi hoặc co chân.")
    else:
        left = np.mean(visibility[[11, 23, 25, 27]])
        right = np.mean(visibility[[12, 24, 26, 28]])
        if max(left, right) < .55 or max(visibility[27], visibility[28]) < .35:
            raise InvalidPhoto("Ảnh nghiêng: cần thấy rõ vai, hông, đầu gối và ít nhất một bàn chân.")
    if not np.isfinite(points).all():
        raise InvalidPhoto("Không đọc được các mốc cơ thể. Hãy chụp lại.")
    if capture_mode == "full_body":
        # Hông phải thấy và nằm trong khung; nếu không, hàng eo/hông sẽ được
        # ngoại suy từ mô hình mẫu nhưng vẫn báo như số đo từ ảnh.
        hips_visible = max(float(visibility[23]), float(visibility[24]))
        hips_in_frame = all(0 <= points[i, 0] < w and 0 <= points[i, 1] < h for i in (23, 24))
        if hips_visible < 0.55 or not hips_in_frame:
            raise InvalidPhoto(
                f"Ảnh {name}: chưa thấy rõ hông/cạp quần. Hãy đứng lùi để thấy từ đầu đến hông và chân."
            )
    return Observation(mask, points, visibility, top, bottom, float(bottom - top))


def capture_feedback(image: np.ndarray, view: str, capture_mode: str = "full_body") -> dict:
    """Check sampled camera frames with actual pose detection, not pixel stillness.

    Note: `quality["pose_visibility_mean"]` is MediaPipe `detector_confidence`
    for 2D pose landmarks, NOT anthropometric measurement accuracy.
    """
    brightness = round(float(np.mean(image)), 2) if image.size else 0.0
    try:
        detector = get_detector()
        with _detector_lock:
            obs = observe(image, detector, "chính diện" if view == "front" else "góc nghiêng", capture_mode)
        shoulder_ratio = float(abs(obs.points[11, 0] - obs.points[12, 0]) / obs.height)
        if view == "front" and shoulder_ratio < .12:
            raise InvalidPhoto("Hướng cả hai vai về camera để chụp chính diện.")
        if view == "side" and shoulder_ratio > .11:
            raise InvalidPhoto("Xoay người thêm, gần 90° so với camera.")
        torso_profile(obs, arm_sides=(more_visible_arm_side(obs.points, obs.visibility),) if view == "side" else None)
        h, w = image.shape[:2]
        landmarks = [[round(float(p[0] / w), 4), round(float(p[1] / h), 4), round(float(v), 3)] for p, v in zip(obs.points, obs.visibility)]
        key_indices = [11, 12, 23, 24] if capture_mode == "upper_body" else [11, 12, 23, 24, 25, 26, 27, 28]
        pose_vis_mean = float(np.mean(obs.visibility[key_indices]))
        quality = {
            "brightness": brightness,
            "mask_coverage": round(float(np.mean(obs.mask)), 4),
            "pose_visibility_mean": round(pose_vis_mean, 4),
            "shoulder_width_ratio": round(shoulder_ratio, 4),
        }
        return {
            "ready": True,
            "message": "Đã thấy vai, eo và hông trên. Giữ yên; không cần thấy chân." if capture_mode == "upper_body" else "Đã nhận diện toàn thân và góc chụp. Giữ yên.",
            "landmarks": landmarks,
            "view": view,
            "capture_mode": capture_mode,
            "quality": quality,
        }
    except InvalidPhoto as exc:
        return {
            "ready": False,
            "message": str(exc),
            "landmarks": [],
            "view": view,
            "capture_mode": capture_mode,
            "quality": {
                "brightness": brightness,
                "mask_coverage": 0.0,
                "pose_visibility_mean": 0.0,
                "shoulder_width_ratio": 0.0,
            },
        }


def center_run_width(mask: np.ndarray, y: float, center: float) -> float:
    """Width of foreground run nearest the anatomical centre, excluding arms."""
    row = mask[min(max(int(round(y)), 0), mask.shape[0] - 1)]
    if row[0] or row[-1]:
        padded = np.empty(len(row) + 2, dtype=bool)
        padded[0] = False
        padded[1:-1] = row
        padded[-1] = False
        idx_trans = np.flatnonzero(padded[1:] != padded[:-1])
    else:
        idx_trans = np.flatnonzero(row[1:] != row[:-1]) + 1
    if not len(idx_trans):
        return float("nan")
    starts = idx_trans[0::2]
    ends = idx_trans[1::2]
    if len(starts) == 1:
        return float(ends[0] - starts[0])
    containing = np.where((starts <= center) & (ends > center))[0]
    idx = int(containing[0]) if len(containing) else int(np.argmin(abs((starts + ends) / 2 - center)))
    return float(ends[idx] - starts[idx])


def read_template(path: Path = TEMPLATE_PATH) -> trimesh.Trimesh:
    # Parse only body faces: upstream OBJ also contains helper/joint geometry.
    vertices, faces = [], []
    active = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            vertices.append([float(v) for v in line.split()[1:4]])
        elif line.startswith("g "):
            active = line.strip() == "g body"
        elif active and line.startswith("f "):
            indices = [int(v.split("/")[0]) - 1 for v in line.split()[1:]]
            faces.extend([[indices[0], indices[i], indices[i + 1]] for i in range(1, len(indices) - 1)])
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.remove_unreferenced_vertices()
    bounds = mesh.bounds
    mesh.vertices -= np.array([(bounds[0, 0] + bounds[1, 0]) / 2, bounds[0, 1], (bounds[0, 2] + bounds[1, 2]) / 2])
    mesh.vertices /= bounds[1, 1] - bounds[0, 1]
    return mesh


def deform_template(mesh: trimesh.Trimesh, fractions: np.ndarray, front_width: np.ndarray, side_depth: np.ndarray, height_cm: float, sex: str = "female", levels: tuple[float, float] | None = None) -> trimesh.Trimesh:
    mesh = shape_sex(mesh, sex)
    shoulder_level, hip_level = levels or (.805, .515)
    vertices = mesh.vertices.copy()
    y = vertices[:, 1]
    # Template landmarks are fixed to this CC0 asset; these are a modelling prior,
    # not detected measurements. Arms/head/legs retain template topology.
    # A hand overlapping the side silhouette can introduce a large local bulge.
    # Fit a smooth template prior through the three measured regions, rather
    # than imprinting every noisy silhouette row onto the skin.
    _, anchors = estimate_from_profiles(fractions, front_width, side_depth, height_cm, 0, True, shoulder_level, hip_level)
    levels = np.array([a["level"] for a in anchors])
    front_width = np.array([a["width_cm"] / height_cm for a in anchors])
    side_depth = np.array([a["depth_cm"] / height_cm for a in anchors])
    base_width, base_depth, base_center_z = [], [], []
    for level in levels:
        _, band = closed_torso_section(mesh, float(level))
        base_width.append(np.ptp(band[:, 0]))
        base_depth.append(np.ptp(band[:, 2]))
        base_center_z.append((band[:, 2].min() + band[:, 2].max()) / 2)
    width_ratio = front_width / np.maximum(base_width, 0.04)
    depth_ratio = side_depth / np.maximum(base_depth, 0.04)
    if np.any((width_ratio < 0.55) | (width_ratio > 1.9)) or np.any((depth_ratio < 0.5) | (depth_ratio > 2.2)):
        raise InvalidPhoto("Tỷ lệ hai ảnh chưa phù hợp với demo. Hãy chụp đúng góc, cùng tư thế và mặc đồ ôm sát.")
    # Blend into unmodified neck and lower legs so the mesh remains smooth.
    knots = np.concatenate(([0.0, 0.25, 0.40], levels[::-1], [0.84, 0.92, 1.0]))
    sx = np.concatenate(([1, 1, width_ratio[-1] * 0.5 + 0.5], width_ratio[::-1], [1, 1, 1]))
    sz = np.concatenate(([1, 1, depth_ratio[-1] * 0.5 + 0.5], depth_ratio[::-1], [1, 1, 1]))
    x_scale = PchipInterpolator(knots, sx)(y)
    z_scale = PchipInterpolator(knots, sz)(y)
    # Exterior arm vertices are shifted with the torso rather than thickened to
    # torso depth. Arms remain a template estimate, explicitly disclosed in UI.
    radius = np.interp(y, levels[::-1], np.asarray(base_width)[::-1] / 2)
    torso_weight = np.clip((radius * 1.35 - abs(vertices[:, 0])) / (radius * .45), 0, 1)
    torso_weight = torso_weight * torso_weight * (3 - 2 * torso_weight)
    # Arms keep their own thickness: only a small part of the torso widening
    # becomes an outward shift, so a larger chest no longer detaches the arms.
    vertices[:, 0] = scale_lateral(vertices[:, 0], 1 + (x_scale - 1) * (.2 + .8 * torso_weight), radius)
    # OBJ depth origin is not the torso centre (feet/nose affect its bounds).
    # Scaling about global zero pushes the back sideways and distorts posture.
    center_z = np.interp(y, levels[::-1], np.asarray(base_center_z)[::-1])
    # Chest depth grows forward, buttock depth backward. One symmetric factor is
    # what used to inflate the back into a barrel whenever the chest grew.
    front_w, back_w = depth_weights(y)
    side_w = np.where(vertices[:, 2] > center_z, front_w, back_w)
    vertices[:, 2] = center_z + (vertices[:, 2] - center_z) * (1 + (z_scale - 1) * torso_weight * side_w)
    vertices *= height_cm / 100
    mesh.vertices = vertices
    mesh.visual.vertex_colors = [148, 170, 146, 255]
    mesh.fix_normals()
    return mesh


def smooth_avatar(mesh: trimesh.Trimesh, targets: list[dict], height_cm: float, width_targets=None, fit_mode: str = "pchip"):
    """Region-weighted Taubin pass, then re-measure; rollback if girths move > 0.5 cm.

    The old volume-constrained Laplacian + full re-fit sharpened the neck/shoulder
    step. Taubin is applied only outside the 0.82–0.86 H neck band (with a soft
    taper), so the neck keeps its pre-smoothing profile. Circumferences are
    measured on the smoothed mesh; if any moved more than 0.5 cm, the original
    mesh is returned and the caller keeps the pre-smoothing profile.
    """
    target_height = height_cm / 100
    candidate = mesh.copy()
    try:
        from trimesh.smoothing import filter_taubin

        filter_taubin(candidate, lamb=.65, nu=.68, iterations=2)
    except Exception:  # pragma: no cover - optional dependency detail
        try:
            from trimesh.smoothing import filter_laplacian

            filter_laplacian(candidate, lamb=.15, iterations=1, volume_constraint=False)
        except Exception:
            return mesh, None

    y = candidate.vertices[:, 1]
    span = float(y.max() - y.min())
    if span <= 0 or abs(span - target_height) > .02:
        return mesh, None
    normalized = (y - y.min()) / span
    # Reduce (not fully remove) smoothing at the neck and shoulder transition.
    neck_weight = np.exp(-((normalized - .84) / .06) ** 2)
    blend = 1.0 - neck_weight
    candidate.vertices = mesh.vertices + (candidate.vertices - mesh.vertices) * blend[:, None]

    y = candidate.vertices[:, 1]
    span = float(y.max() - y.min())
    if span <= 0:
        return mesh, None
    candidate.vertices[:, 1] = (y - y.min()) * (target_height / span)
    candidate.vertices[:, 1] -= candidate.vertices[:, 1].min()

    candidate, profile = measure_target_sections(candidate, targets, height_cm, fit_mode=fit_mode, iterations=0)
    if profile["max_fit_error_cm"] > .5:
        return mesh, None
    if not (profile.get("mesh_validation") or {}).get("valid", False):
        return mesh, None
    return candidate, profile


def refit_avatar(fitting: dict, measurements: dict, overrides: dict, height_cm: float, destination: Path, fit_mode: str = "pchip", ring_mode: str = "field") -> dict:
    """Rebuild the avatar after the user edits measurements.

    The photo-derived width/depth profile is kept; only the edited circumferences
    change. Width and depth are scaled by the same ratio so the silhouette's W/D
    aspect ratio survives the correction. `fit_measurement_targets` then re-imposes
    every section, so the exported GLB still reports an exact fit.
    """
    targets = [dict(target) for target in fitting.get("targets", [])]
    if not targets:
        raise InvalidPhoto("Phiên này không lưu đủ dữ liệu để dựng lại mô hình. Hãy quét lại.")
    for target in targets:
        key = target.get("key")
        if key in overrides:
            new_cm = float(overrides[key])
            ratio = new_cm / max(float(target["target_cm"]), 1e-6)
            target["target_cm"] = new_cm
            target["width_cm"] = float(target["width_cm"]) * ratio
            target["depth_cm"] = float(target["depth_cm"]) * ratio

    body_model = fitting.get("body_model", "template")
    width_targets = []
    levels = (float(fitting["levels"]["shoulder"]), float(fitting["levels"]["hip"]))
    if body_model == "anny" and anny_body.available()[0]:
        prior = fitting.get("prior") or {}
        mesh = anny_body.build(
            fitting.get("sex", "female"),
            float(prior.get("weight", 0.5)),
            float(prior.get("muscle", 0.45)),
            height_cm,
        )
    else:
        body_model = "template"
        mesh = deform_template(
            read_template(),
            np.asarray(fitting["fractions"], dtype=float),
            np.asarray(fitting["widths"], dtype=float),
            np.asarray(fitting["depths"], dtype=float),
            height_cm,
            fitting.get("sex", "female"),
            levels,
        )
        shoulder_cm = measurements.get("shoulder_width_cm")
        if shoulder_cm:
            width_targets.append({"key": "shoulder_width_cm", "label": "Rộng vai", "kind": "width", "level": levels[0], "target_cm": shoulder_cm, "width_cm": shoulder_cm, "blend": .6})

    base_mains = {}
    for target in targets:
        try:
            base_mains[target["key"]] = closed_torso_section(mesh, target["level"] * height_cm / 100)[0]
        except InvalidPhoto:
            base_mains[target["key"]] = target["target_cm"]
    ring_scales = proportions.ring_scales(base_mains, {t["key"]: t["target_cm"] for t in targets})
    proportions.apply_rings(mesh, ring_scales, height_cm / 100, mode=ring_mode)

    mesh, profile = fit_measurement_targets(mesh, targets, height_cm, width_targets, fit_mode=fit_mode)
    mesh, smoothed = smooth_avatar(mesh, targets, height_cm, width_targets, fit_mode=fit_mode)
    if smoothed is not None:
        profile = smoothed
    profile["capture_mode"] = fitting.get("capture_mode", "full_body")
    profile["sex"] = fitting.get("sex", "female")
    profile["sex_source"] = fitting.get("sex_source", "auto")
    profile["body_model"] = body_model
    profile["proportional_rings"] = proportions.describe(ring_scales)
    profile["proportional_ring_mode"] = ring_mode
    if fitting.get("prior"):
        profile["body_model_prior"] = fitting["prior"]
    profile["levels"] = fitting["levels"]
    profile["engine_version"] = ENGINE
    profile["uncertainty_cm"] = None
    profile["scale_method"] = "refit_from_user_measurements"
    profile["measurement_method"] = "user_corrected_refit"
    from .report import measurement_report
    profile["measurement_details"] = _tag_measurement_details(measurement_report(mesh, measurements, profile, height_cm, overrides=overrides))
    profile["mesh_validation"] = validate_glb_mesh(mesh, height_cm, profile["sections"])
    mesh.export(destination, file_type="glb", include_normals=True)
    return profile


def build_from_measurements(measurements: dict, height_cm: float, sex: str, capture_mode: str, destination: Path, fit_mode: str = "pchip", ring_mode: str = "field") -> dict:
    """Build a 3D avatar directly from a set of measurements (no photos/MediaPipe).

    Used by the AI Vision flow: Gemini already produced chest/waist/hip, so there
    is no need to run the camera detector again. The Anny basis supplies the base
    shape and W/D ratio at each ring; ``refit_avatar`` then imposes the numbers.
    """
    anny_ready, message = anny_body.available()
    if not anny_ready:
        raise InvalidPhoto(message or "Chưa có basis Anny để dựng từ số đo.")
    mesh_sex, sex_source = resolve_sex(sex, measurements, capture_mode)
    weight, muscle = anny_body.phenotype_from_measurements(measurements, height_cm)
    base = anny_body.build(mesh_sex, weight, muscle, height_cm)
    h = height_cm / 100
    targets = []
    for key, label, level in (("chest_cm", "Ngực", .72), ("waist_cm", "Eo", .60), ("hip_cm", "Mông", .5334)):
        _, curve = closed_torso_section(base, level * h)
        width_cm = float(np.ptp(curve[:, 0]) * 100)
        depth_cm = float(np.ptp(curve[:, 2]) * 100)
        target_cm = measurements.get(key)
        if not target_cm or target_cm <= 0:
            target_cm = float(closed_torso_section(base, level * h)[0])
        targets.append({"key": key, "label": label, "target_cm": float(target_cm), "width_cm": width_cm, "depth_cm": depth_cm, "level": level})
    fitting = {
        "sex": mesh_sex,
        "sex_source": sex_source,
        "capture_mode": capture_mode,
        "height_cm": height_cm,
        "body_model": "anny",
        "prior": {"weight": weight, "muscle": muscle},
        "targets": targets,
        "width_targets": [],
        "levels": {"shoulder": .805, "hip": .534, "neck": .855},
        "fractions": [],
        "widths": [],
        "depths": [],
    }
    return refit_avatar(fitting, measurements, {}, height_cm, destination, fit_mode=fit_mode, ring_mode=ring_mode)


def reconstruct(front: np.ndarray, side: np.ndarray, height_cm: float, destination: Path, report: Callable[[str], None], capture_mode: str = "full_body", sex: str = "auto", fit_mode: str = "pchip", ring_mode: str = "field") -> tuple[list[str], dict[str, float | None], dict]:
    report("Đang nhận diện cơ thể trong hai ảnh…")
    detector = get_detector()
    with _detector_lock:
        frontal = observe(front, detector, "chính diện", capture_mode)
        lateral = observe(side, detector, "góc nghiêng", capture_mode)
    shared_height = fuse_camera_scale(frontal, lateral)
    # Cổng A: người phải chiếm đủ khung ở cả hai ảnh, nếu không mask cắt mất
    # tóc/chân và mọi chu vi bị nhân sai theo chiều cao.
    for label, observation in (("chính diện", frontal), ("góc nghiêng", lateral)):
        coverage = frame_coverage(observation)
        if coverage < MIN_FRAME_COVERAGE:
            raise InvalidPhoto(
                f"Ảnh {label}: người chỉ chiếm {coverage * 100:.0f}% chiều cao khung (cần ≥ "
                f"{MIN_FRAME_COVERAGE * 100:.0f}%). Hãy đứng gần camera hơn, thấy đủ từ đầu đến chân."
            )
    quality_diagnostics = assess_cross_view_quality(frontal, lateral, shared_height=shared_height)
    front_shoulders = abs(frontal.points[11, 0] - frontal.points[12, 0]) / frontal.height
    side_shoulders = abs(lateral.points[11, 0] - lateral.points[12, 0]) / lateral.height
    if front_shoulders < 0.12:
        raise InvalidPhoto("Ảnh đầu cần chụp chính diện. Hãy hướng cả hai vai về camera.")
    if side_shoulders > front_shoulders * 0.75:
        raise InvalidPhoto("Ảnh thứ hai chưa đủ nghiêng. Hãy xoay người khoảng 90° so với camera.")
    # Reported shoulder width follows the outer silhouette at the acromion row,
    # not the landmark centres (28.0 vs a 40 cm tape shoulder on P01b). The
    # landmark span above stays as the pose check for the two views.
    front_shoulders_ratio, shoulder_source = shoulder_span(frontal)
    report("Đang khớp đường viền và dựng bề mặt 3D…")
    # Each image is converted with its own cm/px scale: widths use the frontal
    # body height, depths use the lateral body height.
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
    template = read_template()
    landmarks = template_landmarks(str(TEMPLATE_PATH))
    shoulder_level = landmarks.get("shoulder", .805)
    hip_level = landmarks.get("hip", .515)
    if capture_mode == "upper_body":
        # Hip silhouette is not observed. Restore template widths for those rows,
        # and mark the resulting hip as model-only rather than a photo estimate.
        for i in np.flatnonzero(fractions > .78):
            level = float(shoulder_level - fractions[i] * (shoulder_level - hip_level))
            _, curve = closed_torso_section(template, level)
            blend = min(1., (fractions[i]-.78)/.17)
            widths[i] = widths[i]*(1-blend)+np.ptp(curve[:,0])*blend
            depths[i] = depths[i]*(1-blend)+np.ptp(curve[:,2])*blend
    report("Đang trích xuất thông số kích thước cơ thể…")
    measurements, targets = estimate_from_profiles(fractions, widths, depths, height_cm, front_shoulders_ratio, True, shoulder_level, hip_level)
    # The side view is only useful when it shows the waist narrowing. With an arm
    # hanging in front of the torso (or a 3/4 turn instead of 90°) the depth
    # profile is flat and the waist circumference becomes fabric plus arm: on
    # P01b that read 86.6 cm against a 60 cm tape waist. Report it as
    # unavailable instead of wrong.
    depth_by_key = {t["key"]: float(t["depth_cm"]) for t in targets if t.get("depth_cm")}
    waist_unavailable_reason: str | None = None
    if "waist_cm" in depth_by_key:
        waist_depth = depth_by_key["waist_cm"]
        neighbours = [d for k, d in depth_by_key.items() if k in ("chest_cm", "hip_cm")]
        spread = max(depth_by_key.values()) - min(depth_by_key.values())
        # Chest, waist and hip depths cannot be near-identical on a real torso:
        # a spread under 2 cm means the side silhouette is fabric or arm rather
        # than the body profile (P01b measured 1.2 cm and its waist came out
        # +26.6 cm). Refuse the waist instead of reporting that number.
        contaminated = spread < 2.0
        body_like = bool(neighbours) and waist_depth < min(neighbours) - 1.0
        if contaminated:
            waist_unavailable_reason = (
                "Không đọc được vòng eo: bề dày thân gần như không đổi giữa các mốc "
                f"({spread:.1f} cm) nên ảnh nghiêng bị tay hoặc nền che. Hãy chụp lại ảnh nghiêng "
                "với tay đưa ra trước và xoay hẳn 90°."
            )
        elif not body_like:
            waist_unavailable_reason = (
                "Không đọc được vòng eo: ảnh nghiêng chưa lộ phần thon eo (tay che thân hoặc chưa xoay đủ 90°). "
                "Hãy chụp lại ảnh nghiêng với tay đưa ra trước và xoay hẳn 90°."
            )
        if waist_unavailable_reason:
            measurements["waist_cm"] = None
    # Arm/clothing diagnostics are measured on the cleaned frontal mask.
    f_shoulder, f_hip = aligned_torso_landmarks(frontal)
    shoulder_span_px = float(abs(frontal.points[11, 0] - frontal.points[12, 0]))
    depth_keys = ("chest_cm", "waist_cm") if capture_mode == "upper_body" else ("chest_cm", "waist_cm", "hip_cm")
    merged_rows: dict[str, bool] = {}
    depths_cm: list[float] = []
    for target in targets:
        if target["key"] not in depth_keys:
            continue
        frac = (shoulder_level - target["level"]) / max(shoulder_level - hip_level, 1e-9)
        row_y = f_shoulder[1] + frac * (f_hip[1] - f_shoulder[1])
        center_x = f_shoulder[0] + frac * (f_hip[0] - f_shoulder[0])
        merged_rows[target["key"]] = row_arm_merged(
            frontal.mask, row_y, center_x, shoulder_span_px, float(frontal.height)
        )
        depths_cm.append(float(target["depth_cm"]))
    chest_target = next((t for t in targets if t["key"] == "chest_cm"), None)
    looseness_flag, looseness_reasons = clothing_looseness(
        float(chest_target["width_cm"]) if chest_target else None,
        measurements.get("shoulder_width_cm"),
        depths_cm,
        merged_rows,
    )
    mesh_sex, sex_source = resolve_sex(sex, measurements, capture_mode)
    report("Đang dựng hình thể nam/nữ…")
    anny_ready, _anny_message = anny_body.available()
    width_targets = []
    shoulder_cm = measurements.get("shoulder_width_cm")
    body_prior = None
    if anny_ready:
        # Anny's sex phenotype supplies the anatomy (shoulders, bust, glutes,
        # limbs). Its cross-section at the shoulder joint includes the upper
        # arms, so the landmark breadth is NOT imposed here: it would narrow a
        # natural deltoid instead of matching an acromion-to-acromion width.
        weight, muscle = anny_body.phenotype_from_measurements(measurements, height_cm)
        mesh = anny_body.build(mesh_sex, weight, muscle, height_cm)
        body_prior = {"weight": weight, "muscle": muscle}
    else:
        mesh = deform_template(template, fractions, widths, depths, height_cm, mesh_sex, (shoulder_level, hip_level))
        if shoulder_cm:
            # Breadth from pose landmarks is noisier than a silhouette perimeter, so
            # the mesh blends towards it instead of being forced onto it.
            width_targets.append({"key": "shoulder_width_cm", "label": "Rộng vai", "kind": "width", "level": shoulder_level, "target_cm": shoulder_cm, "width_cm": shoulder_cm, "blend": .6})
    report("Đang khớp avatar theo các vòng ước lượng…")
    base_mains = {}
    for target in targets:
        try:
            base_mains[target["key"]] = closed_torso_section(mesh, target["level"] * height_cm / 100)[0]
        except InvalidPhoto:
            base_mains[target["key"]] = target["target_cm"]
    ring_scales = proportions.ring_scales(base_mains, {t["key"]: t["target_cm"] for t in targets})
    proportions.apply_rings(mesh, ring_scales, height_cm / 100, mode=ring_mode)
    mesh, profile = fit_measurement_targets(mesh, targets, height_cm, width_targets, fit_mode=fit_mode)
    mesh, smoothed_profile = smooth_avatar(mesh, targets, height_cm, width_targets, fit_mode=fit_mode)
    if smoothed_profile is not None:
        profile = smoothed_profile
    profile["capture_mode"] = capture_mode
    profile["sex"] = mesh_sex
    profile["sex_source"] = sex_source
    profile["body_model"] = "anny" if anny_ready else "template"
    if body_prior:
        profile["body_model_prior"] = body_prior
    profile["levels"] = {"shoulder": round(shoulder_level, 4), "hip": round(hip_level, 4), "neck": round(landmarks.get("neck", .855), 4)}
    profile["proportional_rings"] = proportions.describe(ring_scales)
    profile["proportional_ring_mode"] = ring_mode
    # Everything needed to rebuild the same body after the user edits a
    # measurement: the photo width/depth profile, the chosen base and the
    # fitted targets. Kept in the profile so a PATCH never needs the photos.
    profile["fitting"] = {
        "sex": mesh_sex,
        "sex_source": sex_source,
        "capture_mode": capture_mode,
        "height_cm": height_cm,
        "body_model": "anny" if anny_ready else "template",
        "prior": body_prior,
        "targets": targets,
        "width_targets": width_targets,
        "levels": profile["levels"],
        "fractions": np.asarray(fractions, dtype=float).tolist(),
        "widths": np.asarray(widths, dtype=float).tolist(),
        "depths": np.asarray(depths, dtype=float).tolist(),
    }
    profile["engine_version"] = ENGINE
    profile["uncertainty_cm"] = None
    profile["quality_diagnostics"] = quality_diagnostics
    profile["per_image_scale"] = {
        "front_body_height_px": round(float(frontal.height), 2),
        "side_body_height_px": round(float(lateral.height), 2),
        "front_cm_per_px": round(float(height_cm) / float(frontal.height), 5) if frontal.height > 0 else None,
        "side_cm_per_px": round(float(height_cm) / float(lateral.height), 5) if lateral.height > 0 else None,
        "height_diff_ratio": round(abs(float(frontal.height) - float(lateral.height)) / max(float(frontal.height), 1e-9), 4),
    }
    profile["arm_removal"] = {
        "front_radius_px": getattr(frontal, "arm_radius_px", {}),
        "side_radius_px": getattr(lateral, "arm_radius_px", {}),
        "warnings": list(getattr(frontal, "arm_removal_warnings", [])) + list(getattr(lateral, "arm_removal_warnings", [])),
    }
    profile["arm_merged_rows"] = merged_rows
    # Cổng A: vai/tay dính vào thân làm chu vi ngực bị cộng phần tay. Chặn thay
    # vì trả một con số rộng hơn thực tế.
    for key, label in (("chest_cm", "vòng ngực"), ("waist_cm", "vòng eo")):
        if merged_rows.get(key):
            raise InvalidPhoto(
                f"Tay đang dính vào thân ở mốc {label}. Hãy đưa hai tay ra trước hoặc sang ngang "
                "khoảng 40 độ rồi quét lại."
                )
    profile["clothing_looseness_flag"] = bool(looseness_flag)
    profile["clothing_looseness_reasons"] = looseness_reasons
    # Where the reported shoulder width came from: the outer silhouette at the
    # acromion row, or the landmark span when that row was unusable.
    profile["shoulder_width_source"] = shoulder_source
    # Bắp/cẳng tay chưa bật: mặt nạ P01b (tay sát thân, áo dài tay) cho cẳng tay
    # 29,3 cm so tape 20 cm, tức phép cắt đã lấn sang thân. Thuật toán có trong
    # arm_metrics (đã test), chỉ bật khi ảnh có tay rời thân rõ ràng.
    measurements["bicep_cm"] = None
    measurements["forearm_cm"] = None
    # Dài tay: chuỗi vai-khuỷu-cổ tay trên ảnh chính diện. Đây là số duy nhất
    # trong nhóm tay tính trực tiếp từ mốc; bắp/cẳng tay cần mặt cắt vuông góc
    # với trục xương nên chưa đưa vào (capsule chỉ cho một bán kính cho cả tay).
    measurements["arm_length_cm"] = arm_length_cm(
        frontal.points, float(height_cm) / max(float(frontal.height), 1.0)
    )
    profile["waist_unavailable_reason"] = waist_unavailable_reason
    profile["section_factors_calibrated"] = SECTION_FACTORS_CALIBRATED
    profile["scale_method"] = "height_per_image_upper_body" if capture_mode == "upper_body" else "height_and_per_image_silhouette"
    if capture_mode == "upper_body":
        measurements["hip_cm"] = None
        measurements["inseam_cm"] = None
        profile["measurement_method"] = "upper_body_anatomical_calibrated_v2"
    from .report import measurement_report
    profile["measurement_details"] = _tag_measurement_details(measurement_report(mesh, measurements, profile, height_cm))
    profile["mesh_validation"] = validate_glb_mesh(mesh, height_cm, profile["sections"])
    report("Đang hoàn thiện file 3D…")
    mesh.export(destination, file_type="glb", include_normals=True)
    warnings = [
        "Phần thân được điều chỉnh theo đường viền hai ảnh trên mẫu cơ thể có sẵn. Đây là hình thể ước lượng, không phải bản sao 3D chính xác.",
        "Ngực/eo được ước lượng từ bề rộng và độ sâu hai ảnh với hiệu chuẩn lát cắt giải phẫu; mông giữ theo mẫu." if capture_mode == "upper_body" else "Ngực/eo/mông được ước lượng từ bề rộng và độ sâu hai ảnh với hiệu chuẩn lát cắt giải phẫu. Chưa kiểm chứng sai số trên người thật.",
        "Chiều cao do bạn nhập; rộng vai là khoảng cách hai mốc vai trên ảnh. Chưa đủ cơ sở đo inseam nên không xuất số này.",
        "Đầu, khuôn mặt và bàn tay/chân giữ theo mẫu.",
        "Biên dạng thân được làm mượt qua ba vùng đo trên mẫu có sẵn; chưa tái tạo đầy đủ tư thế hoặc phân bố mô cơ thể.",
    ]
    if capture_mode == "upper_body":
        warnings.insert(0, "Chế độ webcam thân trên: tỷ lệ cm suy ra từ chiều cao và đa mỏ neo sọ–vai–hông của mẫu. Ngực/eo phụ thuộc giả định này; mông và chân không được đo từ ảnh. Không dùng cho may đo.")
    warnings.append(
        ("Dáng mô hình 3D: Nữ" if mesh_sex == "female" else "Dáng mô hình 3D: Nam")
        + (" (bạn chọn)." if sex_source == "user" else " (ước lượng từ tỉ lệ số đo).")
        + " Đây là giả định dựng hình để mô hình có tỉ lệ cơ thể, không phải nhận diện giới tính."
    )
    if quality_diagnostics.get("cross_view_warning"):
        warnings.append(quality_diagnostics["cross_view_warning"])
    if looseness_flag:
        warnings.append(
            "Cờ cảnh báo quần áo/tay: " + "; ".join(looseness_reasons)
            + ". Kết quả có thể bị phóng đại bởi đồ rộng hoặc tay dính thân."
        )
    if anny_ready:
        warnings.append(
            "Hình nền nam/nữ dựng từ mô hình cơ thể Anny (Apache-2.0, asset MakeHuman CC0) rồi mới khớp số đo. "
            "Đây vẫn là hình thể ước lượng, không phải bản sao 3D của bạn."
        )
    else:
        warnings.append(
            "Chưa có basis Anny trong backend/models nên đang dùng lưới MakeHuman cũ; "
            "chạy verification/scripts/build_anny_bases.py để bật mô hình nam/nữ đầy đủ."
        )
    warnings.append(
        "Vòng cổ/đùi/bắp chân/cổ chân suy từ vòng ngực hoặc hông theo hệ số tỷ lệ dựng hình "
        f"(cổ {ring_scales['neck_cm']:.2f}×, đùi {ring_scales['thigh_cm']:.2f}×, "
        f"bắp chân {ring_scales['calf_cm']:.2f}×, cổ chân {ring_scales['ankle_cm']:.2f}×). "
        "Không phải số đo trực tiếp từ ảnh."
    )
    return warnings, measurements, profile










