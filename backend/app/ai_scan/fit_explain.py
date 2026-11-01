"""Explain a size from the measured ease — never invent or change a size.

The node is deliberately small: one LangGraph node, one model call, hard
post-validation. It receives only what the user is about to see (size, ease per
region, garment notes) and must return an explanation that uses **exactly those
ease numbers**. Any other number, a size change, or an over-long answer is
rejected and replaced with the deterministic fallback.

The fallback is the normal path on a free tier: quota errors, 503s, timeouts and
invalid JSON all end there, with no retry loop.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional, TypedDict

from pydantic import BaseModel, Field

from .config import configured_model, google_api_key, is_configured

logger = logging.getLogger(__name__)

MAX_EXPLANATION_CHARS = 300
AI_TIMEOUT_SECONDS = 15.0
CACHE_LIMIT = 128

REGION_LABEL = {"chest_cm": "Ngực", "waist_cm": "Eo", "hip_cm": "Mông"}


class ExplainBasis(BaseModel):
    metric: str
    ease_cm: float


class ExplainOutput(BaseModel):
    explanation: str = Field(min_length=1, max_length=MAX_EXPLANATION_CHARS)
    basis: list[ExplainBasis] = Field(default_factory=list)


class _ExplainState(TypedDict, total=False):
    output: Any


_CACHE: dict[tuple, dict] = {}


def _clean_eases(eases: dict[str, Optional[float]] | None) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for key in ("chest_cm", "waist_cm", "hip_cm"):
        value = (eases or {}).get(key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number and abs(number) <= 100:
            cleaned[key] = round(number, 1)
    return cleaned


def fallback_explanation(size: str, eases: dict[str, float]) -> str:
    """Deterministic sentence from the ease only; no model involved."""

    def clause(key: str) -> str:
        label = REGION_LABEL.get(key, key)
        ease = eases.get(key)
        if ease is None:
            return f"{label} chưa có số đo áo nên chưa kết luận."
        value = f"{abs(ease):.1f}".replace(".", ",")
        if ease < 0:
            return f"{label} áo hẹp hơn cơ thể {value} cm nên hơi bó."
        if ease <= 2:
            return f"{label} áo rộng hơn cơ thể {value} cm nên vừa."
        return f"{label} áo rộng hơn cơ thể {value} cm nên rộng."

    if not eases:
        return f"Size {size}: chưa có số đo áo cho ngực và eo nên chưa thể giải thích."
    return f"Size {size}: " + " ".join(clause(key) for key in ("chest_cm", "waist_cm"))


def fallback_payload(size: str, eases: dict[str, float], reason: str) -> dict:
    return {
        "size": size,
        "explanation": fallback_explanation(size, eases)[:MAX_EXPLANATION_CHARS],
        "basis": [{"metric": key, "ease_cm": value} for key, value in eases.items()],
        "source": "fallback",
        "fallback_reason": reason,
    }


def _numbers_in(text: str) -> set[float]:
    return {
        round(float(match.replace(",", ".")), 2)
        for match in re.findall(r"\d+(?:[.,]\d+)?", text or "")
    }


def output_uses_only_input_ease(output: ExplainOutput, eases: dict[str, float]) -> bool:
    """Every number in the text must be one of the supplied ease values."""
    allowed = {round(value, 2) for value in eases.values()}
    for number in _numbers_in(output.explanation):
        if not any(abs(number - value) <= 0.05 for value in allowed):
            return False
    return True


def _prompt(size: str, eases: dict[str, float], garment: dict | None) -> list[Any]:
    from langchain_core.messages import HumanMessage, SystemMessage

    lines = [
        "Bạn giải thích vì sao một size áo vừa/chật/rộng cho một người dùng.",
        "QUY TẮC BẮT BUỘC:",
        "- CHỈ giải thích, KHÔNG đề xuất size khác và KHÔNG đổi size.",
        "- KHÔNG tạo số mới. Chỉ được dùng đúng các số ease (cm) được cung cấp.",
        "- Nêu mốc nào rộng/chật và mức bao nhiêu cm; tối đa 300 ký tự.",
        '- Trả JSON: {"explanation": string, "basis": [{"metric": string, "ease_cm": number}]}',
    ]
    data = {
        "size": size,
        "ease_cm": eases,
        "garment": {key: value for key, value in (garment or {}).items() if value is not None},
    }
    return [
        SystemMessage(content="\n".join(lines)),
        HumanMessage(content=json.dumps(data, ensure_ascii=False)),
    ]


def _parse_output(content: Any) -> ExplainOutput:
    text = content if isinstance(content, str) else str(getattr(content, "content", content))
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    payload = json.loads(text)
    return ExplainOutput.model_validate(payload)


async def _call_model(size: str, eases: dict[str, float], garment: dict | None) -> ExplainOutput:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.graph import END, START, StateGraph

    model = ChatGoogleGenerativeAI(
        model=configured_model(),
        api_key=google_api_key(),
        temperature=0.0,
        max_retries=0,
    )

    async def explain_node(state: dict) -> dict:
        response = await model.ainvoke(_prompt(size, eases, garment))
        return {"output": _parse_output(response)}

    workflow = StateGraph(_ExplainState)
    workflow.add_node("explain", explain_node)
    workflow.add_edge(START, "explain")
    workflow.add_edge("explain", END)
    graph = workflow.compile()
    result = await asyncio.wait_for(
        graph.ainvoke({"output": None}),
        timeout=AI_TIMEOUT_SECONDS,
    )
    return result["output"]


def _cache_key(size: str, eases: dict[str, float]) -> tuple:
    return (size, eases.get("chest_cm"), eases.get("waist_cm"))


async def explain_fit(size: str, eases: dict[str, Optional[float]] | None, garment: dict | None = None) -> dict:
    """Return an explanation; never raises for AI failures (fallback instead)."""
    cleaned = _clean_eases(eases)
    size = (size or "").strip()
    if not size:
        return fallback_payload("—", cleaned, "invalid_size")
    key = _cache_key(size, cleaned)
    cached = _CACHE.get(key)
    if cached is not None:
        return dict(cached)
    if not cleaned:
        return fallback_payload(size, cleaned, "no_ease")
    if not is_configured():
        return fallback_payload(size, cleaned, "not_configured")

    try:
        output = await _call_model(size, cleaned, garment)
    except asyncio.TimeoutError:
        return fallback_payload(size, cleaned, "timeout")
    except Exception as exc:  # quota, 503, parse, import
        text = str(exc).lower()
        reason = "quota" if ("429" in text or "quota" in text or "resource_exhausted" in text) else "ai_error"
        logger.info("fit explain: AI unavailable (%s): %s", reason, exc)
        return fallback_payload(size, cleaned, reason)

    if not output_uses_only_input_ease(output, cleaned):
        return fallback_payload(size, cleaned, "number_mismatch")
    if len(output.explanation) > MAX_EXPLANATION_CHARS:
        return fallback_payload(size, cleaned, "too_long")

    payload = {
        "size": size,
        "explanation": output.explanation,
        "basis": [{"metric": key_name, "ease_cm": value} for key_name, value in cleaned.items()],
        "source": "ai",
        "fallback_reason": None,
    }
    if len(_CACHE) >= CACHE_LIMIT:
        _CACHE.clear()
    _CACHE[key] = payload
    return dict(payload)
