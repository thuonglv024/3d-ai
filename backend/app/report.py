"""Viewer annotations with explicit provenance. Model dimensions are not body measurements.

Note on uncertainty_cm:
    `uncertainty_cm` is explicitly set to `None` because empirical human tape-measure
    calibration data has not been collected yet. Never fabricate a ±X cm confidence
    interval without clinical/human validation data.
"""
import numpy as np
from .measurements import closed_torso_section
from .images import InvalidPhoto

ENGINE = "mediapipe-two-photo-fit-v6"
VALID_SIZING_SOURCES = frozenset({"user_input", "photo_estimate", "photo_with_prior"})


def _observed_region(key: str, upper: bool) -> str:
    if key == "height_cm":
        return "user_reported"
    if key in {"chest_cm", "waist_cm", "shoulder_width_cm"}:
        return "upper_torso_with_template_prior" if upper else "frontal_and_lateral_torso"
    if key == "hip_cm":
        return "template_prior_unobserved" if upper else "frontal_and_lateral_torso"
    if key in {"head_cm", "neck_cm", "thigh_cm", "calf_cm", "ankle_cm"}:
        return "template_prior_unobserved"
    if key in {"arm_length_cm", "inseam_cm"}:
        return "unobserved"
    if key in {"bicep_cm", "forearm_cm"}:
        return "frontal_arm_silhouette"
    return "template_prior_unobserved"


def _quality_warnings(key: str, source: str, upper: bool) -> list[str]:
    if key == "height_cm":
        return [
            "Chiều cao do người dùng tự nhập; các số đo quy đổi sang cm phụ thuộc tuyến tính vào giá trị này."
        ]
    if key in {"bicep_cm", "forearm_cm"}:
        if source == "unavailable":
            return [
                "Không đo được vòng tay: chưa tách được tay khỏi thân, hoặc mặt cắt ngoài khoảng bán kính 2–8 cm."
            ]
        return [
            "Đo trên biên dạng tay ở ảnh chính diện (mặt cắt vuông góc với xương), gồm cả độ dày tay áo; "
            "chưa hiệu chuẩn trên người thật."
        ]
    if source == "photo_with_prior":
        return [
            "Ước lượng từ biên dạng 2 ảnh thân trên kết hợp giả định tỷ lệ chiều cao đa mỏ neo sọ–vai–hông.",
            "Độ dày trang phục hoặc góc đứng lệch 90° có thể làm thay đổi số đo; chưa hiệu chuẩn trên người thật.",
        ]
    if source == "photo_estimate":
        return [
            "Ước lượng từ biên dạng 2 ảnh toàn thân và chiều cao tự nhập.",
            "Độ dày trang phục hoặc góc đứng lệch 90° có thể làm thay đổi số đo; chưa hiệu chuẩn trên người thật.",
        ]
    if source == "template_model":
        if upper and key == "hip_cm":
            return [
                "Chế độ thân trên không quan sát vùng mông; chỉ số này thuộc mô hình nền (Anny/MakeHuman), không dùng để chọn size hoặc theo dõi tiến trình."
            ]
        if key in {"neck_cm", "thigh_cm", "calf_cm", "ankle_cm"}:
            return [
                "Chỉ số suy từ vòng ngực/hông chính theo hệ số tỷ lệ dựng hình, không đo trực tiếp từ ảnh; "
                "không dùng để chọn size hoặc theo dõi tiến trình cơ thể."
            ]
        return [
            "Chỉ số trích xuất từ mặt cắt mô hình nền (Anny/MakeHuman) chưa quan sát trực tiếp; không dùng để chọn size hoặc theo dõi tiến trình cơ thể."
        ]
    return [
        "Không đủ cơ sở mốc giải phẫu tin cậy từ 2 ảnh 2D để ước lượng chỉ số này."
    ]


def _unavailable_reason(key: str, profile: dict) -> str | None:
    """Specific reason recorded by the pipeline, when there is one."""
    specific = {
        "waist_cm": profile.get("waist_unavailable_reason"),
        "shoulder_width_cm": profile.get("shoulder_unavailable_reason"),
        "bicep_cm": profile.get("arm_unavailable_reason"),
        "forearm_cm": profile.get("arm_unavailable_reason"),
    }.get(key)
    return str(specific) if specific else None


def measurement_report(mesh, measurements, profile, height_cm, overrides=None):
    """Build per-metric provenance and quality report.

    `overrides` are measurements the user corrected after the scan. They become
    `user_input` rows and their warning says so, instead of pretending the photo
    produced the new value.

    `uncertainty_cm` is always `None` until empirical tape-measure validation
    on human subjects is available; never invent a synthetic ±X cm bound.
    """
    overrides = {key: float(value) for key, value in (overrides or {}).items() if value is not None}
    h = height_cm / 100
    upper = profile["capture_mode"] == "upper_body"
    rows = []

    def add(key, label, value, source, points=None, color="#39d5c2"):
        if key in overrides:
            value = overrides[key]
            source = "user_input"
        if upper and key == "hip_cm" and key not in overrides:
            source = "template_model"
        # A missing number is not a photo estimate: say so instead of attaching
        # a source to a value that does not exist.
        if value is None and source != "user_input":
            source = "unavailable"
        val_cm = round(float(value), 1) if value is not None else None
        is_valid = bool(source in VALID_SIZING_SOURCES and val_cm is not None)
        observed_region = "user_reported" if key in overrides else _observed_region(key, upper)
        if key == "arm_length_cm" and source != "unavailable":
            observed_region = "frontal_arm_landmarks"
        if key in overrides:
            warnings = ["Số đo bạn nhập lại sau khi quét; mô hình 3D và gợi ý size được dựng lại theo giá trị này."]
        elif source == "unavailable":
            warnings = [_unavailable_reason(key, profile) or _quality_warnings(key, source, upper)[0]]
        else:
            warnings = _quality_warnings(key, source, upper)
        rows.append({
            "key": key,
            "label": label,
            "value_cm": val_cm,
            "source": source,
            "observed_region": observed_region,
            "valid_for_sizing": is_valid,
            "valid_for_tracking": is_valid,
            "engine_version": ENGINE,
            "uncertainty_cm": None,
            "quality_warnings": warnings,
            "color": color,
            "points_m": np.round(points, 5).tolist() if points is not None else [],
        })

    # No 3D line for height: a vertical line inside the body pokes out through
    # the head and feet and reads as a rendering glitch. The value stays in the
    # table, only the annotation is omitted.
    add("height_cm", "Chiều cao", height_cm, "user_input")
    for section, color in zip(profile["sections"], ["#f17be0", "#5ce4dc", "#f0dd61"]):
        source = "template_model" if upper and section["key"] == "hip_cm" else "photo_with_prior" if upper else "photo_estimate"
        add(section["key"], section["label"], section["model_cm"] if source == "template_model" else measurements[section["key"]], source, section["points_m"], color)
    add("shoulder_width_cm", "Rộng vai", measurements.get("shoulder_width_cm"), "photo_with_prior" if upper else "photo_estimate")
    # Horizontal closed sections on the actual mesh. Anatomical levels are a
    # template prior, including for full-body uploads: never claim observation.
    for key, title, level, x, color in [
        ("head_cm", "Vòng đầu", .955, 0, "#a8eb73"),
        ("neck_cm", "Vòng cổ", .855, 0, "#a195ff"),
        ("thigh_cm", "Vòng đùi trái", .405, .055, "#bfa8dd"),
        ("calf_cm", "Vòng bắp chân trái", .235, .06, "#76cfed"),
        ("ankle_cm", "Vòng cổ chân trái", .065, .06, "#efc65b"),
    ]:
        try:
            circumference, curve = closed_torso_section(mesh, level * h, center_x_m=x * h)
            add(key, title, circumference, "template_model", curve, color)
        except InvalidPhoto:
            add(key, title, None, "unavailable", color=color)
    add(
        "arm_length_cm",
        "Dài tay",
        measurements.get("arm_length_cm"),
        "photo_with_prior" if upper else "photo_estimate",
    )
    arm_source = "photo_with_prior" if upper else "photo_estimate"
    for key, title in (("bicep_cm", "Bắp tay"), ("forearm_cm", "Cẳng tay")):
        value = measurements.get(key)
        add(key, title, value, arm_source if value is not None else "unavailable")
    add("inseam_cm", "Dài trong chân", None, "unavailable")
    return rows

