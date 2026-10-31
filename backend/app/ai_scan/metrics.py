"""Shared metric tables for the AI scan ensemble.

One source of truth for the metric list, plausible bounds, Vietnamese labels
and the agreement tolerances used when fusing ensemble members and the
MediaPipe geometric estimate. The bounds match the values previously kept in
``graph.py`` so validation behaviour is unchanged.
"""
from __future__ import annotations

# (key, Vietnamese label, plausible low cm, plausible high cm)
METRICS: tuple[tuple[str, str, float, float], ...] = (
    ("chest_cm", "Vòng ngực", 55.0, 190.0),
    ("waist_cm", "Vòng eo", 40.0, 190.0),
    ("hip_cm", "Vòng mông", 55.0, 200.0),
    ("shoulder_width_cm", "Rộng vai", 20.0, 80.0),
    ("chest_width_cm", "Ngang ngực", 20.0, 80.0),
    ("chest_depth_cm", "Sâu ngực", 10.0, 60.0),
    ("waist_width_cm", "Ngang eo", 15.0, 80.0),
    ("waist_depth_cm", "Sâu eo", 8.0, 60.0),
    ("hip_width_cm", "Ngang mông", 20.0, 90.0),
    ("hip_depth_cm", "Sâu mông", 10.0, 60.0),
)

CORE_METRICS = tuple(metric[0] for metric in METRICS[:4])
METRIC_LABELS = {key: label for key, label, _low, _high in METRICS}

# Plausible value / height ratios. Outside these ranges we keep the number but
# lower confidence and surface a warning; we never fabricate a correction.
RATIO_BOUNDS: dict[str, tuple[float, float]] = {
    "chest_cm": (0.38, 0.75),
    "waist_cm": (0.28, 0.65),
    "hip_cm": (0.38, 0.72),
    "shoulder_width_cm": (0.16, 0.32),
    "chest_width_cm": (0.14, 0.35),
    "chest_depth_cm": (0.08, 0.30),
    "waist_width_cm": (0.10, 0.32),
    "waist_depth_cm": (0.06, 0.28),
    "hip_width_cm": (0.15, 0.40),
    "hip_depth_cm": (0.08, 0.32),
}

# Max spread (cm) between ensemble members before we flag a metric as
# unstable. Circumferences are harder to pin down than straight widths, so
# they get a wider band.
DISPERSION_TOLERANCE_CM: dict[str, float] = {
    "chest_cm": 6.0,
    "waist_cm": 6.0,
    "hip_cm": 7.0,
    "shoulder_width_cm": 4.0,
    "chest_width_cm": 3.5,
    "chest_depth_cm": 3.5,
    "waist_width_cm": 3.0,
    "waist_depth_cm": 3.0,
    "hip_width_cm": 4.0,
    "hip_depth_cm": 4.0,
}

# Max |AI - MediaPipe geometry| difference (cm) treated as agreement when
# fusing the two independent estimators.
GEOMETRY_FUSION_TOLERANCE_CM: dict[str, float] = {
    "chest_cm": 5.0,
    "waist_cm": 5.0,
    "hip_cm": 6.0,
    "shoulder_width_cm": 3.0,
}

# Metrics the MediaPipe geometric estimator can support (estimate_from_profiles
# output that maps 1:1 onto AI metrics).
GEOMETRY_METRICS = ("chest_cm", "waist_cm", "hip_cm", "shoulder_width_cm")
