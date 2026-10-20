"""Gemini + LangGraph execution for the experimental AI scan."""

from __future__ import annotations

import base64
import time

from .config import configured_model, google_api_key, is_configured
from .graph import CORE_METRICS, build_graph
from .schemas import AiScanResponse


class AiScanNotConfigured(RuntimeError):
    """The model API key is missing."""


class AiScanUnavailable(RuntimeError):
    """The model ran but could not support any measurement."""


async def run_ai_scan(
    front_bytes: bytes,
    side_bytes: bytes,
    height_cm: float,
    capture_mode: str,
    front_mime: str = "image/jpeg",
    side_mime: str = "image/jpeg",
) -> dict:
    if not is_configured():
        raise AiScanNotConfigured(
            "Chưa cấu hình GOOGLE_API_KEY (hoặc GEMINI_API_KEY) cho mode quét AI."
        )

    # Imported lazily so the existing 3D scan keeps working if the optional AI
    # dependencies have not been installed.
    from langchain_google_genai import ChatGoogleGenerativeAI

    model_name = configured_model()
    model = ChatGoogleGenerativeAI(
        model=model_name,
        api_key=google_api_key(),
        temperature=0,
        max_retries=1,
    )
    graph = build_graph(model, model_name)
    started = time.perf_counter()

    state = await graph.ainvoke(
        {
            "front_data_url": _data_url(front_bytes, front_mime),
            "side_data_url": _data_url(side_bytes, side_mime),
            "height_cm": float(height_cm),
            "capture_mode": capture_mode,
            "model_name": model_name,
        }
    )

    values = state.get("values") or {}
    if not any(values.get(key) is not None for key in CORE_METRICS):
        raise AiScanUnavailable(
            "AI không ước lượng được số đo nào từ hai ảnh. "
            "Hãy chụp lại với ánh sáng tốt hơn, đủ thân trên và giữ tư thế thẳng."
        )

    result = dict(state.get("result") or {})
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return AiScanResponse.model_validate(result).model_dump()


def _data_url(data: bytes, mime: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"
