"""Range matching against an explicitly supplied BODY measurement chart."""
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator


class Range(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min: float = Field(ge=10, le=250, allow_inf_nan=False)
    max: float = Field(ge=10, le=250, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered(self):
        if self.max < self.min:
            raise ValueError("Giới hạn trên cần lớn hơn hoặc bằng giới hạn dưới.")
        return self


class SizeRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    size: str = Field(min_length=1, max_length=20)
    chest_cm: Range | None = None
    waist_cm: Range | None = None
    hip_cm: Range | None = None


class SizeChart(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=100)
    garment: Literal["top", "bottom", "dress", "outerwear"] | str = "top"
    source: Literal["illustrative", "user_provided"] | str = "illustrative"
    measurement_basis: Literal["body_cm"] = "body_cm"
    rows: list[SizeRow] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def dimensions(self):
        if len({r.size.strip() for r in self.rows}) != len(self.rows) or any(not r.size.strip() for r in self.rows):
            raise ValueError("Tên size cần khác nhau và không để trống.")

        garment = (self.garment or "").lower().strip()
        if garment == "bottom":
            required = ("waist_cm", "hip_cm")
            if any(getattr(r, key) is None for r in self.rows for key in required):
                raise ValueError("Quần cần eo/mông. Nhập khoảng số đo cơ thể bằng cm.")
        elif garment == "dress":
            # cần ("chest_cm", "waist_cm") hoặc ("chest_cm", "waist_cm", "hip_cm")
            if any(r.chest_cm is None or r.waist_cm is None for r in self.rows):
                raise ValueError("Váy/đầm cần ngực/eo hoặc ngực/eo/mông. Nhập khoảng số đo cơ thể bằng cm.")
            has_hip = [r.hip_cm is not None for r in self.rows]
            if any(has_hip) and not all(has_hip):
                raise ValueError("Bảng size váy/đầm cần có đủ số đo mông cho tất cả các size nếu có.")
        else:
            # "top", "outerwear", hoặc loại trang phục thân trên khác
            required = ("chest_cm", "waist_cm")
            if any(getattr(r, key) is None for r in self.rows for key in required):
                raise ValueError("Áo/áo khoác cần ngực/eo. Nhập khoảng số đo cơ thể bằng cm.")

        return self


VALID_SIZING_SOURCES = {"photo_estimate", "photo_with_prior", "user_input"}


def filter_valid_sizing_measurements(
    rows_or_dict,
    details: Optional[list[dict]] = None,
    capture_mode: Optional[str] = None,
) -> dict[str, Optional[float]]:
    """
    Filters body measurements so only metrics from VALID_SIZING_SOURCES with positive
    numeric values are kept. Metrics from 'template_model' or 'unavailable', or with
    value_cm is None / <= 0, or hip_cm from an upper_body scan (unless user_input)
    are mapped to None.
    """
    if rows_or_dict is None and not details:
        return {}

    result: dict[str, Optional[float]] = {}

    if isinstance(rows_or_dict, (list, tuple)):
        for r in rows_or_dict:
            r_map = dict(r) if not isinstance(r, dict) else r
            k = r_map.get("metric_key") or r_map.get("key")
            if not k:
                continue
            src = r_map.get("source")
            val = r_map.get("value_cm")
            if src not in VALID_SIZING_SOURCES or val is None or isinstance(val, bool):
                result[k] = None
                continue
            try:
                fval = float(val)
            except (TypeError, ValueError):
                result[k] = None
                continue
            if fval <= 0:
                result[k] = None
                continue
            if capture_mode == "upper_body" and k == "hip_cm" and src != "user_input":
                result[k] = None
                continue
            result[k] = fval
        return result

    raw_dict = rows_or_dict if isinstance(rows_or_dict, dict) else {}
    detail_by_key: dict[str, dict] = {}
    if details and isinstance(details, (list, tuple)):
        for item in details:
            if isinstance(item, dict):
                k = item.get("key") or item.get("metric_key")
                if k:
                    detail_by_key[k] = item

    all_keys = list(dict.fromkeys(list(raw_dict.keys()) + list(detail_by_key.keys())))
    for k in all_keys:
        det = detail_by_key.get(k)
        src = det.get("source") if det else None
        if src is not None and src not in VALID_SIZING_SOURCES:
            result[k] = None
            continue
        val = raw_dict.get(k) if k in raw_dict else (det.get("value_cm") if det else None)
        if val is None or isinstance(val, bool):
            result[k] = None
            continue
        try:
            fval = float(val)
        except (TypeError, ValueError):
            result[k] = None
            continue
        if fval <= 0:
            result[k] = None
            continue
        if capture_mode == "upper_body" and k == "hip_cm" and src != "user_input":
            result[k] = None
            continue
        result[k] = fval

    return result


class SizingRecommendRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product_id: Optional[str] = None
    product_slug: Optional[str] = None
    scan_id: Optional[str] = None
    saved_scan_id: Optional[str] = None
    guest_token: Optional[str] = None
    measurements: Optional[dict[str, Optional[float]]] = None
    chart: Optional[SizeChart] = None


def recommend_size(measurements: Optional[dict], chart: SizeChart):
    raw_measurements = measurements or {}
    clean_measurements: dict[str, Optional[float]] = {}
    for k, v in raw_measurements.items():
        if v is None or isinstance(v, bool):
            clean_measurements[k] = None
        else:
            try:
                fv = float(v)
                clean_measurements[k] = fv if fv > 0 else None
            except (TypeError, ValueError):
                clean_measurements[k] = None

    dimensions = [
        key for key in ("chest_cm", "waist_cm", "hip_cm")
        if any(getattr(row, key) is not None for row in chart.rows)
    ]

    missing = [k for k in dimensions if clean_measurements.get(k) is None]

    labels = {
        "chest_cm": "vòng ngực",
        "waist_cm": "vòng eo",
        "hip_cm": "vòng mông",
    }

    candidates = []
    comparisons = []
    for row in chart.rows:
        checks = {}
        for key in ("chest_cm", "waist_cm", "hip_cm"):
            r_range = getattr(row, key)
            if r_range is not None:
                val = clean_measurements.get(key)
                within = bool(val is not None and r_range.min <= val <= r_range.max)
                checks[key] = {
                    "value_cm": val,
                    "min_cm": r_range.min,
                    "max_cm": r_range.max,
                    "within": within,
                }
        fits = bool(checks and all(c["within"] for c in checks.values()) and not missing)
        if fits:
            candidates.append(row.size)
        comparisons.append({"size": row.size, "fits": fits, "checks": checks})

    warning_text = (
        "Số đo từ ảnh chưa được kiểm chứng; đây là gợi ý tham khảo. "
        "Độ co giãn và độ rộng trang phục chưa được mô phỏng."
    )

    if missing:
        missing_text = ", ".join(labels.get(k, k) for k in missing)
        return {
            "status": "insufficient_measurements",
            "candidates": [],
            "missing": missing,
            "chart_name": chart.name,
            "chart_source": chart.source,
            "comparisons": comparisons,
            "message": f"Chưa đủ dữ liệu để gợi ý (cần số đo {missing_text})",
            "warning": warning_text,
        }

    return {
        "status": "matched" if candidates else "no_match",
        "candidates": candidates,
        "chart_name": chart.name,
        "chart_source": chart.source,
        "comparisons": comparisons,
        "message": (
            "Khớp các khoảng trong bảng đã chọn."
            if candidates
            else "Không size nào khớp tất cả số đo. Không tự chọn size gần nhất."
        ),
        "warning": warning_text,
    }
