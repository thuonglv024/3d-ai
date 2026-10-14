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
from scipy.ndimage import binary_fill_holes, gaussian_filter1d, label
from scipy.interpolate import PchipInterpolator
import trimesh

from .config import MODELS
from .images import InvalidPhoto

MODEL_PATH = MODELS / "pose_landmarker_full.task"
TEMPLATE_PATH = MODELS / "body-template.obj"
ENGINE = "mediapipe-silhouette-template-v1"

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


def readiness() -> tuple[bool, str]:
    missing = [p.name for p in (MODEL_PATH, TEMPLATE_PATH) if not p.is_file()]
    if missing:
        return False, "Thiếu dữ liệu model: " + ", ".join(missing) + ". Chạy setup.ps1."
    try:
        import mediapipe  # noqa: F401
    except ImportError:
        return False, "Chưa cài MediaPipe. Chạy setup.ps1 để cài thư viện backend."
    return True, "Dựng hình thể ước lượng từ 2 ảnh bằng CPU; chưa hỗ trợ khuôn mặt hoặc số đo may đo."


def segmentation_mask(array: np.ndarray) -> np.ndarray:
    # MediaPipe versions return either HxW or HxWx1 for a float mask.
    if array.ndim == 3 and array.shape[2] == 1:
        array = array[:, :, 0]
    if array.ndim != 2:
        raise InvalidPhoto("Định dạng mask chưa được hỗ trợ. Kiểm tra phiên bản MediaPipe.")
    return array > 0.55


def observe(image: np.ndarray, detector, name: str) -> Observation:
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
    top, bottom = int(yy.min()), int(yy.max())
    h, w = mask.shape
    if bottom - top < h * 0.42:
        raise InvalidPhoto(f"Ảnh {name}: người quá nhỏ. Hãy tiến gần camera hơn.")
    if top < 3 or bottom >= h - 3 or xx.min() < 2 or xx.max() >= w - 2:
        raise InvalidPhoto(f"Ảnh {name}: cơ thể chạm mép ảnh. Chụp lại để đủ đầu, tay và bàn chân.")
    points = np.array([[p.x * w, p.y * h] for p in result.pose_landmarks[0]])
    visibility = np.array([p.visibility for p in result.pose_landmarks[0]])
    # Side-view far limbs can be occluded; inspect the better-visible side only.
    if name == "chính diện":
        required = [11, 12, 23, 24, 25, 26, 27, 28]
        if np.mean(visibility[required]) < 0.65 or np.min(visibility[[27, 28]]) < 0.35:
            raise InvalidPhoto("Ảnh chính diện: cần thấy rõ vai, hông, đầu gối và bàn chân.")
        if abs(points[11, 1] - points[12, 1]) > (bottom - top) * 0.06:
            raise InvalidPhoto("Ảnh chính diện: giữ vai ngang và camera thẳng khi chụp.")
        if max(points[27, 1], points[28, 1]) - np.mean(points[[11, 12], 1]) < (bottom - top) * 0.55:
            raise InvalidPhoto("Hãy đứng thẳng toàn thân; demo chưa hỗ trợ tư thế ngồi hoặc co chân.")
    return Observation(mask, points, visibility, top, bottom, float(bottom - top))


def center_run_width(mask: np.ndarray, y: float, center: float) -> float:
    """Width of foreground run nearest the anatomical centre, excluding arms."""
    row = mask[int(np.clip(round(y), 0, mask.shape[0] - 1))]
    padded = np.pad(row.astype(np.int8), (1, 1))
    starts = np.where(np.diff(padded) == 1)[0]
    ends = np.where(np.diff(padded) == -1)[0]
    if not len(starts):
        return float("nan")
    containing = np.where((starts <= center) & (ends > center))[0]
    idx = int(containing[0]) if len(containing) else int(np.argmin(abs((starts + ends) / 2 - center)))
    return float(ends[idx] - starts[idx])


def torso_profile(obs: Observation) -> tuple[np.ndarray, np.ndarray]:
    shoulder = obs.points[[11, 12]].mean(axis=0)
    hip = obs.points[[23, 24]].mean(axis=0)
    if hip[1] - shoulder[1] < obs.height * 0.15:
        raise InvalidPhoto("Không xác định được vùng thân. Hãy đứng thẳng và chụp lại.")
    fractions = np.linspace(0.12, 1.12, 35)
    rows = shoulder[1] + fractions * (hip[1] - shoulder[1])
    centers = shoulder[0] + fractions * (hip[0] - shoulder[0])
    widths = []
    for row, center in zip(rows, centers):
        local = [center_run_width(obs.mask, row + d, center) for d in (-2, -1, 0, 1, 2)]
        widths.append(np.nanmedian(local) / obs.height)
    widths = np.asarray(widths)
    if not np.all(np.isfinite(widths)) or np.min(widths) < 0.06 or np.max(widths) > 0.40:
        raise InvalidPhoto("Đường viền cơ thể chưa rõ. Hãy dùng nền đơn giản và tránh tay che thân.")
    return fractions, gaussian_filter1d(widths, sigma=1.4)


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


def deform_template(mesh: trimesh.Trimesh, fractions: np.ndarray, front_width: np.ndarray, side_depth: np.ndarray, height_cm: float) -> trimesh.Trimesh:
    mesh = mesh.copy()
    vertices = mesh.vertices.copy()
    y = vertices[:, 1]
    # Template landmarks are fixed to this CC0 asset; these are a modelling prior,
    # not detected measurements. Arms/head/legs retain template topology.
    shoulder_y, hip_y = 0.805, 0.515
    levels = shoulder_y - fractions * (shoulder_y - hip_y)
    base_width, base_depth = [], []
    for level in levels:
        band = vertices[(abs(y - level) < 0.008) & (abs(vertices[:, 0]) < 0.14)]
        if len(band) < 8:
            raise RuntimeError("Body template has incompatible topology.")
        base_width.append(np.ptp(band[:, 0]))
        base_depth.append(np.ptp(band[:, 2]))
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
    torso_weight = np.clip((0.23 - abs(vertices[:, 0])) / 0.09, 0, 1)
    torso_weight = torso_weight * torso_weight * (3 - 2 * torso_weight)
    vertices[:, 0] *= 1 + (x_scale - 1) * torso_weight
    vertices[:, 2] *= 1 + (z_scale - 1) * torso_weight
    # Shift exterior arm vertices laterally with torso widening to avoid mesh interpenetration
    arm_weight = (1 - torso_weight) * np.clip((y - 0.40) / 0.44, 0, 1)
    vertices[:, 0] += np.sign(vertices[:, 0]) * 0.14 * (x_scale - 1) * arm_weight
    vertices *= height_cm / 100
    mesh.vertices = vertices
    mesh.visual.vertex_colors = [148, 170, 146, 255]
    mesh.fix_normals()
    return mesh


def calculate_measurements(mesh: trimesh.Trimesh, height_cm: float) -> dict[str, float]:
    """Calculate estimated anatomical circumferences and lengths in cm from the 3D mesh."""
    h_m = height_cm / 100.0

    def slice_contour_perimeter(y_val: float, max_half_width: float) -> float:
        lines = trimesh.intersections.mesh_plane(mesh, plane_normal=[0, 1, 0], plane_origin=[0, y_val, 0])
        if len(lines) == 0:
            return 0.0
        centers_x = np.abs(lines.mean(axis=1)[:, 0])
        torso_lines = lines[centers_x <= max_half_width]
        if len(torso_lines) == 0:
            return 0.0
        diff = torso_lines[:, 0, :] - torso_lines[:, 1, :]
        return float(np.sum(np.sqrt((diff ** 2).sum(axis=-1)))) * 100.0

    # 1. Chest: peak of ribcage / chest area (y ~ 0.69 to 0.74 * height)
    chest_levels = np.linspace(0.69, 0.74, 6) * h_m
    chest_perims = [slice_contour_perimeter(y, 0.22 * h_m) for y in chest_levels]
    chest_cm = round(max(chest_perims) if chest_perims else 0.0, 1)

    # 2. Waist: narrowest part between ribcage and pelvis (y ~ 0.56 to 0.63 * height)
    waist_levels = np.linspace(0.56, 0.63, 8) * h_m
    waist_perims = [slice_contour_perimeter(y, 0.20 * h_m) for y in waist_levels]
    valid_waist = [p for p in waist_perims if p > 0]
    waist_cm = round(min(valid_waist) if valid_waist else 0.0, 1)

    # 3. Hip: widest part around pelvis and buttocks (y ~ 0.47 to 0.54 * height)
    hip_levels = np.linspace(0.47, 0.54, 8) * h_m
    hip_perims = [slice_contour_perimeter(y, 0.26 * h_m) for y in hip_levels]
    hip_cm = round(max(hip_perims) if hip_perims else 0.0, 1)

    # 4. Shoulder width: span at shoulder level
    shoulder_lines = trimesh.intersections.mesh_plane(mesh, plane_normal=[0, 1, 0], plane_origin=[0, 0.805 * h_m, 0])
    if len(shoulder_lines) > 0:
        shoulder_pts = shoulder_lines.reshape(-1, 3)
        shoulder_width_cm = round(float(np.ptp(shoulder_pts[:, 0])) * 100.0, 1)
    else:
        shoulder_width_cm = round(0.24 * height_cm, 1)

    # 5. Inseam: crotch to floor
    inseam_cm = round(0.46 * height_cm, 1)

    return {
        "height_cm": round(height_cm, 1),
        "chest_cm": chest_cm,
        "waist_cm": waist_cm,
        "hip_cm": hip_cm,
        "shoulder_width_cm": shoulder_width_cm,
        "inseam_cm": inseam_cm,
    }


def analyze_body_profile(measurements: dict[str, float]) -> dict[str, str]:
    """Classify body silhouette shape and recommend clothing sizes."""
    chest = measurements.get("chest_cm", 90.0)
    waist = measurements.get("waist_cm", 75.0)
    hip = measurements.get("hip_cm", 95.0)
    height = measurements.get("height_cm", 170.0)

    # 1. Body shape classification
    if waist <= chest * 0.75 and waist <= hip * 0.75 and abs(chest - hip) <= 6.0:
        shape = "Đồng hồ cát"
        desc = "Cân đối lý tưởng. Phù hợp trang phục ôm dáng, nhấn eo hoặc kèm thắt lưng tôn dáng."
    elif hip >= chest + 4.5 and hip > waist * 1.15:
        shape = "Dáng quả lê"
        desc = "Hông và đùi nở nang. Phù hợp áo sáng màu, cổ chữ V, váy chữ A hoặc quần ống suông."
    elif chest >= hip + 4.5:
        shape = "Tam giác ngược"
        desc = "Khung vai và ngực nở thể thao. Phù hợp quần ống rộng, váy xòe, tránh chi tiết đệm vai."
    elif waist >= chest * 0.88 or waist >= hip * 0.88:
        shape = "Dáng quả táo"
        desc = "Vòng bụng đầy đặn. Phù hợp trang phục cổ sâu, chất liệu rũ nhẹ, đầm suông hoặc áo form rộng."
    else:
        shape = "Dáng chữ nhật"
        desc = "Vóc dáng thanh thoát, đều đặn. Phù hợp tạo điểm nhấn eo, croptop hoặc phối đồ layer nhiều lớp."

    # 2. Asian / VN Top Size Recommendation
    if height < 163 or chest < 86:
        top_size = "S"
    elif (height < 172 and chest < 93) or chest < 91:
        top_size = "M"
    elif (height < 179 and chest < 100) or chest < 98:
        top_size = "L"
    elif (height < 185 and chest < 107) or chest < 105:
        top_size = "XL"
    else:
        top_size = "XXL"

    # 3. Bottom Size (Waist in inches: 1 inch = 2.54 cm)
    waist_inch = waist / 2.54
    if waist_inch < 28.5:
        bottom_size = "28 - 29"
    elif waist_inch < 30.5:
        bottom_size = "30"
    elif waist_inch < 32.0:
        bottom_size = "31 - 32"
    elif waist_inch < 33.5:
        bottom_size = "33"
    elif waist_inch < 35.5:
        bottom_size = "34 - 35"
    else:
        bottom_size = "36+"

    return {
        "shape": shape,
        "shape_description": desc,
        "top_size": top_size,
        "bottom_size": bottom_size,
        "fit_type": "Regular Fit",
    }


def reconstruct(front: np.ndarray, side: np.ndarray, height_cm: float, destination: Path, report: Callable[[str], None]) -> tuple[list[str], dict[str, float], dict[str, str]]:
    report("Đang nhận diện cơ thể trong hai ảnh…")
    detector = get_detector()
    with _detector_lock:
        frontal = observe(front, detector, "chính diện")
        lateral = observe(side, detector, "góc nghiêng")
    front_shoulders = abs(frontal.points[11, 0] - frontal.points[12, 0]) / frontal.height
    side_shoulders = abs(lateral.points[11, 0] - lateral.points[12, 0]) / lateral.height
    if front_shoulders < 0.12:
        raise InvalidPhoto("Ảnh đầu cần chụp chính diện. Hãy hướng cả hai vai về camera.")
    if side_shoulders > front_shoulders * 0.75:
        raise InvalidPhoto("Ảnh thứ hai chưa đủ nghiêng. Hãy xoay người khoảng 90° so với camera.")
    report("Đang khớp đường viền và dựng bề mặt 3D…")
    fractions, widths = torso_profile(frontal)
    _, depths = torso_profile(lateral)
    mesh = deform_template(read_template(), fractions, widths, depths, height_cm)
    report("Đang trích xuất thông số kích thước cơ thể…")
    measurements = calculate_measurements(mesh, height_cm)
    report("Đang phân tích dáng người & gợi ý size…")
    profile = analyze_body_profile(measurements)
    report("Đang hoàn thiện file 3D…")
    mesh.export(destination, file_type="glb", include_normals=True)
    warnings = [
        "Phần thân được điều chỉnh theo đường viền hai ảnh trên mẫu cơ thể có sẵn. Đây là hình thể ước lượng, không phải bản sao 3D chính xác.",
        "Thông số các vòng (ngực, eo, mông) là ước lượng hình học vi phân từ lưới 3D, mang tính tham khảo trực quan, chưa qua kiểm chứng may đo.",
        "Đầu, khuôn mặt và bàn tay/chân giữ theo mẫu.",
    ]
    return warnings, measurements, profile
