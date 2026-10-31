"""Configuration for the experimental Gemini/LangGraph scan mode.

``backend/.env`` is re-read whenever the file changes, so adding or rotating
``GOOGLE_API_KEY`` takes effect on the next request instead of requiring a
backend restart. Real process environment variables always win over the file.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / ".env"

PROVIDER = "google-genai"
DEFAULT_MODEL = "gemini-2.5-flash"
REQUEST_TIMEOUT_SECONDS = 120

_ENV_MTIME: float | None = None
_ENV_LOADED: dict[str, str] = {}


def _parse_env_file() -> dict[str, str]:
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    parsed: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if value[:1] in ("'", '"'):
            end = value.find(value[0], 1)
            value = value[1:end] if end > 0 else value[1:]
        else:
            value = value.split("#", 1)[0].strip()
        if key:
            parsed[key] = value
    return parsed


def _refresh_env() -> None:
    """Reload ``backend/.env`` when its mtime changed (key rotation without restart)."""
    global _ENV_MTIME
    try:
        mtime = ENV_FILE.stat().st_mtime
    except OSError:
        return
    if mtime == _ENV_MTIME:
        return
    _ENV_MTIME = mtime
    for key, value in _parse_env_file().items():
        current = os.environ.get(key)
        # Keep values that were set outside the file (shell/CI), refresh only
        # values that still match what this file loaded previously.
        if current is None or (key in _ENV_LOADED and current == _ENV_LOADED[key]):
            os.environ[key] = value
            _ENV_LOADED[key] = value


def google_api_key() -> str:
    _refresh_env()
    return (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()


def configured_model() -> str:
    _refresh_env()
    return (os.getenv("MORPH_AI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


DEFAULT_TEMPERATURE = 0.0
DEFAULT_ENSEMBLE_SIZE = 1


def temperature() -> float:
    """Sampling temperature for ensemble members (0 disables the ensemble's
    diversity, 1.0 is too noisy for measurements)."""
    _refresh_env()
    try:
        return min(1.0, max(0.0, float((os.getenv("MORPH_AI_TEMPERATURE") or "").strip() or DEFAULT_TEMPERATURE)))
    except ValueError:
        return DEFAULT_TEMPERATURE


def ensemble_size() -> int:
    """Number of concurrent AI members (roles are cut to fit, min 1, max 5)."""
    _refresh_env()
    try:
        return max(1, min(5, int((os.getenv("MORPH_AI_ENSEMBLE") or "").strip() or DEFAULT_ENSEMBLE_SIZE)))
    except ValueError:
        return DEFAULT_ENSEMBLE_SIZE


def is_configured() -> bool:
    return bool(google_api_key())


def configuration_message() -> str:
    _refresh_env()
    if is_configured():
        return f"Sẵn sàng · {PROVIDER} · {configured_model()}"
    location = "backend/.env" if ENV_FILE.is_file() else "biến môi trường"
    return (
        f"Chưa cấu hình GOOGLE_API_KEY (hoặc GEMINI_API_KEY). "
        f"Thêm key vào {location} rồi thử lại."
    )



