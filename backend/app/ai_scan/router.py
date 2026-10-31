"""HTTP routes for the experimental AI scan mode."""

from __future__ import annotations

import asyncio
from hashlib import sha256
import logging
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..config import MAX_UPLOAD
from ..images import InvalidPhoto, decode_photo
from .config import (
    PROVIDER,
    REQUEST_TIMEOUT_SECONDS,
    configuration_message,
    configured_model,
    is_configured,
)
from .schemas import AiScanResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-scan", tags=["ai-scan"])


@router.get("/health")
def ai_health():
    """Report whether the optional AI mode is configured (never exposes the key)."""
    return {
        "ready": is_configured(),
        "provider": PROVIDER,
        "model": configured_model(),
        "message": configuration_message(),
    }


@router.post("/analyze", response_model=AiScanResponse)
async def analyze(
    front: UploadFile = File(...),
    side: UploadFile = File(...),
    height_cm: float = Form(..., ge=100, le=230),
    consent: bool = Form(False),
    capture_mode: Literal["full_body", "upper_body"] = Form("upper_body"),
    sex: Literal["auto", "female", "male"] = Form("auto"),
):
    """Estimate measurements from two photos without storing them.

    Images are validated in memory and sent to Gemini as base64 data URLs. The
    endpoint never writes the photos to disk.
    """
    if not consent:
        raise HTTPException(400, "Cần đồng ý gửi hai ảnh tới dịch vụ AI để phân tích.")

    try:
        front_bytes = await front.read(MAX_UPLOAD + 1)
        side_bytes = await side.read(MAX_UPLOAD + 1)
    finally:
        await front.close()
        await side.close()

    if len(front_bytes) > MAX_UPLOAD or len(side_bytes) > MAX_UPLOAD:
        raise HTTPException(413, "Mỗi ảnh tối đa 10 MB.")
    if sha256(front_bytes).digest() == sha256(side_bytes).digest():
        raise HTTPException(400, "Hai ảnh giống nhau. Hãy chụp một ảnh chính diện và một ảnh nghiêng.")

    try:
        decode_photo(front_bytes)
        decode_photo(side_bytes)
    except InvalidPhoto as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        from . import service
    except ImportError as exc:  # pragma: no cover - only without AI extras
        logger.exception("AI scan dependencies are not installed")
        raise HTTPException(
            503,
            "AI mode chưa được cài đặt trên máy chủ. "
            "Chạy: backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-ai.txt",
        ) from exc

    try:
        result = await asyncio.wait_for(
            service.run_ai_scan(
                front_bytes,
                side_bytes,
                height_cm,
                capture_mode,
                front.content_type or "image/jpeg",
                side.content_type or "image/jpeg",
                sex,
            ),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except service.AiScanNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except service.AiScanQuotaExceeded as exc:
        raise HTTPException(429, str(exc)) from exc
    except service.AiScanUnavailable as exc:
        # 422 nghĩa là "dữ liệu đầu vào không xử lý được". Ở đây model phía trên
        # lỗi, nên trả 502 để client biết ảnh/đầu vào không phải nguyên nhân.
        raise HTTPException(502, str(exc)) from exc
    except asyncio.TimeoutError as exc:
        raise HTTPException(504, "Dịch vụ AI phản hồi quá lâu. Hãy thử lại sau.") from exc
    except Exception as exc:
        logger.exception("AI scan failed")
        detail = f"{type(exc).__name__} {exc}".lower()
        if any(hint in detail for hint in ("api key", "api_key", "unauthenticated", "permission_denied", " 401", " 403")):
            raise HTTPException(
                503,
                "GOOGLE_API_KEY trong backend/.env không hợp lệ hoặc đã hết hạn. "
                "Cập nhật key mới từ Google AI Studio — backend tự đọc lại file, không cần khởi động lại.",
            ) from exc
        raise HTTPException(
            502,
            "Không phân tích được ảnh bằng AI. Kiểm tra kết nối và cấu hình API key rồi thử lại.",
        ) from exc

    return JSONResponse(result, headers={"Cache-Control": "no-store"})
