"""Configuration for the experimental Gemini/LangGraph scan mode."""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

try:  # python-dotenv is optional; environment variables work without it.
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - exercised only without the AI extras
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(BACKEND_ROOT / ".env", override=False)

PROVIDER = "google-genai"
DEFAULT_MODEL = "gemini-2.5-flash"
REQUEST_TIMEOUT_SECONDS = 90


def google_api_key() -> str:
    return (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()


def configured_model() -> str:
    return (os.getenv("MORPH_AI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def is_configured() -> bool:
    return bool(google_api_key())


def configuration_message() -> str:
    if is_configured():
        return f"Sẵn sàng · {PROVIDER} · {configured_model()}"
    return (
        "Chưa cấu hình GOOGLE_API_KEY (hoặc GEMINI_API_KEY). "
        "Thêm key vào backend/.env rồi khởi động lại backend."
    )
