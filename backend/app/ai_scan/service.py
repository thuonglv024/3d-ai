"""Gemini + LangGraph execution for the experimental AI scan.

One model call per scan (``MORPH_AI_ENSEMBLE`` can raise it to 5) at
temperature 0, so a scan costs one request and repeating it does not change the
number. The MediaPipe geometric estimator runs concurrently on the same two
photos as a cross-check, not as a second opinion to average with: it comes from
the same photos and clothing, so their errors are correlated, and its numbers
are only adopted for a metric the model left empty.

Neither route is calibrated against tape measurements, so the result stays
labelled as a visual estimate.
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


class AiScanQuotaExceeded(AiScanUnavailable):
    """The provider refused the call for quota/rate reasons (HTTP 429)."""


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
        max_retries=0,
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
    # Geometry fills in any metric the model missed, which is fine as a
    # cross-check. What is not fine is every number coming from MediaPipe while
    # the response still claims to be an AI measurement: a failed model call
    # must surface as an error, not as a confident-looking result.
    if not ai_supported(state):
        errors = [str(m.get("error") or "") for m in (state.get("member_meta") or []) if m.get("error")]
        detail = f" Lỗi model: {errors[0][:140]}" if errors else ""
        quota_hit = any(
            "429" in error or "RESOURCE_EXHAUSTED" in error or "quota" in error.lower() for error in errors
        )
        message = (
            "Không lượt AI nào trả về số đo (model lỗi hoặc hết quota), nên chưa có kết quả AI. "
            "Số đo hình học MediaPipe không được dùng thay cho kết quả AI." + detail
        )
        if quota_hit:
            raise AiScanQuotaExceeded(
                "Hết hạn mức gọi AI của key hiện tại (free tier khoảng 20 lượt/ngày cho mỗi model). "
                "Thử lại sau khi hạn mức đặt lại, đổi key, hoặc dùng chế độ quét 3D (không cần AI)." + detail
            )
        raise AiScanUnavailable(message)

    result = dict(state.get("result") or {})
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return AiScanResponse.model_validate(result).model_dump()


def ai_supported(state: dict) -> bool:
    """True when at least one shown metric came from the model, not from geometry.

    ``estimated_by`` is set per metric by the fusion step: "ensemble",
    "ensemble+geometry", "geometry", "ensemble+prior". Only the geometry-only
    value counts as "no AI estimate".
    """
    estimated_by = state.get("estimated_by") or {}
    values = state.get("values") or {}
    for key, source in estimated_by.items():
        if values.get(key) is None:
            continue
        if source and source != "geometry":
            return True
    return False


def _data_url(data: bytes, mime: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


