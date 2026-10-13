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
    measurements = measurements or {}
    dimensions = [
        key for key in ("chest_cm", "waist_cm", "hip_cm")
        if any(getattr(row, key) is not None for row in chart.rows)
    ]

    missing = [k for k in dimensions if measurements.get(k) is None]

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
                val = measurements.get(key)
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
