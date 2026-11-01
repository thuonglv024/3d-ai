"""POST /api/fit/explain: explain, never invent a number or a size."""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.ai_scan import fit_explain
from app.ai_scan.fit_explain import (
    ExplainOutput,
    explain_fit,
    fallback_explanation,
    output_uses_only_input_ease,
)


def test_fallback_uses_only_the_input_ease_numbers():
    text = fallback_explanation("M", {"chest_cm": 1.9, "waist_cm": -1.5})
    assert "M" in text
    assert "1,9" in text and "1,5" in text
    assert "vừa" in text and "hẹp" in text
    assert len(text) <= 300
    assert "rộng" in fallback_explanation("M", {"chest_cm": 2.9})


def test_missing_region_is_stated_not_guessed():
    text = fallback_explanation("L", {"chest_cm": 4.0})
    assert "Eo chưa có số đo áo" in text
    assert "4,0" in text


def test_an_invented_number_is_rejected():
    eases = {"chest_cm": 2.9}
    good = ExplainOutput(explanation="Ngực áo rộng hơn cơ thể 2,9 cm nên vừa.")
    bad = ExplainOutput(explanation="Ngực áo rộng hơn cơ thể 5 cm nên thử size L.")
    assert output_uses_only_input_ease(good, eases) is True
    assert output_uses_only_input_ease(bad, eases) is False


def test_without_a_key_the_answer_is_the_fallback(monkeypatch):
    monkeypatch.setattr(fit_explain, "is_configured", lambda: False)
    fit_explain._CACHE.clear()
    out = asyncio.run(explain_fit("M", {"chest_cm": 2.9, "waist_cm": None}, {"name": "Oricano"}))
    assert out["source"] == "fallback"
    assert out["fallback_reason"] == "not_configured"
    assert out["basis"] == [{"metric": "chest_cm", "ease_cm": 2.9}]


def test_ai_output_with_a_foreign_number_falls_back(monkeypatch):
    monkeypatch.setattr(fit_explain, "is_configured", lambda: True)
    fit_explain._CACHE.clear()

    async def fake_call(size, eases, garment):
        return ExplainOutput(explanation="Ngực áo rộng hơn 5 cm nên thử size L.")

    monkeypatch.setattr(fit_explain, "_call_model", fake_call)
    out = asyncio.run(explain_fit("M", {"chest_cm": 2.9}))
    assert out["source"] == "fallback"
    assert out["fallback_reason"] == "number_mismatch"


def test_ai_success_is_cached_and_uses_the_input_ease(monkeypatch):
    monkeypatch.setattr(fit_explain, "is_configured", lambda: True)
    fit_explain._CACHE.clear()
    calls: list[str] = []

    async def fake_call(size, eases, garment):
        calls.append(size)
        return ExplainOutput(explanation="Ngực áo rộng hơn cơ thể 2,9 cm nên vừa.")

    monkeypatch.setattr(fit_explain, "_call_model", fake_call)
    first = asyncio.run(explain_fit("M", {"chest_cm": 2.9}))
    second = asyncio.run(explain_fit("M", {"chest_cm": 2.9}))
    assert first["source"] == "ai"
    assert second["source"] == "ai"
    assert len(calls) == 1


def test_quota_error_falls_back_without_retry(monkeypatch):
    monkeypatch.setattr(fit_explain, "is_configured", lambda: True)
    fit_explain._CACHE.clear()
    calls: list[str] = []

    async def fake_call(size, eases, garment):
        calls.append(size)
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(fit_explain, "_call_model", fake_call)
    out = asyncio.run(explain_fit("M", {"chest_cm": 2.9}))
    assert out["source"] == "fallback"
    assert out["fallback_reason"] == "quota"
    assert len(calls) == 1


def test_endpoint_returns_200_with_a_fallback(monkeypatch):
    from app.main import app

    monkeypatch.setattr(fit_explain, "is_configured", lambda: False)
    fit_explain._CACHE.clear()
    response = TestClient(app).post(
        "/api/fit/explain",
        json={"size": "M", "eases": {"chest_cm": 2.9}, "garment": {"name": "Oricano", "fit": "body"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["basis"] == [{"metric": "chest_cm", "ease_cm": 2.9}]
    assert "2,9" in body["explanation"]


def test_endpoint_ignores_a_blank_size_without_crashing(monkeypatch):
    from app.main import app

    monkeypatch.setattr(fit_explain, "is_configured", lambda: False)
    response = TestClient(app).post("/api/fit/explain", json={"size": " ", "eases": {"chest_cm": 1.0}})
    # Pydantic accepts a whitespace size; explain_fit must still answer 200.
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
