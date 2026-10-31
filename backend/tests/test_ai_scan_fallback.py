"""Hai bản sửa của lớp đọc số đo: bỏ hệ số lõm cứng, và không trả số hình học thay AI.

Bối cảnh (đo trên P01b, tape ngực 80 / eo 60 / hông 92):
- ellipse ngực 83,1 cm (+3,1) rồi nhân hệ số lõm cũ (+8,07%) thành 89,8 cm (+9,8):
  hơn 2/3 sai số ngực là do hằng số, không phải do đường viền.
- khi cả 3 lượt AI lỗi, pipeline cũ vẫn trả `completed` với số của MediaPipe.
"""

from __future__ import annotations

import asyncio

import pytest

from app.ai_scan import service
from app.ai_scan.service import AiScanUnavailable, ai_supported
from app.measurements import ANATOMICAL_SECTION_FACTORS, SECTION_FACTORS_CALIBRATED


def test_section_factors_are_identity_until_calibrated():
    assert SECTION_FACTORS_CALIBRATED is False
    assert ANATOMICAL_SECTION_FACTORS == {"chest_cm": 1.0, "waist_cm": 1.0, "hip_cm": 1.0}


def test_ai_supported_rejects_geometry_only_results():
    state = {
        "values": {"chest_cm": 89.8, "waist_cm": 86.6},
        "estimated_by": {"chest_cm": "geometry", "waist_cm": "geometry"},
    }
    assert ai_supported(state) is False


def test_ai_supported_accepts_any_model_backed_metric():
    assert ai_supported(
        {"values": {"chest_cm": 91.0, "waist_cm": 86.0}, "estimated_by": {"chest_cm": "ensemble", "waist_cm": "geometry"}}
    )
    assert ai_supported(
        {
            "values": {"chest_cm": 91.0},
            "estimated_by": {"chest_cm": "ensemble+geometry"},
        }
    )
    assert ai_supported(
        {"values": {"waist_cm": 72.0}, "estimated_by": {"waist_cm": "ensemble+prior"}}
    )


def test_ai_supported_ignores_metrics_without_a_value():
    state = {"values": {"chest_cm": None}, "estimated_by": {"chest_cm": "ensemble"}}
    assert ai_supported(state) is False


class _FakeGraph:
    def __init__(self, state: dict):
        self._state = state

    async def ainvoke(self, _payload):
        return self._state


def test_run_ai_scan_raises_instead_of_returning_geometry_numbers(monkeypatch):
    state = {
        "values": {"chest_cm": 89.8, "waist_cm": 86.6, "hip_cm": 100.5},
        "estimated_by": {"chest_cm": "geometry", "waist_cm": "geometry", "hip_cm": "geometry"},
        "member_meta": [
            {"role": "anchor", "error": "429 RESOURCE_EXHAUSTED"},
            {"role": "shape", "error": "429 RESOURCE_EXHAUSTED"},
            {"role": "audit", "error": "429 RESOURCE_EXHAUSTED"},
        ],
        "capture_mode": "full_body",
        "sex": "auto",
        "height_cm": 156.0,
        "result": {"status": "completed"},
    }
    monkeypatch.setattr(service, "is_configured", lambda: True)
    monkeypatch.setattr(service, "google_api_key", lambda: "test-key")
    monkeypatch.setattr(service, "configured_model", lambda: "fake-model")
    monkeypatch.setattr(service, "temperature", lambda: 0.0)
    monkeypatch.setattr(service, "build_graph", lambda *args, **kwargs: _FakeGraph(state))

    with pytest.raises(AiScanUnavailable) as error:
        asyncio.run(service.run_ai_scan(b"front", b"side", 156.0, "full_body"))
    message = str(error.value)
    assert "chưa có kết quả AI" in message
    assert "429" in message  # lý do thật được chuyển ra ngoài
