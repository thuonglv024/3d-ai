"""Pydantic contracts for the experimental AI scan mode."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CaptureMode = Literal["upper_body", "full_body"]
Sex = Literal["auto", "female", "male"]
ClothingFit = Literal["fitted", "regular", "loose", "unknown"]


class VisionMeasurementEstimate(BaseModel):
    """Structured output requested from the vision model.

    Every measurement field is optional on purpose: the model must be able to
    say "I cannot see this region" instead of inventing a number.
    """

    chest_cm: float | None = Field(
        default=None,
        description="Estimated chest/bust circumference in centimetres, or null if not visible.",
    )
    waist_cm: float | None = Field(
        default=None,
        description="Estimated natural waist circumference in centimetres, or null if not visible.",
    )
    hip_cm: float | None = Field(
        default=None,
        description="Estimated hip circumference in centimetres, or null if not visible.",
    )
    shoulder_width_cm: float | None = Field(
        default=None,
        description="Estimated biacromial shoulder width in centimetres, or null if not visible.",
    )
    chest_width_cm: float | None = Field(
        default=None,
        description="Frontal side-to-side breadth of the chest at the chest level, or null.",
    )
    chest_depth_cm: float | None = Field(
        default=None,
        description="Front-to-back depth of the chest at the chest level, or null.",
    )
    waist_width_cm: float | None = Field(
        default=None,
        description="Frontal breadth of the natural waist, or null.",
    )
    waist_depth_cm: float | None = Field(
        default=None,
        description="Front-to-back depth of the natural waist, or null.",
    )
    hip_width_cm: float | None = Field(
        default=None,
        description="Frontal breadth of the hips, or null (always null in upper_body mode).",
    )
    hip_depth_cm: float | None = Field(
        default=None,
        description="Front-to-back depth of the hips, or null (always null in upper_body mode).",
    )
    metric_confidence: dict[str, float] = Field(
        default_factory=dict,
        description="Per-metric confidence 0..1, keyed by the *_cm fields above. "
        "An absent key means the model had no basis to rate that metric.",
    )
    clothing_fit: ClothingFit = Field(
        default="unknown",
        description="How closely the clothing hugs the body, which drives the fabric offset.",
    )
    head_length_cm: float | None = Field(
        default=None,
        description="Estimated head length (chin to crown) in cm, used as the head-unit scale anchor.",
    )
    shape_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the width/depth shape estimates (separate from circumferences).",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the estimates, based on pose, lighting and landmark visibility.",
    )
    pose_quality: Literal["good", "fair", "poor"] = Field(
        default="fair",
        description="Visible posture quality for body measurement.",
    )
    image_quality: str = Field(
        default="",
        description="Short note about lighting, blur, framing or clothing that affected the estimate.",
    )
    notes: str = Field(
        default="",
        description="Brief explanation of how the estimates were derived.",
    )


class AiMeasurementValues(BaseModel):
    height_cm: float
    chest_cm: float | None = None
    waist_cm: float | None = None
    hip_cm: float | None = None
    shoulder_width_cm: float | None = None
    chest_width_cm: float | None = None
    chest_depth_cm: float | None = None
    waist_width_cm: float | None = None
    waist_depth_cm: float | None = None
    hip_width_cm: float | None = None
    hip_depth_cm: float | None = None


class AiMeasurementDetail(BaseModel):
    key: str
    label: str
    value_cm: float | None
    source: Literal["ai_vision_estimate"] = "ai_vision_estimate"
    confidence: float | None = None
    support: int | None = None
    estimated_by: str | None = None


class EnsembleMemberSummary(BaseModel):
    role: str
    label: str
    confidence: float | None = None
    supported_metrics: int = 0
    error: str | None = None


class EnsembleSummary(BaseModel):
    size: int
    members: list[EnsembleMemberSummary] = Field(default_factory=list)
    geometric_available: bool = False


class GeometricCheck(BaseModel):
    """MediaPipe geometric estimate run on the same two photos."""

    available: bool = False
    reason: str = ""
    measurements: dict[str, float | None] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class AiScanResponse(BaseModel):
    status: Literal["completed"] = "completed"
    provider: Literal["google-genai"] = "google-genai"
    model: str
    capture_mode: CaptureMode
    sex: Sex = "auto"
    measurements: AiMeasurementValues
    details: list[AiMeasurementDetail]
    confidence: float = Field(ge=0.0, le=1.0)
    shape_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    pose_quality: str
    notes: str = ""
    warnings: list[str] = Field(default_factory=list)
    elapsed_seconds: float
    source: Literal["ai_vision_estimate"] = "ai_vision_estimate"
    ensemble: EnsembleSummary | None = None
    geometric_check: GeometricCheck | None = None
