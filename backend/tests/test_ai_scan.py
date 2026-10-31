"""Tests for the experimental AI scan mode.

No network calls are made here: the endpoint tests use a fake service and the
LangGraph test uses a fake structured model.
"""

from __future__ import annotations

import asyncio
import os
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app import main
from app.ai_scan import service
from app.ai_scan.graph import build_graph, validate_estimate
from app.ai_scan.schemas import AiScanResponse, VisionMeasurementEstimate


def photo(color: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (300, 500), color).save(output, format="JPEG")
    return output.getvalue()


def test_ai_health_reports_not_configured(monkeypatch):
    import app.ai_scan.router as ai_router

    monkeypatch.setattr(ai_router, "is_configured", lambda: False)
    monkeypatch.setattr(ai_router, "configuration_message", lambda: "Chưa cấu hình key.")
    with TestClient(main.app) as client:
        body = client.get("/api/ai-scan/health").json()
    assert body["ready"] is False
    assert body["provider"] == "google-genai"
    assert "model" in body


def test_ai_health_reports_configured(monkeypatch):
    import app.ai_scan.router as ai_router

    monkeypatch.setattr(ai_router, "is_configured", lambda: True)
    monkeypatch.setattr(ai_router, "configuration_message", lambda: "Sẵn sàng.")
    with TestClient(main.app) as client:
        body = client.get("/api/ai-scan/health").json()
    assert body["ready"] is True


def test_ai_analyze_requires_consent():
    files = {
        "front": ("front.jpg", photo("white"), "image/jpeg"),
        "side": ("side.jpg", photo("gray"), "image/jpeg"),
    }
    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai-scan/analyze",
            files=files,
            data={"height_cm": 170, "capture_mode": "upper_body"},
        )
    assert response.status_code == 400


def test_ai_analyze_rejects_identical_images():
    front = photo("white")
    files = {
        "front": ("front.jpg", front, "image/jpeg"),
        "side": ("side.jpg", front, "image/jpeg"),
    }
    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai-scan/analyze",
            files=files,
            data={"height_cm": 170, "capture_mode": "upper_body", "consent": True},
        )
    assert response.status_code == 400
    assert "giống nhau" in response.json()["detail"]


def test_ai_analyze_returns_503_when_key_missing(monkeypatch):
    monkeypatch.setattr(service, "is_configured", lambda: False)
    files = {
        "front": ("front.jpg", photo("white"), "image/jpeg"),
        "side": ("side.jpg", photo("gray"), "image/jpeg"),
    }
    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai-scan/analyze",
            files=files,
            data={"height_cm": 170, "capture_mode": "upper_body", "consent": True},
        )
    assert response.status_code == 503


def test_validate_estimate_drops_impossible_values_and_upper_body_hip():
    state = {
        "height_cm": 170.0,
        "capture_mode": "upper_body",
        "estimate": {
            "chest_cm": 95.0,
            "waist_cm": 500.0,
            "hip_cm": 100.0,
            "shoulder_width_cm": 40.0,
            "confidence": 0.9,
            "pose_quality": "good",
            "notes": "test",
        },
    }
    result = validate_estimate(state)
    assert result["values"]["chest_cm"] == 95.0
    assert result["values"]["waist_cm"] is None
    assert result["values"]["hip_cm"] is None
    assert result["confidence"] <= 0.65
    assert any("ngoài khoảng" in warning for warning in result["warnings"])


def test_validate_flags_contradictory_shape_and_clears_upper_body_hip_shape():
    state = {
        "height_cm": 170.0,
        "capture_mode": "upper_body",
        "estimate": {
            "chest_cm": 115.0,
            "chest_width_cm": 30.0,
            "chest_depth_cm": 22.0,
            "waist_cm": 75.0,
            "shoulder_width_cm": 40.0,
            "hip_width_cm": 38.0,
            "hip_depth_cm": 24.0,
            "shape_confidence": 0.7,
            "confidence": 0.9,
            "pose_quality": "good",
        },
    }
    result = validate_estimate(state)
    assert result["values"]["chest_width_cm"] == 30.0
    assert result["values"]["hip_width_cm"] is None
    assert result["values"]["hip_depth_cm"] is None
    assert any("lệch" in warning for warning in result["warnings"])
    assert result["shape_confidence"] == 0.7


def test_langgraph_pipeline_with_fake_model():
    class FakeStructured:
        async def ainvoke(self, _messages):
            return VisionMeasurementEstimate(
                chest_cm=96.0,
                waist_cm=78.0,
                hip_cm=101.0,
                shoulder_width_cm=39.0,
                confidence=0.82,
                pose_quality="good",
                image_quality="good",
                notes="fake estimate",
            )

    class FakeModel:
        def with_structured_output(self, _schema):
            return FakeStructured()

    graph = build_graph(FakeModel(), "fake-model")
    state = asyncio.run(
        graph.ainvoke(
            {
                "front_data_url": "data:image/jpeg;base64,AA==",
                "side_data_url": "data:image/jpeg;base64,AA==",
                "height_cm": 170.0,
                "capture_mode": "full_body",
                "model_name": "fake-model",
            }
        )
    )

    result = state["result"]
    assert result["measurements"]["chest_cm"] == 96.0
    assert result["measurements"]["hip_cm"] == 101.0
    assert result["model"] == "fake-model"
    assert result["source"] == "ai_vision_estimate"
    assert len(result["details"]) == 10


def test_ai_analyze_returns_result_from_service(monkeypatch):
    async def fake_run_ai_scan(*_args, **_kwargs):
        return AiScanResponse(
            model="fake-model",
            capture_mode="upper_body",
            measurements={
                "height_cm": 170,
                "chest_cm": 95,
                "waist_cm": 77,
                "hip_cm": None,
                "shoulder_width_cm": 39,
            },
            details=[
                {"key": "chest_cm", "label": "Vòng ngực", "value_cm": 95},
                {"key": "hip_cm", "label": "Vòng mông", "value_cm": None},
            ],
            confidence=0.7,
            pose_quality="good",
            notes="fake",
            warnings=[],
            elapsed_seconds=0.01,
        ).model_dump()

    monkeypatch.setattr(service, "run_ai_scan", fake_run_ai_scan)
    files = {
        "front": ("front.jpg", photo("white"), "image/jpeg"),
        "side": ("side.jpg", photo("gray"), "image/jpeg"),
    }
    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai-scan/analyze",
            files=files,
            data={"height_cm": 170, "capture_mode": "upper_body", "consent": True},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["measurements"]["chest_cm"] == 95
    assert body["source"] == "ai_vision_estimate"


def _analyze_files():
    return {
        "front": ("front.jpg", photo("white"), "image/jpeg"),
        "side": ("side.jpg", photo("gray"), "image/jpeg"),
    }


def test_ai_analyze_maps_quota_to_429(monkeypatch):
    async def quota(*_args, **_kwargs):
        raise service.AiScanQuotaExceeded(
            "Hết hạn mức gọi AI của key hiện tại (free tier khoảng 20 lượt/ngày cho mỗi model)."
        )

    monkeypatch.setattr(service, "run_ai_scan", quota)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai-scan/analyze",
            files=_analyze_files(),
            data={"height_cm": 170, "capture_mode": "upper_body", "consent": True},
        )
    assert response.status_code == 429
    assert "hạn mức" in response.json()["detail"]


def test_ai_analyze_maps_upstream_failure_to_502(monkeypatch):
    async def unavailable(*_args, **_kwargs):
        raise service.AiScanUnavailable("Không lượt AI nào trả về số đo. Lỗi model: 503 UNAVAILABLE")

    monkeypatch.setattr(service, "run_ai_scan", unavailable)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai-scan/analyze",
            files=_analyze_files(),
            data={"height_cm": 170, "capture_mode": "upper_body", "consent": True},
        )
    assert response.status_code == 502
    assert "503" in response.json()["detail"]


def test_env_file_is_reloaded_without_restart(monkeypatch, tmp_path):
    from app.ai_scan import config as ai_config

    env = tmp_path / ".env"
    env.write_text("GOOGLE_API_KEY=first-key\n", encoding="utf-8")
    monkeypatch.setattr(ai_config, "ENV_FILE", env)
    monkeypatch.setattr(ai_config, "_ENV_MTIME", None)
    monkeypatch.setattr(ai_config, "_ENV_LOADED", {})
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert ai_config.google_api_key() == "first-key"

    env.write_text("GOOGLE_API_KEY=rotated-key\n", encoding="utf-8")
    os.utime(env, (1_700_000_100, 1_700_000_100))
    assert ai_config.google_api_key() == "rotated-key"

    # A real environment variable must win over the file.
    monkeypatch.setenv("GOOGLE_API_KEY", "shell-key")
    assert ai_config.google_api_key() == "shell-key"


def test_invalid_api_key_returns_actionable_503(monkeypatch):
    async def failing(*_args, **_kwargs):
        raise RuntimeError("400 API key not valid. Please pass a valid API key.")

    monkeypatch.setattr(service, "run_ai_scan", failing)
    files = {
        "front": ("front.jpg", photo("white"), "image/jpeg"),
        "side": ("side.jpg", photo("gray"), "image/jpeg"),
    }
    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai-scan/analyze",
            files=files,
            data={"height_cm": 170, "capture_mode": "upper_body", "consent": True},
        )
    assert response.status_code == 503
    assert "không hợp lệ" in response.json()["detail"]
