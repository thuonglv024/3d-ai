"""MediaPipe geometric estimator for the AI scan ensemble.

Runs the project's classic two-photo geometry (segmentation + pose landmarks +
camera fusion + anatomical calibration) on the same two photos the vision
model sees, producing an independent estimate for the core circumferences and
shoulder width. It runs in a worker thread while the three AI members are in
flight, and every failure is contained: geometry can only add information,
never break the AI scan.
"""
from __future__ import annotations

import logging
from typing import Any

from .metrics import GEOMETRY_METRICS

logger = logging.getLogger(__name__)


def geometric_check_enabled() -> bool:
    """Allow ops to disable the MediaPipe cross-check via env (cost/latency)."""
    import os

    return (os.getenv("MORPH_AI_GEOMETRY_CHECK", "1").strip().lower() not in {"0", "false", "off"})


def run_geometric_estimate(
    front_bytes: bytes | None,
    side_bytes: bytes | None,
    height_cm: float,
    capture_mode: str,
) -> dict[str, Any]:
    """Estimate core measurements from silhouettes, or explain why it cannot."""
    result: dict[str, Any] = {
        "available": False,
        "reason": "",
        "measurements": {key: None for key in GEOMETRY_METRICS},
        "warnings": [],
    }
    if not front_bytes or not side_bytes:
        result["reason"] = "Không có ảnh gốc để chạy kiểm tra hình học."
        return result
    if not geometric_check_enabled():
        result["reason"] = "Kiểm tra hình học bị tắt (MORPH_AI_GEOMETRY_CHECK=0)."
        return result
    try:
        # Imported lazily: ai_scan stays importable on installs without the
        # MediaPipe model files, and this thread does not block the event loop.
        from .. import reconstruction
        from ..anatomy import template_landmarks
        from ..camera_fusion import fuse_camera_scale
        from ..images import InvalidPhoto, decode_photo
        from ..measurements import estimate_from_profiles
        from ..torso_mask import more_visible_arm_side

        front = decode_photo(front_bytes)
        side = decode_photo(side_bytes)
        detector = reconstruction.get_detector()
        with reconstruction._detector_lock:
            frontal = reconstruction.observe(front, detector, "chính diện", capture_mode)
            lateral = reconstruction.observe(side, detector, "góc nghiêng", capture_mode)

        front_shoulders = abs(frontal.points[11, 0] - frontal.points[12, 0]) / frontal.height
        side_shoulders = abs(lateral.points[11, 0] - lateral.points[12, 0]) / lateral.height
        if front_shoulders < 0.12:
            raise InvalidPhoto("Ảnh chính diện chưa thẳng mặt; bỏ qua kiểm tra hình học.")
        if side_shoulders > front_shoulders * 0.75:
            raise InvalidPhoto("Ảnh thứ hai chưa đủ nghiêng 90°; bỏ qua kiểm tra hình học.")

        fuse_camera_scale(frontal, lateral)
        fractions, widths = reconstruction.torso_profile(
            frontal, reference_obs=None, norm_height=frontal.height
        )
        if getattr(frontal, "arm_radius_px", None):
            import numpy as np

            lateral.arm_radius_hint = (
                float(np.mean(list(frontal.arm_radius_px.values())))
                * float(lateral.height)
                / max(float(frontal.height), 1.0)
            )
        _, depths = reconstruction.torso_profile(
            lateral,
            reference_obs=frontal,
            norm_height=lateral.height,
            arm_sides=(more_visible_arm_side(lateral.points, lateral.visibility),),
        )
        landmarks = template_landmarks(str(reconstruction.TEMPLATE_PATH))
        measurements, _targets = estimate_from_profiles(
            fractions,
            widths,
            depths,
            height_cm,
            front_shoulders,
            True,
            landmarks.get("shoulder", 0.805),
            landmarks.get("hip", 0.515),
        )
        for key in GEOMETRY_METRICS:
            value = measurements.get(key)
            if capture_mode == "upper_body" and key == "hip_cm":
                value = None
            result["measurements"][key] = float(value) if value is not None else None
        result["available"] = any(v is not None for v in result["measurements"].values())
        result["warnings"] = [
            w for w in getattr(frontal, "arm_removal_warnings", [])[:2]
        ]
        if not result["available"]:
            result["reason"] = "Hình học không xác định được vòng nào."
    except Exception as exc:  # noqa: BLE001 - geometry must never fail the scan
        logger.info("Geometric cross-check skipped: %s", exc)
        result["available"] = False
        result["reason"] = str(exc)[:200]
    return result
