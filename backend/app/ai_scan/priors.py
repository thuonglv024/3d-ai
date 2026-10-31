"""Statistical post-processing for ensemble measurements.

Two deterministic layers run after the AI aggregation:

1. ``apply_bias_correction`` — per-metric linear map ``y = a * x + b``. The
   coefficients are identity by default; fit them on a tape-measured dataset
   (30-50 subjects) and fill the table in. Until then this layer is a no-op
   that exists so the calibration hook is testable, and it never changes a
   value that has no coefficient.
2. ``apply_prior`` — a plausibility guard plus an *opt-in* shrink toward an
   anthropometric prior conditioned on height and sex.

The default for the shrink step is **off** (``MORPH_AI_PRIOR_SHRINK=0``). With
no tape-measured calibration set, shrinking a plausible estimate toward a
population mean injects an unmeasurable bias and makes a correct measurement
wrong; on the only real subject measured so far (156 cm, tape waist 60 cm) the
female waist prior would pull a correct 60 cm up to about 63 cm. So by default
this module only *flags*: it computes the z-score of every core measurement
against the prior, lowers that metric's confidence when the value is rare or
extreme, and raises a user-facing warning. It never rewrites the number.

When an operator turns the shrink on, every changed value is reported as a
``before -> after`` warning and the metric's ``estimated_by`` becomes
``ensemble+prior``, so a number can never be silently edited.

The prior table is a reference ratio set, not a validated population dataset:
no citable table, page or release of ANSUR II / SizeUK is recorded yet, and it
is not Vietnamese population data. Treat it as a plausibility band only.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .metrics import CORE_METRICS, METRIC_LABELS

# (mean ratio to height, sd ratio to height) per sex. PROVISIONAL reference
# magnitudes, not a citation: do not present these as ANSUR II or SizeUK data.
PRIOR_RATIOS: dict[str, dict[str, tuple[float, float]]] = {
    "female": {
        "chest_cm": (0.545, 0.045),
        "waist_cm": (0.450, 0.045),
        "hip_cm": (0.575, 0.040),
        "shoulder_width_cm": (0.222, 0.018),
    },
    "male": {
        "chest_cm": (0.535, 0.045),
        "waist_cm": (0.475, 0.050),
        "hip_cm": (0.545, 0.038),
        "shoulder_width_cm": (0.245, 0.018),
    },
}
# "auto": average of both means, wider spread.
UNKNOWN_PRIOR_RATIOS: dict[str, tuple[float, float]] = {
    key: ((PRIOR_RATIOS["female"][key][0] + PRIOR_RATIOS["male"][key][0]) / 2,
          (PRIOR_RATIOS["female"][key][1] + PRIOR_RATIOS["male"][key][1]) / 2 * 1.25)
    for key in PRIOR_RATIOS["female"]
}

LOW_DENSITY_Z = 2.5
EXTREME_Z = 4.0
LOW_DENSITY_CONFIDENCE_CAP = 0.55
EXTREME_CONFIDENCE_CAP = 0.35

# Opt-in switch for the shrink step. Default off: no calibration data yet.
SHRINK_ENV = "MORPH_AI_PRIOR_SHRINK"

# Linear bias correction (a, b): fitted = a * raw + b. Identity until a
# tape-measured calibration dataset is collected; see docs/AI_SCAN_FEATURE.md.
BIAS_CORRECTION: dict[str, tuple[float, float]] = {
    "chest_cm": (1.0, 0.0),
    "waist_cm": (1.0, 0.0),
    "hip_cm": (1.0, 0.0),
    "shoulder_width_cm": (1.0, 0.0),
}


@dataclass(frozen=True)
class PriorOutcome:
    """Result of the prior layer, with every edit made visible."""

    values: dict[str, float | None]
    warnings: list[str] = field(default_factory=list)
    # key -> (before, after); empty unless the shrink step is enabled.
    adjustments: dict[str, tuple[float, float]] = field(default_factory=dict)
    # key -> maximum confidence for that metric (guard, always applied).
    confidence_caps: dict[str, float] = field(default_factory=dict)


def shrink_enabled() -> bool:
    """True only when an operator opts into shrinking toward the prior."""
    raw = os.getenv(SHRINK_ENV, "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def apply_bias_correction(values: dict[str, float | None]) -> dict[str, float | None]:
    corrected = dict(values)
    for key, (a, b) in BIAS_CORRECTION.items():
        raw = corrected.get(key)
        if raw is None:
            continue
        corrected[key] = round(a * float(raw) + b, 1)
    return corrected


def _prior_table(sex: str) -> dict[str, tuple[float, float]]:
    return PRIOR_RATIOS.get(sex) or UNKNOWN_PRIOR_RATIOS


def apply_prior(
    values: dict[str, float | None],
    metric_confidence: dict[str, float],
    height_cm: float,
    sex: str,
    shrink: bool | None = None,
) -> PriorOutcome:
    """Flag implausible values; shrink only when explicitly enabled.

    ``shrink=None`` reads ``MORPH_AI_PRIOR_SHRINK`` (default off). The guard
    always runs: a rare value keeps its number, loses confidence and gains a
    warning, because without calibration data the prior is not good enough to
    overrule a measurement.
    """
    if height_cm <= 0:
        return PriorOutcome(values=dict(values))
    do_shrink = shrink_enabled() if shrink is None else bool(shrink)
    table = _prior_table(sex)
    out_values = dict(values)
    warnings: list[str] = []
    adjustments: dict[str, tuple[float, float]] = {}
    caps: dict[str, float] = {}

    for key, (mean_ratio, sd_ratio) in table.items():
        raw = out_values.get(key)
        if raw is None:
            continue
        label = METRIC_LABELS.get(key, key)
        value = float(raw)
        prior_mean = mean_ratio * height_cm
        sd = max(sd_ratio * height_cm, 1.0)
        z = (value - prior_mean) / sd
        severe = abs(z) > EXTREME_Z
        rare = abs(z) > LOW_DENSITY_Z

        if severe:
            caps[key] = EXTREME_CONFIDENCE_CAP
            warnings.append(
                f"{label}: {value:.1f} cm rất hiếm so với chiều cao {height_cm:.0f} cm "
                f"(khoảng tham khảo {prior_mean:.0f} cm, bảng prior chưa hiệu chuẩn). "
                "Số đo được giữ nguyên nhưng độ tin cậy bị hạ mạnh; nên đo lại bằng thước dây."
            )
        elif rare:
            caps[key] = LOW_DENSITY_CONFIDENCE_CAP
            warnings.append(
                f"{label}: {value:.1f} cm hiếm gặp ở người cao {height_cm:.0f} cm "
                f"(khoảng tham khảo {prior_mean:.0f} cm, bảng prior chưa hiệu chuẩn). "
                "Số đo được giữ nguyên; nên kiểm tra lại bằng thước dây."
            )

        if not do_shrink:
            continue
        confidence = float(metric_confidence.get(key, 0.5))
        if severe:
            weight = 0.35
        elif rare:
            weight = 0.55
        else:
            weight = min(0.95, max(0.55, 0.55 + 0.35 * confidence))
        blended = round(weight * value + (1.0 - weight) * prior_mean, 1)
        if blended == value:
            continue
        out_values[key] = blended
        adjustments[key] = (value, blended)
        warnings.append(
            f"{label}: {value:.1f} -> {blended:.1f} cm "
            f"(kéo về prior theo chiều cao và giới tính, chưa hiệu chuẩn)."
        )

    return PriorOutcome(
        values=out_values,
        warnings=warnings,
        adjustments=adjustments,
        confidence_caps=caps,
    )


def consistency_checks(values: dict[str, float | None], sex: str) -> list[str]:
    """Cross-metric proportion warnings, deterministic and sex aware."""
    warnings: list[str] = []
    chest = values.get("chest_cm")
    waist = values.get("waist_cm")
    hip = values.get("hip_cm")
    shoulder = values.get("shoulder_width_cm")
    chest_width = values.get("chest_width_cm")

    if chest is not None and hip is not None:
        # The pelvis is never drastically narrower than the chest.
        floor = 6.0 if sex == "female" else 12.0
        if hip < chest - floor:
            warnings.append(
                "Vòng mông nhỏ hơn vòng ngực quá nhiều so với tỉ lệ cơ thể phổ biến; "
                "một trong hai số đo có thể chưa chính xác."
            )
    if waist is not None and hip is not None and waist > hip + 6:
        warnings.append(
            "Vòng eo lớn hơn vòng mông; hãy kiểm tra lại vị trí đo eo (trên rốn, không phải cạp quần)."
        )
    if shoulder is not None and chest_width is not None and shoulder < chest_width * 0.85:
        warnings.append(
            "Rộng vai nhỏ hơn ngang ngực một cách bất thường; "
            "mốc vai có thể bị nhận sai hoặc bị che trong ảnh."
        )
    return warnings


def supported_prior_metrics() -> tuple[str, ...]:
    return tuple(key for key in CORE_METRICS if key in UNKNOWN_PRIOR_RATIOS)
