"""Gemini + LangGraph execution for the experimental AI scan.

Each request runs a three-member ensemble of the same model with three role
prompts, concurrently with a MediaPipe geometric estimator over the same two
photos. That is four estimates from two inputs, not four independent
measurements: the members share the model, the photos and the clothing, so
their errors are correlated. Median aggregation buys robustness against one
deviant pass, and the geometric estimate buys a second route through the
project's own pixel-to-centimetre pipeline. Neither is calibrated against tape
measurements, so the result stays labelled as a visual estimate.
"""

from __future__ import annotations

import base64
import time

from .config import configured_model, ensemble_size, google_api_key, is_configured, temperature
from .ensemble import MEMBER_ROLES
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
    sex: str = "auto",
) -> dict:
    if not is_configured():
        raise AiScanNotConfigured(
            "Chưa cấu hình GOOGLE_API_KEY (hoặc GEMINI_API_KEY) cho mode quét AI."
        )

    # Imported lazily so the existing 3D scan keeps working if the optional AI
    # dependencies have not been installed.
    from langchain_google_genai import ChatGoogleGenerativeAI

    model_name = configured_model()
    # Temperature above zero gives the members partly independent sampling
    # noise, which is what the median aggregation and the dispersion penalty
    # measure. It does not make them independent estimators: same model, same
    # photos, same clothing.
    model = ChatGoogleGenerativeAI(
        model=model_name,
        api_key=google_api_key(),
        temperature=temperature(),
        max_retries=1,
    )
    graph = build_graph(model, model_name, roles=MEMBER_ROLES[: ensemble_size()])
    started = time.perf_counter()

    state = await graph.ainvoke(
        {
            "front_data_url": _data_url(front_bytes, front_mime),
            "side_data_url": _data_url(side_bytes, side_mime),
            "front_bytes": front_bytes,
            "side_bytes": side_bytes,
            "height_cm": float(height_cm),
            "capture_mode": capture_mode,
            "sex": sex,
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
