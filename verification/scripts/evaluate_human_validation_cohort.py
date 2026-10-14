"""
Anthropometric Validation & Statistical Calibration Harness for MORPH AI.

Implements:
  1. ISO 7250-1:2017 & ISO 8559-1:2017 vs. Algorithmic Measurement Cross-Walk
     (including MediaPipe Landmarks 11-12 vs. Acromion shoulder offset analysis).
  2. Real-Human Dataset Manifest & Informed Consent Audit + Intra/Inter-Observer
     Technical Error of Measurement (TEM) Verification + Subject-Disjoint Split Guard.
  3. Non-Parametric Calibrated Prediction Intervals (replacing ±1.96 * RMSE):
       - Bias-Corrected Split Conformal Prediction Intervals (90% & 95%)
       - Asymmetric Empirical Residual Quantile Intervals ([q_{alpha/2}, q_{1-alpha/2}])
  4. Held-Out Empirical Coverage (%) and Mean/Median Interval Width (cm) evaluation
     across capture modes (`full_body`, `upper_body`), metrics (`chest_cm`, `waist_cm`,
     `hip_cm`, `shoulder_width_cm`), and independent subgroups (`torso_ratio_group`,
     `body_size_tier`, `sex`, `perturbation_condition`).
  5. Explicit non-acceptance verdict (`NOT_ACCEPTED_NO_EMPIRICAL_DATASET`) when no
     consented real-human dataset is present in `verification/datasets/real_human_pilot/`.

Run with:
    D:\\MORPH-AI\\backend\\.venv\\Scripts\\python.exe verification\\scripts\\evaluate_human_validation_cohort.py
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
REAL_HUMAN_DATASET_DIR = ROOT / "verification" / "datasets" / "real_human_pilot"
CACHE_DIR = ROOT / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
VALIDATION_OUTPUT_DIR = ROOT / "output" / "runs" / "run-20261014-v2" / "validation"
VALIDATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CACHE_REPORT_PATH = CACHE_DIR / "human_validation_cohort_report.json"
RUN_VALIDATION_REPORT_PATH = VALIDATION_OUTPUT_DIR / "human_validation_cohort_report.json"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(ROOT / "verification" / "scripts"))

from app.measurements import ANATOMICAL_SECTION_FACTORS, closed_torso_section  # noqa: E402
from app.reconstruction import ENGINE, read_template, reconstruct  # noqa: E402
from app.sizing import filter_valid_sizing_measurements  # noqa: E402


# ==============================================================================
# 1. ISO 7250-1:2017 & ISO 8559-1:2017 VS ALGORITHMIC MEASUREMENT CROSS-WALK
# ==============================================================================

ISO_VS_ALGORITHM_MEASUREMENT_MAPPING: dict[str, dict[str, Any]] = {
    "height_cm": {
        "iso_standards": [
            "ISO 7250-1:2017 Clause 6.1.1 (Stature / Body height)",
            "ISO 8559-1:2017 Clause 5.1.1 (Stature)",
        ],
        "anatomical_definition": (
            "Khoảng cách thẳng đứng từ mặt sàn (standing surface) đến điểm cao nhất của hộp sọ "
            "(Vertex) khi đầu định hướng trên mặt phẳng Frankfort, đi chân trần."
        ),
        "algorithm_implementation": (
            "Người dùng tự nhập (`source = 'user_input'`), không suy đoán từ camera 2D thiếu chiều sâu. "
            "Dùng làm hệ số quy đổi toàn cục từ chiều cao pixel đồng bộ (`shared_height`) sang cm và "
            "scale trục Y của lưới MakeHuman (`vertices *= height_cm / 100`)."
        ),
        "code_references": [
            "backend/app/measurements.py:estimate_from_profiles (line 47)",
            "backend/app/reconstruction.py:deform_template (line 358)",
        ],
        "structural_offset_and_validation_note": (
            "Sai số tự nhập chiều cao Delta_H kéo theo sai số tỷ lệ tuyến tính (~Delta_H / H) trên mọi số đo. "
            "Trong nghiệm thu Pilot, phải đo Stadiometer chuẩn tới 0.1 cm làm đầu vào基准 (baseline)."
        ),
    },
    "shoulder_width_cm": {
        "iso_standards": [
            "ISO 7250-1:2017 Clause 6.2.1 (Biacromial breadth)",
            "ISO 8559-1:2017 Clause 5.4.1 (Shoulder width / Back shoulder width)",
            "ISO 7250-1:2017 Clause 6.2.2 (Bideltoid breadth)",
        ],
        "anatomical_definition": (
            "ISO 7250-1 (6.2.1): Khoảng cách thẳng giữa hai mỏm cùng vai xương bả vai (Acromion) đo bằng thước kẹp. "
            "ISO 8559-1 (5.4.1): Khoảng cách qua bề mặt lưng hoặc giữa hai mỏm Acromion."
        ),
        "algorithm_implementation": (
            "Tính `shoulder_width_cm = round(shoulder_ratio * height_cm, 1)` với "
            "`shoulder_ratio = abs(frontal.points[11, 0] - frontal.points[12, 0]) / shared_height` "
            "(khoảng cách ngang Euclidean 2D giữa hai mốc MediaPipe Pose Landmarks 11 và 12)."
        ),
        "code_references": [
            "backend/app/reconstruction.py:reconstruct (line 373)",
            "backend/app/measurements.py:estimate_from_profiles (line 47)",
        ],
        "structural_offset_and_validation_note": (
            "LANDMARK OFFSET BIAS: Mốc MediaPipe 11 & 12 là tâm khớp vai 2D (glenohumeral joint centers) suy từ ảnh RGB, "
            "nằm thấp hơn và dịch vào trong (medial) khoảng 1.2–2.2 cm mỗi bên (tổng ~2.4–4.4 cm) so với mỏm xương "
            "Acromion ngoài da. Khi đo kiểm trên người thật bắt buộc ghi nhận cả `shoulder_biacromial_gt_cm` (Acromion) "
            "và `shoulder_joint_gt_cm` (liên tâm khớp vai) để lượng hóa và khử độ chệch mốc này."
        ),
    },
    "chest_cm": {
        "iso_standards": [
            "ISO 8559-1:2017 Clause 5.3.4 (Chest girth / Bust girth)",
            "ISO 7250-1:2017 Clause 6.4.6 (Chest circumference)",
        ],
        "anatomical_definition": (
            "Chu vi thân ngang đo bằng thước dây đi qua điểm nhô cao nhất của bầu ngực (Thelion / Bustpoint) "
            "hoặc mức xương ức giữa (Mesosternale — khoang liên sườn 4), song song với mặt sàn ở cuối thì thở ra bình thường."
        ),
        "algorithm_implementation": (
            "Tìm chu vi mặt cắt ngang lớn nhất (`choice = 'max'`) trong dải tỷ lệ thân `fractions in [0.30, 0.44]` "
            "(ánh xạ vào mức chiều cao lưới `level = 0.805 - 0.290 * f in [0.6774*H, 0.7180*H]`, thuộc dải ngực "
            "`~0.68*H .. 0.79*H` tính từ mặt đất trên lưới MakeHuman đã biến dạng), nhân hệ số bù lõm giải phẫu "
            "`ANATOMICAL_SECTION_FACTORS['chest_cm'] = 1 / (1 - 0.074710) = 1.08074` (+8.07%)."
        ),
        "code_references": [
            "backend/app/measurements.py:ANATOMICAL_SECTION_FACTORS (line 21)",
            "backend/app/measurements.py:estimate_from_profiles (lines 46-67)",
            "backend/app/measurements.py:fit_measurement_targets (lines 208-250)",
        ],
        "structural_offset_and_validation_note": (
            "Đòi hỏi hai cánh tay tách khỏi sườn 15°–25° ở ảnh chính diện để `center_run_width` không gộp bóng nách vào ngực."
        ),
    },
    "waist_cm": {
        "iso_standards": [
            "ISO 8559-1:2017 Clause 5.3.10 (Waist girth / Natural waist)",
            "ISO 7250-1:2017 Clause 6.4.7 (Waist circumference)",
        ],
        "anatomical_definition": (
            "Chu vi ngang nhỏ nhất của phần thân tự nhiên nằm giữa bờ dưới xương sườn thứ 10 (10th rib) "
            "và bờ trên mào chậu (Iliocristale), thước dây song song với mặt sàn."
        ),
        "algorithm_implementation": (
            "Tìm chu vi mặt cắt ngang nhỏ nhất (`choice = 'min'`) trong dải tỷ lệ thân `fractions in [0.52, 0.78]` "
            "(ánh xạ vào mức chiều cao lưới `level = 0.805 - 0.290 * f in [0.5788*H, 0.6542*H]`, thuộc dải eo "
            "`0.56*H .. 0.66*H` tính từ sàn), nhân hệ số bù lõm giải phẫu "
            "`ANATOMICAL_SECTION_FACTORS['waist_cm'] = 1 / (1 - 0.031088) = 1.03209` (+3.21%)."
        ),
        "code_references": [
            "backend/app/measurements.py:ANATOMICAL_SECTION_FACTORS (line 22)",
            "backend/app/measurements.py:estimate_from_profiles (lines 46-67)",
        ],
        "structural_offset_and_validation_note": (
            "Tương thích trực tiếp với định nghĩa Natural Waist (chu vi thân nhỏ nhất) của ISO 8559-1 Clause 5.3.10."
        ),
    },
    "hip_cm": {
        "iso_standards": [
            "ISO 8559-1:2017 Clause 5.3.13 (Hip girth / Seat girth)",
            "ISO 7250-1:2017 Clause 6.4.8 (Hip circumference)",
        ],
        "anatomical_definition": (
            "Chu vi ngang lớn nhất đi qua vùng nhô cao nhất của cơ mông phía sau (Gluteal prominence / Buttock protrusion) "
            "song song với mặt sàn, hai bàn chân khép sát."
        ),
        "algorithm_implementation": (
            "Tìm chu vi mặt cắt ngang lớn nhất (`choice = 'max'`) trong dải tỷ lệ thân `fractions in [0.95, 1.12]` "
            "(ánh xạ vào mức chiều cao lưới `level = 0.805 - 0.290 * f in [0.4802*H, 0.5295*H]`, thuộc dải mông "
            "`0.48*H .. 0.54*H` tính từ sàn), nhân hệ số `ANATOMICAL_SECTION_FACTORS['hip_cm'] = 1 / (1 - 0.058685) = 1.06234` (+6.23%). "
            "Khi `capture_mode == 'upper_body'`, khóa cứng `hip_cm = None` (`source = 'template_model'`)."
        ),
        "code_references": [
            "backend/app/measurements.py:ANATOMICAL_SECTION_FACTORS (line 23)",
            "backend/app/measurements.py:estimate_from_profiles (lines 46-67)",
            "backend/app/reconstruction.py:reconstruct (lines 383-404)",
        ],
        "structural_offset_and_validation_note": (
            "Chỉ đo từ ảnh trong chế độ `full_body`. Trong chế độ `upper_body`, `hip_cm` bị khóa `None` và bị chặn khỏi gợi ý size."
        ),
    },
}


# ==============================================================================
# 2. PROPOSED PILOT TARGET THRESHOLDS (INTERNAL ENGINEERING TARGETS)
# ==============================================================================

PROPOSED_PILOT_TARGET_THRESHOLDS: dict[str, Any] = {
    "threshold_classification": "PROPOSED_PILOT_ENGINEERING_TARGETS",
    "is_iso_international_mandate": False,
    "is_empirically_proven_on_humans": False,
    "derivation_rationale": (
        "Đề xuất kỹ thuật nội bộ cho giai đoạn Pilot dựa trên nửa bước nhảy bảng size may sẵn "
        "(Ready-to-Wear grade step = 4.0-8.0 cm, bán kính nửa bậc size = ±2.0-4.0 cm). "
        "ISO 8559-1:2017 và ISO 7250-1:2017 chỉ chuẩn hóa vị trí mốc đo, không quy định các ngưỡng sai số này."
    ),
    "ground_truth_tem_quality_gates": {
        "intra_observer_tem_max_cm": 0.40,
        "inter_observer_tem_max_cm": 0.60,
        "relative_tem_max_pct": 1.00,
    },
    "full_body_proposed_targets": {
        "chest_cm": {"mae_max_cm": 2.5, "abs_bias_max_cm": 1.0, "p90_max_cm": 4.0, "p95_max_cm": 5.0, "repeatability_sd_max_cm": 0.8},
        "waist_cm": {"mae_max_cm": 2.5, "abs_bias_max_cm": 1.0, "p90_max_cm": 4.0, "p95_max_cm": 5.0, "repeatability_sd_max_cm": 0.8},
        "hip_cm": {"mae_max_cm": 2.5, "abs_bias_max_cm": 1.0, "p90_max_cm": 4.0, "p95_max_cm": 5.0, "repeatability_sd_max_cm": 0.8},
        "shoulder_width_cm": {"mae_max_cm": 1.8, "abs_bias_max_cm": 1.0, "p90_max_cm": 3.2, "p95_max_cm": 4.0, "repeatability_sd_max_cm": 0.6},
        "size_agreement_min_pct": 85.0,
        "true_rejection_rate_min_pct": 95.0,
    },
    "upper_body_proposed_targets": {
        "chest_cm": {"mae_max_cm": 3.0, "abs_bias_max_cm": 1.2, "p90_max_cm": 4.5, "p95_max_cm": 5.5, "repeatability_sd_max_cm": 1.0},
        "waist_cm": {"mae_max_cm": 3.0, "abs_bias_max_cm": 1.2, "p90_max_cm": 4.5, "p95_max_cm": 5.5, "repeatability_sd_max_cm": 1.0},
        "hip_cm": {"status": "BLOCKED_NONE", "coverage_target_pct": 0.0},
        "shoulder_width_cm": {"mae_max_cm": 2.0, "abs_bias_max_cm": 1.2, "p90_max_cm": 3.5, "p95_max_cm": 4.5, "repeatability_sd_max_cm": 0.8},
        "size_agreement_top_only_min_pct": 82.0,
        "true_rejection_rate_min_pct": 95.0,
    },
}


# ==============================================================================
# 3. TECHNICAL ERROR OF MEASUREMENT (TEM) & SUBJECT-DISJOINT VERIFICATION
# ==============================================================================

def verify_subject_disjoint_split(
    calibration_subjects: list[str] | set[str],
    evaluation_subjects: list[str] | set[str],
) -> dict[str, Any]:
    """Ensure calibration and evaluation splits share zero subject IDs."""
    cal_set = {str(s).strip() for s in calibration_subjects if str(s).strip()}
    eval_set = {str(s).strip() for s in evaluation_subjects if str(s).strip()}
    if not cal_set:
        raise ValueError("Tập hiệu chuẩn (calibration_subjects) không được rỗng.")
    if not eval_set:
        raise ValueError("Tập đánh giá độc lập (evaluation_subjects) không được rỗng.")
    overlap = sorted(cal_set & eval_set)
    if overlap:
        raise ValueError(
            f"DATA LEAKAGE DETECTED: {len(overlap)} subject_id(s) xuất hiện ở cả tập "
            f"calibration và evaluation: {overlap}"
        )
    return {
        "disjoint_verified": True,
        "calibration_subject_count": len(cal_set),
        "evaluation_subject_count": len(eval_set),
        "overlapping_subjects": [],
        "calibration_subjects": sorted(cal_set),
        "evaluation_subjects": sorted(eval_set),
    }


def compute_anthropometric_tem(
    measurer_a_trial1: np.ndarray | list[float],
    measurer_a_trial2: np.ndarray | list[float],
    measurer_b_trial1: np.ndarray | list[float],
    measurer_b_trial2: np.ndarray | list[float],
) -> dict[str, float | bool]:
    """Compute Intra-observer TEM, Inter-observer TEM, and Relative %TEM per ISO/ISAK protocol."""
    a1 = np.asarray(measurer_a_trial1, dtype=float)
    a2 = np.asarray(measurer_a_trial2, dtype=float)
    b1 = np.asarray(measurer_b_trial1, dtype=float)
    b2 = np.asarray(measurer_b_trial2, dtype=float)
    n = len(a1)
    if n == 0 or not (len(a2) == len(b1) == len(b2) == n):
        raise ValueError("Các mảng số đo lặp của Measurer A và B phải cùng độ dài N > 0.")

    tem_intra_a = float(np.sqrt(np.sum(np.square(a1 - a2)) / (2.0 * n)))
    tem_intra_b = float(np.sqrt(np.sum(np.square(b1 - b2)) / (2.0 * n)))
    tem_intra_pooled = float(np.sqrt((np.sum(np.square(a1 - a2)) + np.sum(np.square(b1 - b2))) / (4.0 * n)))

    mean_a = 0.5 * (a1 + a2)
    mean_b = 0.5 * (b1 + b2)
    tem_inter = float(np.sqrt(np.sum(np.square(mean_a - mean_b)) / (2.0 * n)))

    grand_mean = float(np.mean(0.25 * (a1 + a2 + b1 + b2)))
    rel_tem_intra_pct = float((tem_intra_pooled / max(grand_mean, 1e-6)) * 100.0)
    rel_tem_inter_pct = float((tem_inter / max(grand_mean, 1e-6)) * 100.0)

    return {
        "n_subjects": int(n),
        "grand_mean_cm": round(grand_mean, 2),
        "tem_intra_measurer_a_cm": round(tem_intra_a, 4),
        "tem_intra_measurer_b_cm": round(tem_intra_b, 4),
        "tem_intra_pooled_cm": round(tem_intra_pooled, 4),
        "tem_inter_cm": round(tem_inter, 4),
        "relative_tem_intra_pct": round(rel_tem_intra_pct, 4),
        "relative_tem_inter_pct": round(rel_tem_inter_pct, 4),
        "passes_protocol_gate": bool(
            tem_intra_pooled <= 0.40 and tem_inter <= 0.60 and rel_tem_inter_pct < 1.00
        ),
    }


# ==============================================================================
# 4. CALIBRATED PREDICTION INTERVALS (SPLIT CONFORMAL & EMPIRICAL QUANTILES)
# ==============================================================================

def compute_calibrated_interval_parameters(
    cal_gt: np.ndarray | list[float],
    cal_pred: np.ndarray | list[float],
    alphas: tuple[float, ...] = (0.10, 0.05),
) -> dict[str, Any]:
    """Fit non-parametric Split Conformal and Asymmetric Quantile Intervals on D_cal.

    Replaces the invalid parametric `±1.96 * RMSE` assumption.
    Let signed residual on calibration set be `r_i = y_i^{GT} - y_hat_i`.
    Then for a new prediction `y_hat`:
      - Bias-corrected point estimate: `y_hat_bc = y_hat + mu_cal`, where `mu_cal = mean(r_i)`.
      - Nonconformity score: `s_i = |r_i - mu_cal|`.
      - Finite-sample conformal quantile level: `p_conf = min(1.0, ceil((n + 1) * (1 - alpha)) / n)`.
      - Symmetric bias-corrected conformal interval:
            `[y_hat + mu_cal - q_conf, y_hat + mu_cal + q_conf]`
      - Asymmetric empirical residual quantile interval:
            `[y_hat + Quantile(r, alpha/2), y_hat + Quantile(r, 1 - alpha/2)]`
    """
    y_gt = np.asarray(cal_gt, dtype=float)
    y_hat = np.asarray(cal_pred, dtype=float)
    n = int(len(y_gt))
    if n == 0 or len(y_hat) != n:
        raise ValueError("Calibration ground-truth and prediction arrays must be non-empty and equal length.")

    # Signed residual r_i = y_GT - y_hat (so y_GT = y_hat + r_i)
    residuals = y_gt - y_hat
    mu_cal = float(np.mean(residuals))
    nonconformity_scores = np.abs(residuals - mu_cal)

    intervals_by_level: dict[str, Any] = {}
    for alpha in alphas:
        level_pct = int(round((1.0 - alpha) * 100))
        level_key = f"ci_{level_pct}"
        p_conf = min(1.0, math.ceil((n + 1) * (1.0 - alpha)) / float(n))
        # Using 'higher' / conservative linear quantile on nonconformity scores
        q_conf = float(np.quantile(nonconformity_scores, p_conf, method="weibull" if hasattr(np, "quantile") else "linear"))
        # Standard numpy quantile with linear interpolation at p_conf
        q_conf = float(np.quantile(nonconformity_scores, p_conf))

        q_low_raw = float(np.quantile(residuals, alpha / 2.0))
        q_high_raw = float(np.quantile(residuals, 1.0 - alpha / 2.0))

        intervals_by_level[level_key] = {
            "target_coverage_pct": round((1.0 - alpha) * 100.0, 1),
            "alpha": alpha,
            "n_calibration_samples": n,
            "conformal_quantile_level": round(p_conf, 5),
            "split_conformal_bias_corrected": {
                "bias_correction_cm": round(mu_cal, 3),
                "half_width_cm": round(q_conf, 3),
                "interval_width_cm": round(2.0 * q_conf, 3),
                "formula": "y_hat + bias_correction_cm ± half_width_cm",
            },
            "asymmetric_empirical_quantile": {
                "lower_offset_cm": round(q_low_raw, 3),
                "upper_offset_cm": round(q_high_raw, 3),
                "interval_width_cm": round(q_high_raw - q_low_raw, 3),
                "formula": "[y_hat + lower_offset_cm, y_hat + upper_offset_cm]",
            },
        }

    return {
        "n_calibration": n,
        "calibration_bias_correction_cm": round(mu_cal, 3),
        "calibration_mae_raw_cm": round(float(np.mean(np.abs(residuals))), 3),
        "calibration_mae_bias_corrected_cm": round(float(np.mean(nonconformity_scores)), 3),
        "intervals": intervals_by_level,
    }


def evaluate_intervals_on_records(
    eval_records: list[dict[str, Any]],
    cal_params: dict[str, Any],
    metric_key: str,
) -> dict[str, Any]:
    """Evaluate Empirical Coverage (%) and Interval Width (cm) on held-out records."""
    valid_recs = [
        r for r in eval_records
        if r.get("estimated_cm", {}).get(metric_key) is not None
        and r.get("ground_truth_cm", {}).get(metric_key) is not None
    ]
    m = len(valid_recs)
    if m == 0:
        return {
            "n_eval_samples": 0,
            "status": "BLOCKED_OR_UNAVAILABLE",
        }

    y_gt = np.array([float(r["ground_truth_cm"][metric_key]) for r in valid_recs], dtype=float)
    y_hat = np.array([float(r["estimated_cm"][metric_key]) for r in valid_recs], dtype=float)

    signed_err = y_hat - y_gt
    abs_err_raw = np.abs(signed_err)

    mu_cal = float(cal_params["calibration_bias_correction_cm"])
    y_hat_bc = y_hat + mu_cal
    abs_err_bc = np.abs(y_hat_bc - y_gt)

    coverage_report: dict[str, Any] = {}
    for level_key, params in cal_params["intervals"].items():
        # 1. Split Conformal Bias-Corrected
        hw = float(params["split_conformal_bias_corrected"]["half_width_cm"])
        low_sym = y_hat + mu_cal - hw
        high_sym = y_hat + mu_cal + hw
        in_sym = (y_gt >= low_sym) & (y_gt <= high_sym)
        widths_sym = high_sym - low_sym

        # 2. Asymmetric Empirical Quantile
        off_low = float(params["asymmetric_empirical_quantile"]["lower_offset_cm"])
        off_high = float(params["asymmetric_empirical_quantile"]["upper_offset_cm"])
        low_asym = y_hat + off_low
        high_asym = y_hat + off_high
        in_asym = (y_gt >= low_asym) & (y_gt <= high_asym)
        widths_asym = high_asym - low_asym

        coverage_report[level_key] = {
            "target_coverage_pct": params["target_coverage_pct"],
            "split_conformal_bias_corrected": {
                "empirical_coverage_pct": round(float(np.mean(in_sym) * 100.0), 2),
                "covered_count": int(np.sum(in_sym)),
                "total_eval_count": m,
                "half_width_cm": round(hw, 2),
                "mean_interval_width_cm": round(float(np.mean(widths_sym)), 2),
                "median_interval_width_cm": round(float(np.median(widths_sym)), 2),
            },
            "asymmetric_empirical_quantile": {
                "empirical_coverage_pct": round(float(np.mean(in_asym) * 100.0), 2),
                "covered_count": int(np.sum(in_asym)),
                "total_eval_count": m,
                "lower_offset_cm": round(off_low, 2),
                "upper_offset_cm": round(off_high, 2),
                "mean_interval_width_cm": round(float(np.mean(widths_asym)), 2),
                "median_interval_width_cm": round(float(np.median(widths_asym)), 2),
            },
        }

    return {
        "n_eval_samples": m,
        "raw_mae_cm": round(float(np.mean(abs_err_raw)), 2),
        "raw_signed_bias_cm": round(float(np.mean(signed_err)), 2),
        "raw_p90_abs_error_cm": round(float(np.percentile(abs_err_raw, 90)), 2),
        "raw_p95_abs_error_cm": round(float(np.percentile(abs_err_raw, 95)), 2),
        "bias_corrected_mae_cm": round(float(np.mean(abs_err_bc)), 2),
        "bias_corrected_p90_abs_error_cm": round(float(np.percentile(abs_err_bc, 90)), 2),
        "bias_corrected_p95_abs_error_cm": round(float(np.percentile(abs_err_bc, 95)), 2),
        "calibrated_intervals": coverage_report,
    }


# ==============================================================================
# 5. EXPANDED SUBJECT-DISJOINT SYNTHETIC COHORT FOR HARNESS VERIFICATION
# ==============================================================================

# 12 Calibration Subjects (strictly `subj_cal_*`) spanning torso ratios, sexes, and body tiers
SYNTHETIC_CALIBRATION_SUBJECTS: list[dict[str, Any]] = [
    {
        "subject_id": "subj_cal_001_neutral_template_170",
        "label": "Cal-01: Neutral Template (170cm)",
        "split": "calibration", "sex": "female", "body_size_tier": "standard_athletic", "torso_ratio_group": "medium_torso",
        "height_cm": 170.0, "r_torso": 0.290,
        "chest_w_cm": 29.9, "chest_d_cm": 20.5, "waist_w_cm": 25.3, "waist_d_cm": 19.6, "hip_w_cm": 33.9, "hip_d_cm": 23.2,
        "shoulder_ratio": 0.228, "acromion_offset_cm": 3.2,
    },
    {
        "subject_id": "subj_cal_002_female_ref_162",
        "label": "Cal-02: Reference Female (162cm)",
        "split": "calibration", "sex": "female", "body_size_tier": "standard_athletic", "torso_ratio_group": "medium_torso",
        "height_cm": 162.0, "r_torso": 0.285,
        "chest_w_cm": 28.2, "chest_d_cm": 20.2, "waist_w_cm": 23.0, "waist_d_cm": 17.2, "hip_w_cm": 33.0, "hip_d_cm": 22.8,
        "shoulder_ratio": 0.222, "acromion_offset_cm": 2.9,
    },
    {
        "subject_id": "subj_cal_003_male_ref_176",
        "label": "Cal-03: Reference Male (176cm)",
        "split": "calibration", "sex": "male", "body_size_tier": "standard_athletic", "torso_ratio_group": "medium_torso",
        "height_cm": 176.0, "r_torso": 0.295,
        "chest_w_cm": 33.5, "chest_d_cm": 23.4, "waist_w_cm": 27.2, "waist_d_cm": 20.2, "hip_w_cm": 33.5, "hip_d_cm": 23.2,
        "shoulder_ratio": 0.246, "acromion_offset_cm": 3.5,
    },
    {
        "subject_id": "subj_cal_004_petite_short_torso_154",
        "label": "Cal-04: Petite Short-Torso Female (154cm)",
        "split": "calibration", "sex": "female", "body_size_tier": "petite_slim", "torso_ratio_group": "short_torso",
        "height_cm": 154.0, "r_torso": 0.268,
        "chest_w_cm": 26.5, "chest_d_cm": 18.6, "waist_w_cm": 21.5, "waist_d_cm": 15.8, "hip_w_cm": 30.2, "hip_d_cm": 20.8,
        "shoulder_ratio": 0.219, "acromion_offset_cm": 2.7,
    },
    {
        "subject_id": "subj_cal_005_slim_long_torso_167",
        "label": "Cal-05: Slim Long-Torso Female (167cm)",
        "split": "calibration", "sex": "female", "body_size_tier": "petite_slim", "torso_ratio_group": "long_torso",
        "height_cm": 167.0, "r_torso": 0.308,
        "chest_w_cm": 27.8, "chest_d_cm": 19.5, "waist_w_cm": 22.4, "waist_d_cm": 16.5, "hip_w_cm": 31.8, "hip_d_cm": 21.8,
        "shoulder_ratio": 0.224, "acromion_offset_cm": 3.0,
    },
    {
        "subject_id": "subj_cal_006_curvy_female_164",
        "label": "Cal-06: Curvy Female (164cm)",
        "split": "calibration", "sex": "female", "body_size_tier": "broad_plus", "torso_ratio_group": "medium_torso",
        "height_cm": 164.0, "r_torso": 0.288,
        "chest_w_cm": 32.2, "chest_d_cm": 23.6, "waist_w_cm": 26.8, "waist_d_cm": 20.4, "hip_w_cm": 36.2, "hip_d_cm": 25.4,
        "shoulder_ratio": 0.231, "acromion_offset_cm": 3.1,
    },
    {
        "subject_id": "subj_cal_007_short_torso_male_171",
        "label": "Cal-07: Short-Torso Male (171cm)",
        "split": "calibration", "sex": "male", "body_size_tier": "standard_athletic", "torso_ratio_group": "short_torso",
        "height_cm": 171.0, "r_torso": 0.272,
        "chest_w_cm": 32.8, "chest_d_cm": 22.9, "waist_w_cm": 26.9, "waist_d_cm": 19.9, "hip_w_cm": 32.8, "hip_d_cm": 22.7,
        "shoulder_ratio": 0.244, "acromion_offset_cm": 3.4,
    },
    {
        "subject_id": "subj_cal_008_long_torso_male_180",
        "label": "Cal-08: Long-Torso Male (180cm)",
        "split": "calibration", "sex": "male", "body_size_tier": "standard_athletic", "torso_ratio_group": "long_torso",
        "height_cm": 180.0, "r_torso": 0.315,
        "chest_w_cm": 34.8, "chest_d_cm": 24.2, "waist_w_cm": 28.4, "waist_d_cm": 21.0, "hip_w_cm": 34.2, "hip_d_cm": 23.8,
        "shoulder_ratio": 0.251, "acromion_offset_cm": 3.6,
    },
    {
        "subject_id": "subj_cal_009_broad_plus_male_177",
        "label": "Cal-09: Broad Plus Male (177cm)",
        "split": "calibration", "sex": "male", "body_size_tier": "broad_plus", "torso_ratio_group": "medium_torso",
        "height_cm": 177.0, "r_torso": 0.296,
        "chest_w_cm": 36.8, "chest_d_cm": 26.8, "waist_w_cm": 32.4, "waist_d_cm": 25.2, "hip_w_cm": 36.4, "hip_d_cm": 25.8,
        "shoulder_ratio": 0.254, "acromion_offset_cm": 3.7,
    },
    {
        "subject_id": "subj_cal_010_slim_male_168",
        "label": "Cal-10: Slim Male (168cm)",
        "split": "calibration", "sex": "male", "body_size_tier": "petite_slim", "torso_ratio_group": "short_torso",
        "height_cm": 168.0, "r_torso": 0.278,
        "chest_w_cm": 30.2, "chest_d_cm": 21.0, "waist_w_cm": 24.8, "waist_d_cm": 18.2, "hip_w_cm": 31.2, "hip_d_cm": 21.5,
        "shoulder_ratio": 0.236, "acromion_offset_cm": 3.2,
    },
    {
        "subject_id": "subj_cal_011_plus_long_torso_173",
        "label": "Cal-11: Plus Long-Torso Female (173cm)",
        "split": "calibration", "sex": "female", "body_size_tier": "broad_plus", "torso_ratio_group": "long_torso",
        "height_cm": 173.0, "r_torso": 0.312,
        "chest_w_cm": 34.2, "chest_d_cm": 25.0, "waist_w_cm": 29.5, "waist_d_cm": 22.8, "hip_w_cm": 37.2, "hip_d_cm": 26.2,
        "shoulder_ratio": 0.235, "acromion_offset_cm": 3.3,
    },
    {
        "subject_id": "subj_cal_012_athletic_female_166",
        "label": "Cal-12: Athletic Female (166cm)",
        "split": "calibration", "sex": "female", "body_size_tier": "standard_athletic", "torso_ratio_group": "medium_torso",
        "height_cm": 166.0, "r_torso": 0.292,
        "chest_w_cm": 29.6, "chest_d_cm": 21.0, "waist_w_cm": 23.8, "waist_d_cm": 17.8, "hip_w_cm": 33.4, "hip_d_cm": 23.0,
        "shoulder_ratio": 0.232, "acromion_offset_cm": 3.1,
    },
]

# 10 Held-Out Evaluation Subjects (strictly `subj_eval_*`, 0 overlap with `subj_cal_*`)
SYNTHETIC_EVALUATION_SUBJECTS: list[dict[str, Any]] = [
    {
        "subject_id": "subj_eval_001_slim_petite_155",
        "label": "Eval-01: Slim Petite Female (155cm, r=0.275)",
        "split": "evaluation", "sex": "female", "body_size_tier": "petite_slim", "torso_ratio_group": "short_torso",
        "height_cm": 155.0, "r_torso": 0.275,
        "chest_w_cm": 26.2, "chest_d_cm": 18.4, "waist_w_cm": 21.2, "waist_d_cm": 15.4, "hip_w_cm": 29.8, "hip_d_cm": 20.4,
        "shoulder_ratio": 0.218, "acromion_offset_cm": 2.8,
    },
    {
        "subject_id": "subj_eval_002_standard_female_163",
        "label": "Eval-02: Standard Female (163cm, r=0.290)",
        "split": "evaluation", "sex": "female", "body_size_tier": "standard_athletic", "torso_ratio_group": "medium_torso",
        "height_cm": 163.0, "r_torso": 0.290,
        "chest_w_cm": 29.0, "chest_d_cm": 21.0, "waist_w_cm": 23.5, "waist_d_cm": 17.5, "hip_w_cm": 32.5, "hip_d_cm": 22.5,
        "shoulder_ratio": 0.230, "acromion_offset_cm": 3.0,
    },
    {
        "subject_id": "subj_eval_003_pear_lower_165",
        "label": "Eval-03: Pear Lower-Body (165cm, r=0.280)",
        "split": "evaluation", "sex": "female", "body_size_tier": "standard_athletic", "torso_ratio_group": "short_torso",
        "height_cm": 165.0, "r_torso": 0.280,
        "chest_w_cm": 28.0, "chest_d_cm": 20.0, "waist_w_cm": 23.0, "waist_d_cm": 17.0, "hip_w_cm": 35.5, "hip_d_cm": 25.0,
        "shoulder_ratio": 0.220, "acromion_offset_cm": 3.0,
    },
    {
        "subject_id": "subj_eval_004_hourglass_168",
        "label": "Eval-04: Hourglass Female (168cm, r=0.285)",
        "split": "evaluation", "sex": "female", "body_size_tier": "standard_athletic", "torso_ratio_group": "medium_torso",
        "height_cm": 168.0, "r_torso": 0.285,
        "chest_w_cm": 31.0, "chest_d_cm": 22.5, "waist_w_cm": 22.8, "waist_d_cm": 16.8, "hip_w_cm": 34.8, "hip_d_cm": 24.2,
        "shoulder_ratio": 0.228, "acromion_offset_cm": 3.1,
    },
    {
        "subject_id": "subj_eval_005_short_torso_166",
        "label": "Eval-05: Short-Torso Archetype (166cm, r=0.260)",
        "split": "evaluation", "sex": "female", "body_size_tier": "petite_slim", "torso_ratio_group": "short_torso",
        "height_cm": 166.0, "r_torso": 0.260,
        "chest_w_cm": 29.5, "chest_d_cm": 21.2, "waist_w_cm": 24.2, "waist_d_cm": 18.0, "hip_w_cm": 33.2, "hip_d_cm": 23.0,
        "shoulder_ratio": 0.232, "acromion_offset_cm": 3.1,
    },
    {
        "subject_id": "subj_eval_006_compact_male_169",
        "label": "Eval-06: Compact Male (169cm, r=0.295)",
        "split": "evaluation", "sex": "male", "body_size_tier": "petite_slim", "torso_ratio_group": "medium_torso",
        "height_cm": 169.0, "r_torso": 0.295,
        "chest_w_cm": 32.0, "chest_d_cm": 22.5, "waist_w_cm": 26.5, "waist_d_cm": 19.8, "hip_w_cm": 32.2, "hip_d_cm": 22.4,
        "shoulder_ratio": 0.242, "acromion_offset_cm": 3.4,
    },
    {
        "subject_id": "subj_eval_007_athletic_male_175",
        "label": "Eval-07: Athletic Male (175cm, r=0.290)",
        "split": "evaluation", "sex": "male", "body_size_tier": "standard_athletic", "torso_ratio_group": "medium_torso",
        "height_cm": 175.0, "r_torso": 0.290,
        "chest_w_cm": 34.5, "chest_d_cm": 24.0, "waist_w_cm": 27.5, "waist_d_cm": 20.0, "hip_w_cm": 33.0, "hip_d_cm": 23.0,
        "shoulder_ratio": 0.250, "acromion_offset_cm": 3.5,
    },
    {
        "subject_id": "subj_eval_008_long_torso_178",
        "label": "Eval-08: Long-Torso Male (178cm, r=0.320)",
        "split": "evaluation", "sex": "male", "body_size_tier": "standard_athletic", "torso_ratio_group": "long_torso",
        "height_cm": 178.0, "r_torso": 0.320,
        "chest_w_cm": 34.0, "chest_d_cm": 23.8, "waist_w_cm": 28.0, "waist_d_cm": 20.8, "hip_w_cm": 33.8, "hip_d_cm": 23.5,
        "shoulder_ratio": 0.248, "acromion_offset_cm": 3.6,
    },
    {
        "subject_id": "subj_eval_009_broad_male_182",
        "label": "Eval-09: Broad Male (182cm, r=0.305)",
        "split": "evaluation", "sex": "male", "body_size_tier": "broad_plus", "torso_ratio_group": "long_torso",
        "height_cm": 182.0, "r_torso": 0.305,
        "chest_w_cm": 37.0, "chest_d_cm": 26.0, "waist_w_cm": 30.0, "waist_d_cm": 22.5, "hip_w_cm": 35.0, "hip_d_cm": 24.5,
        "shoulder_ratio": 0.260, "acromion_offset_cm": 3.8,
    },
    {
        "subject_id": "subj_eval_010_high_whr_plus_172",
        "label": "Eval-10: High-WHR / Plus (172cm, r=0.300)",
        "split": "evaluation", "sex": "male", "body_size_tier": "broad_plus", "torso_ratio_group": "long_torso",
        "height_cm": 172.0, "r_torso": 0.300,
        "chest_w_cm": 36.5, "chest_d_cm": 27.5, "waist_w_cm": 33.5, "waist_d_cm": 26.5, "hip_w_cm": 37.0, "hip_d_cm": 26.5,
        "shoulder_ratio": 0.240, "acromion_offset_cm": 3.5,
    },
]


def evaluate_calibrated_prediction_intervals_on_synthetic_cohort(
    template_mesh,
    fractions: np.ndarray,
) -> dict[str, Any]:
    """Run full Split Conformal & Asymmetric Quantile Calibration on the disjoint synthetic cohort.

    Strictly separates:
      - D_cal: 12 calibration subjects x 3 capture conditions = 36 calibration scans per mode
      - D_eval: 10 held-out evaluation subjects x 3 capture conditions = 30 evaluation scans per mode
    """
    from benchmark_scan_product_readiness import (
        _build_ground_truth_subject_mesh_and_measurements,
        _rasterize_subject_observations,
        _run_pipeline_on_observations,
    )

    cal_ids = [s["subject_id"] for s in SYNTHETIC_CALIBRATION_SUBJECTS]
    eval_ids = [s["subject_id"] for s in SYNTHETIC_EVALUATION_SUBJECTS]
    disjoint_check = verify_subject_disjoint_split(cal_ids, eval_ids)

    rng = np.random.default_rng(20261014)
    metrics_keys = ("chest_cm", "waist_cm", "hip_cm", "shoulder_width_cm")

    # Precompute 3D ground-truth measurements for all calibration and evaluation subjects
    gt_by_subject: dict[str, dict[str, float]] = {}
    for subj in SYNTHETIC_CALIBRATION_SUBJECTS + SYNTHETIC_EVALUATION_SUBJECTS:
        _, gt_meas = _build_ground_truth_subject_mesh_and_measurements(template_mesh, subj, fractions)
        # Record both joint-center shoulder width (MediaPipe 11-12 target) and ISO Biacromial breadth
        acromion_off = float(subj.get("acromion_offset_cm", 3.2))
        gt_meas["shoulder_joint_gt_cm"] = gt_meas["shoulder_width_cm"]
        gt_meas["shoulder_biacromial_gt_cm"] = round(gt_meas["shoulder_width_cm"] + acromion_off, 2)
        gt_by_subject[subj["subject_id"]] = gt_meas

    # Three realistic capture conditions per subject to reflect real-world jitter, hip drift & light clothing
    capture_conditions = [
        {"cond_id": "baseline_tight_fit", "drift": 0.02, "pad_px": 0.0, "jitter_scale": 0.8},
        {"cond_id": "moderate_pose_jitter", "drift": -0.04, "pad_px": 0.3, "jitter_scale": 1.5},
        {"cond_id": "everyday_light_attire", "drift": 0.04, "pad_px": 0.8, "jitter_scale": 1.2},
    ]

    results_by_mode: dict[str, Any] = {}

    for mode in ("full_body", "upper_body"):
        cal_records: list[dict[str, Any]] = []
        eval_records: list[dict[str, Any]] = []

        for split_name, cohort, target_list in (
            ("calibration", SYNTHETIC_CALIBRATION_SUBJECTS, cal_records),
            ("evaluation", SYNTHETIC_EVALUATION_SUBJECTS, eval_records),
        ):
            for subj in cohort:
                sid = subj["subject_id"]
                h_cm = float(subj["height_cm"])
                gt = gt_by_subject[sid]

                for cond in capture_conditions:
                    jitter = rng.uniform(-cond["jitter_scale"], cond["jitter_scale"], size=(2, 33, 2))
                    obs_f, obs_s = _rasterize_subject_observations(
                        subj,
                        fractions,
                        capture_mode=mode,
                        landmark_jitter_px=jitter,
                        lateral_hip_drift_pct=cond["drift"],
                        clothing_pad_px=cond["pad_px"],
                    )
                    meas, prof = _run_pipeline_on_observations(template_mesh, obs_f, obs_s, h_cm, mode)
                    valid_sizing = filter_valid_sizing_measurements(meas, prof["measurement_details"], mode)

                    target_list.append({
                        "subject_id": sid,
                        "split": split_name,
                        "sex": subj["sex"],
                        "body_size_tier": subj["body_size_tier"],
                        "torso_ratio_group": subj["torso_ratio_group"],
                        "r_torso": subj["r_torso"],
                        "perturbation_condition": cond["cond_id"],
                        "ground_truth_cm": gt,
                        "estimated_cm": {
                            k: (round(float(valid_sizing[k]), 2) if valid_sizing.get(k) is not None else None)
                            for k in metrics_keys
                        },
                    })

        # Fit Calibrated Prediction Intervals on D_cal and evaluate on D_eval
        mode_intervals_and_coverage: dict[str, Any] = {}
        subgroup_breakdowns: dict[str, Any] = {
            "by_torso_ratio_group": {},
            "by_body_size_tier": {},
            "by_sex": {},
            "by_perturbation_condition": {},
        }

        cal_params_by_metric: dict[str, Any] = {}
        for k in metrics_keys:
            cal_valid = [
                r for r in cal_records
                if r["estimated_cm"].get(k) is not None and r["ground_truth_cm"].get(k) is not None
            ]
            if not cal_valid:
                mode_intervals_and_coverage[k] = {
                    "status": "BLOCKED_IN_MODE",
                    "coverage_for_sizing_pct": 0.0,
                    "note": "hip_cm is locked to None in upper_body mode.",
                }
                continue

            cal_gt_arr = [float(r["ground_truth_cm"][k]) for r in cal_valid]
            cal_pred_arr = [float(r["estimated_cm"][k]) for r in cal_valid]
            cal_params = compute_calibrated_interval_parameters(cal_gt_arr, cal_pred_arr, alphas=(0.10, 0.05))
            cal_params_by_metric[k] = cal_params

            eval_summary = evaluate_intervals_on_records(eval_records, cal_params, k)
            mode_intervals_and_coverage[k] = {
                "calibration_parameters": cal_params,
                "held_out_evaluation": eval_summary,
            }

            # Also evaluate shoulder_width_cm against ISO Biacromial Ground-Truth to quantify Landmark 11-12 Offset Bias
            if k == "shoulder_width_cm":
                cal_biacromial_gt = [float(r["ground_truth_cm"]["shoulder_biacromial_gt_cm"]) for r in cal_valid]
                cal_biacromial_params = compute_calibrated_interval_parameters(
                    cal_biacromial_gt, cal_pred_arr, alphas=(0.10, 0.05)
                )
                eval_biacromial_recs = [
                    {
                        **r,
                        "ground_truth_cm": {
                            **r["ground_truth_cm"],
                            "shoulder_width_cm": r["ground_truth_cm"]["shoulder_biacromial_gt_cm"],
                        },
                    }
                    for r in eval_records
                ]
                eval_biacromial_summary = evaluate_intervals_on_records(
                    eval_biacromial_recs, cal_biacromial_params, "shoulder_width_cm"
                )
                mode_intervals_and_coverage["shoulder_width_cm"]["iso_biacromial_landmark_offset_analysis"] = {
                    "description": (
                        "Đối chiếu khoảng cách MediaPipe Landmarks 11-12 (tâm khớp vai 2D) với "
                        "Biacromial Breadth (mỏm cùng vai Acromion theo ISO 7250-1 Clause 6.2.1)."
                    ),
                    "mean_landmark_offset_bias_cm": round(
                        float(cal_biacromial_params["calibration_bias_correction_cm"]), 2
                    ),
                    "uncalibrated_mae_vs_biacromial_cm": eval_biacromial_summary["raw_mae_cm"],
                    "bias_corrected_mae_vs_biacromial_cm": eval_biacromial_summary["bias_corrected_mae_cm"],
                    "conformal_90_coverage_after_offset_correction_pct": (
                        eval_biacromial_summary["calibrated_intervals"]["ci_90"]["split_conformal_bias_corrected"]["empirical_coverage_pct"]
                    ),
                    "conformal_90_half_width_cm": (
                        eval_biacromial_summary["calibrated_intervals"]["ci_90"]["split_conformal_bias_corrected"]["half_width_cm"]
                    ),
                }

        # Compute Subgroup Breakdowns on Held-Out Evaluation Set D_eval
        subgroup_axes = [
            ("by_torso_ratio_group", "torso_ratio_group", ("short_torso", "medium_torso", "long_torso")),
            ("by_body_size_tier", "body_size_tier", ("petite_slim", "standard_athletic", "broad_plus")),
            ("by_sex", "sex", ("female", "male")),
            (
                "by_perturbation_condition",
                "perturbation_condition",
                ("baseline_tight_fit", "moderate_pose_jitter", "everyday_light_attire"),
            ),
        ]

        for dict_key, field_name, group_values in subgroup_axes:
            for g_val in group_values:
                sub_recs = [r for r in eval_records if r.get(field_name) == g_val]
                sub_metrics: dict[str, Any] = {}
                for k in metrics_keys:
                    if k not in cal_params_by_metric:
                        sub_metrics[k] = {"status": "BLOCKED_IN_MODE"}
                        continue
                    ev = evaluate_intervals_on_records(sub_recs, cal_params_by_metric[k], k)
                    if ev.get("n_eval_samples", 0) > 0:
                        ci90_sym = ev["calibrated_intervals"]["ci_90"]["split_conformal_bias_corrected"]
                        ci95_sym = ev["calibrated_intervals"]["ci_95"]["split_conformal_bias_corrected"]
                        ci90_asym = ev["calibrated_intervals"]["ci_90"]["asymmetric_empirical_quantile"]
                        sub_metrics[k] = {
                            "n_eval_samples": ev["n_eval_samples"],
                            "raw_mae_cm": ev["raw_mae_cm"],
                            "bias_corrected_mae_cm": ev["bias_corrected_mae_cm"],
                            "raw_signed_bias_cm": ev["raw_signed_bias_cm"],
                            "conformal_90_coverage_pct": ci90_sym["empirical_coverage_pct"],
                            "conformal_90_width_cm": ci90_sym["mean_interval_width_cm"],
                            "conformal_95_coverage_pct": ci95_sym["empirical_coverage_pct"],
                            "conformal_95_width_cm": ci95_sym["mean_interval_width_cm"],
                            "asymmetric_90_coverage_pct": ci90_asym["empirical_coverage_pct"],
                            "asymmetric_90_width_cm": ci90_asym["mean_interval_width_cm"],
                        }
                subgroup_breakdowns[dict_key][g_val] = {
                    "n_eval_records": len(sub_recs),
                    "metrics": sub_metrics,
                }

        results_by_mode[mode] = {
            "calibration_subjects_count": len(SYNTHETIC_CALIBRATION_SUBJECTS),
            "calibration_records_count": len(cal_records),
            "evaluation_subjects_count": len(SYNTHETIC_EVALUATION_SUBJECTS),
            "evaluation_records_count": len(eval_records),
            "metrics": mode_intervals_and_coverage,
            "subgroup_breakdown": subgroup_breakdowns,
        }

    # Verify TEM Calculator on a synthetic 2-measurer x 2-trial ground-truth audit table
    tem_demo_rng = np.random.default_rng(20261015)
    true_chests = np.array([gt_by_subject[s["subject_id"]]["chest_cm"] for s in SYNTHETIC_EVALUATION_SUBJECTS])
    tem_verification = compute_anthropometric_tem(
        true_chests + tem_demo_rng.normal(0.0, 0.18, size=len(true_chests)),
        true_chests + tem_demo_rng.normal(0.0, 0.18, size=len(true_chests)),
        true_chests + tem_demo_rng.normal(0.05, 0.22, size=len(true_chests)),
        true_chests + tem_demo_rng.normal(0.05, 0.22, size=len(true_chests)),
    )

    return {
        "methodology": "NON_PARAMETRIC_SPLIT_CONFORMAL_AND_EMPIRICAL_QUANTILE_INTERVALS",
        "deprecated_parametric_formula_removed": "±1.96 * RMSE (Removed due to non-Gaussian clothing skew & heteroscedasticity)",
        "subject_disjoint_split": disjoint_check,
        "tem_gate_verification_test": tem_verification,
        "modes": results_by_mode,
    }


# ==============================================================================
# 6. REAL-HUMAN PILOT DATASET AUDITOR & EVALUATOR
# ==============================================================================

def evaluate_real_human_pilot_cohort(dataset_dir: Path = REAL_HUMAN_DATASET_DIR) -> dict[str, Any]:
    """Audit and evaluate `verification/datasets/real_human_pilot/manifest.json` if present."""
    manifest_path = dataset_dir / "manifest.json"
    if not dataset_dir.is_dir() or not manifest_path.is_file():
        return {
            "REAL_HUMAN_DATASET_STATUS": "MISSING_EMPIRICAL_COHORT",
            "human_accuracy_validation_status": "NOT_ACCEPTED_NO_EMPIRICAL_DATASET",
            "empirical_accuracy_claim_allowed": False,
            "dataset_dir": str(dataset_dir),
            "manifest_path": str(manifest_path),
            "manifest_exists": False,
            "consented_subjects_total": 0,
            "calibration_subjects_count": 0,
            "evaluation_subjects_count": 0,
            "conclusion": (
                "CHƯA THỂ NGHIỆM THU ĐỘ CHÍNH XÁC TRÊN NGƯỜI THẬT "
                "(Human accuracy cannot be accepted yet because no consented real-human dataset is present)."
            ),
            "required_next_steps": [
                "Thu thập tối thiểu N >= 35 tình nguyện viên có ký Informed Consent (N_cal >= 15, N_eval >= 20 tách biệt theo subject_id) theo docs/ANTHROPOMETRIC_VALIDATION_PROTOCOL.md.",
                "Đo thước dây lặp 2 người đo x 2 lần đạt TEM_intra <= 0.4 cm, TEM_inter <= 0.6 cm; ghi nhận cả Biacromial Breadth và Joint-Center Breadth cho vai.",
                "Đặt manifest.json và ảnh chụp vào verification/datasets/real_human_pilot/ và chạy lại script này để xuất Empirical Coverage & Interval Width trên người thật.",
            ],
        }

    # If manifest.json exists, perform full consent, TEM, disjointness, and conformal evaluation
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    subjects = manifest.get("subjects", [])
    unconsented = [s.get("subject_id", "UNKNOWN") for s in subjects if s.get("informed_consent_signed") is not True]
    if unconsented:
        raise ValueError(f"Отсутствует Informed Consent (informed_consent_signed != True) cho các subject: {unconsented}")

    cal_subjects = [s for s in subjects if s.get("split") == "calibration"]
    eval_subjects = [s for s in subjects if s.get("split") == "evaluation"]
    split_check = verify_subject_disjoint_split(
        [s["subject_id"] for s in cal_subjects],
        [s["subject_id"] for s in eval_subjects],
    )

    intra_tem = manifest.get("intra_tem_cm", {})
    inter_tem = manifest.get("inter_tem_cm", {})
    tem_passed = all(float(v) <= 0.40 for v in intra_tem.values()) and all(float(v) <= 0.60 for v in inter_tem.values())

    # Evaluate images if present
    metrics_keys = ("chest_cm", "waist_cm", "hip_cm", "shoulder_width_cm")
    empirical_modes: dict[str, Any] = {}
    for mode in ("full_body", "upper_body"):
        cal_recs, eval_recs = [], []
        for split_label, subj_list, target_recs in (
            ("calibration", cal_subjects, cal_recs),
            ("evaluation", eval_subjects, eval_recs),
        ):
            for s in subj_list:
                cap = s.get("captures", {}).get(mode)
                if not cap:
                    continue
                f_path = dataset_dir / cap["front"]
                s_path = dataset_dir / cap["side"]
                if not (f_path.is_file() and s_path.is_file()):
                    continue
                f_img = np.array(Image.open(f_path).convert("RGB"))
                s_img = np.array(Image.open(s_path).convert("RGB"))
                gt = s["ground_truth_cm"]
                _, meas, prof = reconstruct(
                    f_img, s_img, float(gt["height_cm"]), CACHE_DIR / f"pilot-{s['subject_id']}-{mode}.glb", lambda _: None, mode
                )
                valid_m = filter_valid_sizing_measurements(meas, prof["measurement_details"], mode)
                target_recs.append({
                    "subject_id": s["subject_id"],
                    "split": split_label,
                    "sex": s.get("sex", "unknown"),
                    "body_size_tier": s.get("body_size_tier", "unknown"),
                    "torso_ratio_group": s.get("torso_ratio_group", "unknown"),
                    "perturbation_condition": s.get("attire", "tight_activewear"),
                    "ground_truth_cm": gt,
                    "estimated_cm": valid_m,
                })

        mode_res: dict[str, Any] = {}
        for k in metrics_keys:
            c_val = [r for r in cal_recs if r["estimated_cm"].get(k) is not None and r["ground_truth_cm"].get(k) is not None]
            if not c_val:
                mode_res[k] = {"status": "INSUFFICIENT_OR_BLOCKED"}
                continue
            c_params = compute_calibrated_interval_parameters(
                [float(r["ground_truth_cm"][k]) for r in c_val],
                [float(r["estimated_cm"][k]) for r in c_val],
            )
            mode_res[k] = {
                "calibration_parameters": c_params,
                "held_out_evaluation": evaluate_intervals_on_records(eval_recs, c_params, k),
            }
        empirical_modes[mode] = mode_res

    enough_subjects = len(cal_subjects) >= 15 and len(eval_subjects) >= 20 and tem_passed
    return {
        "REAL_HUMAN_DATASET_STATUS": "EMPIRICAL_COHORT_EVALUATED" if enough_subjects else "PILOT_COHORT_UNDER_MINIMUM_SAMPLE_SIZE",
        "human_accuracy_validation_status": "EVALUATED_SEE_METRICS" if enough_subjects else "NOT_ACCEPTED_INSUFFICIENT_SAMPLE_OR_TEM",
        "empirical_accuracy_claim_allowed": bool(enough_subjects),
        "split_verification": split_check,
        "tem_passed": tem_passed,
        "modes": empirical_modes,
        "conclusion": (
            "ĐÃ ĐÁNH GIÁ TRÊN TẬP NGƯỜI THẬT ĐỘC LẬP."
            if enough_subjects
            else "CHƯA ĐỦ ĐIỀU KIỆN NGHIỆM THU (Cần N_cal >= 15, N_eval >= 20 và đạt chuẩn TEM)."
        ),
    }


def main() -> None:
    print("=" * 120)
    print(f"MORPH AI — ANTHROPOMETRIC VALIDATION & STATISTICAL CALIBRATION HARNESS ({ENGINE})")
    print("=" * 120)

    template_mesh = read_template()
    fractions = np.linspace(0.12, 1.12, 35)

    # 1. Audit Real-Human Dataset Status
    human_eval = evaluate_real_human_pilot_cohort(REAL_HUMAN_DATASET_DIR)
    print("\n[1] TRẠNG THÁI DỮ LIỆU NGƯỜI THẬT & PHÁN QUYẾT NGHIỆM THU NHÂN TRẮC HỌC")
    print("-" * 120)
    print(f"  • REAL_HUMAN_DATASET_STATUS        : {human_eval['REAL_HUMAN_DATASET_STATUS']}")
    print(f"  • human_accuracy_validation_status : {human_eval['human_accuracy_validation_status']}")
    print(f"  • empirical_accuracy_claim_allowed : {human_eval['empirical_accuracy_claim_allowed']}")
    print(f"  • KẾT LUẬN BẮT BUỘC                : {human_eval['conclusion']}")

    # 2. Verify Calibrated Prediction Intervals & Subgroup Breakdown on Synthetic Disjoint Cohort
    print("\n" + "=" * 120)
    print("[2] KIỂM CHỨNG KHOẢNG DỰ ĐOÁN HIỆU CHUẨN (SPLIT CONFORMAL & ASYMMETRIC QUANTILES) TRÊN TẬP HÌNH HỌC ĐỘC LẬP")
    print("    (Thay thế hoàn toàn ±1.96*RMSE | N_cal = 12 subjects [36 scans] vs N_eval = 10 held-out subjects [30 scans])")
    print("=" * 120)
    conformal_eval = evaluate_calibrated_prediction_intervals_on_synthetic_cohort(template_mesh, fractions)

    print(
        f"{'Mode':<11} | {'Metric':<17} | {'Raw MAE':<8} | {'BC MAE':<8} | {'Cal Bias':<9} | "
        f"{'90% Conf Width':<15} | {'90% Emp Cov':<12} | {'95% Conf Width':<15} | {'95% Emp Cov'}"
    )
    print("-" * 120)
    for mode in ("full_body", "upper_body"):
        for k, m_data in conformal_eval["modes"][mode]["metrics"].items():
            if m_data.get("status") == "BLOCKED_IN_MODE":
                print(
                    f"{mode:<11} | {k:<17} | {'BLOCKED':<8} | {'BLOCKED':<8} | {'N/A':<9} | "
                    f"{'N/A (None)':<15} | {'0.0% (Locked)':<12} | {'N/A (None)':<15} | {'0.0% (Locked)'}"
                )
                continue
            cal_p = m_data["calibration_parameters"]
            ev_p = m_data["held_out_evaluation"]
            ci90 = ev_p["calibrated_intervals"]["ci_90"]["split_conformal_bias_corrected"]
            ci95 = ev_p["calibrated_intervals"]["ci_95"]["split_conformal_bias_corrected"]
            print(
                f"{mode:<11} | {k:<17} | {ev_p['raw_mae_cm']:>5.2f} cm | {ev_p['bias_corrected_mae_cm']:>5.2f} cm | "
                f"{cal_p['calibration_bias_correction_cm']:>+6.2f} cm | "
                f"±{ci90['half_width_cm']:>4.2f} ({ci90['mean_interval_width_cm']:>4.2f}cm) | "
                f"{ci90['empirical_coverage_pct']:>9.1f}%   | "
                f"±{ci95['half_width_cm']:>4.2f} ({ci95['mean_interval_width_cm']:>4.2f}cm) | "
                f"{ci95['empirical_coverage_pct']:>9.1f}%"
            )

    # Print Shoulder Landmark Offset Analysis
    sh_offset = conformal_eval["modes"]["full_body"]["metrics"]["shoulder_width_cm"]["iso_biacromial_landmark_offset_analysis"]
    print("-" * 120)
    print(
        f"  • Phân tích Độ chệch mốc Vai (MediaPipe 11-12 vs ISO 7250-1 Biacromial Acromion): "
        f"Offset trung bình = {sh_offset['mean_landmark_offset_bias_cm']:+.2f} cm | "
        f"MAE chưa bù mốc = {sh_offset['uncalibrated_mae_vs_biacromial_cm']:.2f} cm -> "
        f"MAE sau bù mốc Conformal = {sh_offset['bias_corrected_mae_vs_biacromial_cm']:.2f} cm "
        f"(Độ phủ 90% = {sh_offset['conformal_90_coverage_after_offset_correction_pct']:.1f}%, ±{sh_offset['conformal_90_half_width_cm']:.2f} cm)"
    )

    # 3. Print Subgroup Breakdown for Full-Body and Upper-Body
    print("\n" + "=" * 120)
    print("[3] PHÂN TÍCH ĐỘ PHỦ THỰC NGHIỆM (EMPIRICAL COVERAGE) & ĐỘ RỘNG KHOẢNG DỰ ĐOÁN THEO PHÂN NHÓM (SUBGROUP BREAKDOWN)")
    print("=" * 120)
    for mode in ("full_body", "upper_body"):
        print(f"\n  >>> Chế độ `{mode}` (Held-Out Evaluation Set):")
        sub_bd = conformal_eval["modes"][mode]["subgroup_breakdown"]
        for axis_name, groups in sub_bd.items():
            print(f"    [{axis_name}]")
            for g_name, g_info in groups.items():
                chest_m = g_info["metrics"].get("chest_cm", {})
                waist_m = g_info["metrics"].get("waist_cm", {})
                hip_m = g_info["metrics"].get("hip_cm", {})
                hip_str = (
                    f"Hip MAE={hip_m['bias_corrected_mae_cm']:.2f}cm (Cov90={hip_m['conformal_90_coverage_pct']:.1f}%, W={hip_m['conformal_90_width_cm']:.2f}cm)"
                    if "bias_corrected_mae_cm" in hip_m
                    else "Hip=BLOCKED(None)"
                )
                print(
                    f"      - {g_name:<24} (n={g_info['n_eval_records']:>2}): "
                    f"Chest MAE={chest_m['bias_corrected_mae_cm']:.2f}cm (Cov90={chest_m['conformal_90_coverage_pct']:.1f}%, W={chest_m['conformal_90_width_cm']:.2f}cm) | "
                    f"Waist MAE={waist_m['bias_corrected_mae_cm']:.2f}cm (Cov90={waist_m['conformal_90_coverage_pct']:.1f}%, W={waist_m['conformal_90_width_cm']:.2f}cm) | "
                    f"{hip_str}"
                )

    report_payload = {
        "report_type": "MORPH_AI_ANTHROPOMETRIC_VALIDATION_AND_CONFORMAL_CALIBRATION_REPORT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "engine_version": ENGINE,
        "REAL_HUMAN_DATASET_STATUS": human_eval["REAL_HUMAN_DATASET_STATUS"],
        "human_accuracy_validation_status": human_eval["human_accuracy_validation_status"],
        "empirical_accuracy_claim_allowed": human_eval["empirical_accuracy_claim_allowed"],
        "conclusion": human_eval["conclusion"],
        "iso_vs_algorithm_measurement_crosswalk": ISO_VS_ALGORITHM_MEASUREMENT_MAPPING,
        "proposed_pilot_target_thresholds": PROPOSED_PILOT_TARGET_THRESHOLDS,
        "real_human_pilot_evaluation": human_eval,
        "synthetic_disjoint_conformal_calibration_verification": conformal_eval,
    }

    for out_path in (CACHE_REPORT_PATH, RUN_VALIDATION_REPORT_PATH):
        out_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 120)
    print(f"ĐÃ LƯU BÁO CÁO KIỂM ĐỊNH NHÂN TRẮC & CONFORMAL TẠI:\n  1. {RUN_VALIDATION_REPORT_PATH}\n  2. {CACHE_REPORT_PATH}")
    print("=" * 120)


if __name__ == "__main__":
    main()
