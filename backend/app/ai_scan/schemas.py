"""Pydantic contracts for the experimental AI scan mode."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CaptureMode = Literal["upper_body", "full_body"]


class VisionMeasurementEstimate(BaseModel):
    """Structured output requested from the vision model.

    Every field is optional on purpose: the model must be able to say "I cannot
    see this region" instead of inventing a number.
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


class AiMeasurementDetail(BaseModel):
    key: str
    label: str
    value_cm: float | None
    source: Literal["ai_vision_estimate"] = "ai_vision_estimate"


class AiScanResponse(BaseModel):
    status: Literal["completed"] = "completed"
    provider: Literal["google-genai"] = "google-genai"
    model: str
    capture_mode: CaptureMode
    measurements: AiMeasurementValues
    details: list[AiMeasurementDetail]
    confidence: float = Field(ge=0.0, le=1.0)
    pose_quality: str
    notes: str = ""
    warnings: list[str] = Field(default_factory=list)
    elapsed_seconds: float
    source: Literal["ai_vision_estimate"] = "ai_vision_estimate"
