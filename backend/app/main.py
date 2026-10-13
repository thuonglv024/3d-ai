import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import logging
from pathlib import Path
import secrets
import threading
import time
from typing import Literal, Optional, Union
from uuid import uuid4

import numpy as np

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from .config import DATA, MAX_UPLOAD, RESULT_TTL_SECONDS
from .images import InvalidPhoto, decode_photo
from .reconstruction import ENGINE, capture_feedback, close_detector, readiness, reconstruct
from .sizing import SizeChart, SizingRecommendRequest, recommend_size
from .catalog import router as catalog_router
from .orders import init_db as init_orders_db, router as orders_router
from .auth import get_optional_user, router as auth_router
from .history import persist_scan_snapshot, router as history_router
from .db import get_db_connection, get_product_by_slug_or_id

logger = logging.getLogger(__name__)
lock = threading.RLock()
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="morph-scan")


class SessionCancelled(Exception):
    """Raised when a job session was deleted while being processed."""


@dataclass
class Job:
    id: str
    status: str = "queued"
    stage: str = "Đang chờ xử lý…"
    created: float = field(default_factory=time.time)
    finished: float | None = None
    model_url: str | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    measurements: dict[str, float | None] = field(default_factory=dict)
    body_profile: dict = field(default_factory=dict)
    elapsed_seconds: float | None = None
    user_id: str | None = None
    guest_token: str | None = None
    capture_mode: str = "full_body"
    height_cm: float = 170.0


jobs: dict[str, Job] = {}


def cleanup():
    now = time.time()
    with lock:
        expired = [key for key, job in jobs.items() if job.finished and now - job.finished > RESULT_TTL_SECONDS]
        for key in expired:
            (DATA / f"{key}.glb").unlink(missing_ok=True)
            jobs.pop(key, None)
        # Previous-process artifacts have no session to serve and can be removed.
        for path in DATA.glob("*.glb"):
            if path.stem not in jobs:
                path.unlink(missing_ok=True)


@asynccontextmanager
async def lifespan(app):
    global executor
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="morph-scan")
    DATA.mkdir(exist_ok=True, parents=True)
    cleanup()
    init_orders_db()

    async def janitor():
        while True:
            await asyncio.sleep(30)
            cleanup()

    task = asyncio.create_task(janitor())
    yield
    task.cancel()
    executor.shutdown(wait=True, cancel_futures=True)
    close_detector()


app = FastAPI(title="MORPH AI Demo", version="0.1.0", lifespan=lifespan)
app.include_router(catalog_router)
app.include_router(orders_router)
app.include_router(auth_router)
app.include_router(history_router)


def check_scan_access(job: Job, request: Request, guest_token: Optional[str] = None) -> None:
    """Verifies that the requester has permission to view this scan job."""
    if job.user_id is not None:
        user = get_optional_user(request)
        if not user or user["id"] != job.user_id:
            raise HTTPException(403, "Bạn không có quyền truy cập phiên scan này.")
    else:
        # Guest scan: if token is supplied via argument, header, or query, verify it matches
        token = (
            guest_token
            or request.headers.get("X-Guest-Token")
            or request.query_params.get("guest_token")
        )
        if token and job.guest_token:
            token_clean = token.strip()
            job_token_clean = job.guest_token.strip()
            if not secrets.compare_digest(token_clean, job_token_clean):
                raise HTTPException(403, "guest_token không hợp lệ.")


def auto_save_scan_if_enabled(job: Job) -> None:
    """If the scan belongs to a logged-in user with auto_save_scans enabled, persist snapshot."""
    if not job.user_id:
        return
    try:
        with get_db_connection() as conn:
            user_row = conn.execute(
                "SELECT auto_save_scans FROM users WHERE id = ?",
                (job.user_id,),
            ).fetchone()
            if user_row and user_row["auto_save_scans"]:
                persist_scan_snapshot(job.user_id, job)
    except Exception as exc:
        logger.warning("Auto-save failed for job %s: %s", job.id, exc)


@app.get("/api/health")
def health():
    ready, message = readiness()
    return {"ready": ready, "engine": ENGINE, "message": message, "retention_seconds": RESULT_TTL_SECONDS}


@app.post("/api/capture-check")
async def check_capture(photo: UploadFile = File(...), view: Literal["front", "side"] = Form(...), consent: bool = Form(False), capture_mode: Literal["full_body", "upper_body"] = Form("full_body")):
    try:
        if not consent:
            raise HTTPException(400, "Cần đồng ý gửi khung hình tới backend để hướng dẫn AI.")
        with lock:
            if any(j.status in {"queued", "processing"} for j in jobs.values()):
                raise HTTPException(429, "Đang dựng hình. Hướng dẫn camera sẽ tiếp tục sau.")
        data = await photo.read(2 * 1024 * 1024 + 1)
    finally:
        await photo.close()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(413, "Khung hình hướng dẫn tối đa 2 MB.")
    try:
        frame = decode_photo(data)
        result = await asyncio.to_thread(capture_feedback, frame, view, capture_mode) if capture_mode == "upper_body" else await asyncio.to_thread(capture_feedback, frame, view)
    except InvalidPhoto as exc:
        raise HTTPException(400, str(exc)) from exc
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


def process(key: str, front_image: np.ndarray, side_image: np.ndarray, height_cm: float, capture_mode: str = "full_body"):
    started = time.perf_counter()
    with lock:
        if key not in jobs:
            return
        jobs[key].status = "processing"

    def report(stage: str):
        with lock:
            if key not in jobs:
                raise SessionCancelled("Session deleted")
            jobs[key].stage = stage

    path = DATA / f"{key}.glb"
    try:
        result = reconstruct(front_image, side_image, height_cm, path, report, capture_mode) if capture_mode == "upper_body" else reconstruct(front_image, side_image, height_cm, path, report)
        if isinstance(result, tuple) and len(result) == 3:
            warnings, measurements, profile = result
        elif isinstance(result, tuple) and len(result) == 2:
            warnings, measurements = result
            profile = {}
        else:
            warnings, measurements, profile = result, {}, {}
        with lock:
            if key not in jobs:
                path.unlink(missing_ok=True)
                return
            job = jobs[key]
            job.status = "completed"
            job.stage = "Đã dựng hình"
            job.model_url = f"/api/scans/{key}/model"
            job.warnings = warnings
            job.measurements = measurements
            job.body_profile = profile
            job.elapsed_seconds = round(time.perf_counter() - started, 2)
            job.finished = time.time()

        # Check and trigger auto-persistence for logged-in users
        auto_save_scan_if_enabled(job)

    except SessionCancelled:
        path.unlink(missing_ok=True)
        return
    except Exception as exc:
        path.unlink(missing_ok=True)
        if not isinstance(exc, InvalidPhoto):
            logger.exception("Scan failed for job %s", key)
        with lock:
            if key in jobs:
                jobs[key].status = "failed"
                jobs[key].stage = "Cần kiểm tra lại ảnh"
                jobs[key].error = str(exc) if isinstance(exc, InvalidPhoto) else "Không dựng được hình. Kiểm tra log backend rồi thử lại."
                jobs[key].finished = time.time()


@app.post("/api/scans", status_code=202)
async def create_scan(
    request: Request,
    front: UploadFile = File(...),
    side: UploadFile = File(...),
    height_cm: float = Form(..., ge=100, le=230),
    consent: bool = Form(False),
    capture_mode: Literal["full_body", "upper_body"] = Form("full_body"),
):
    if not consent:
        raise HTTPException(400, "Cần đồng ý xử lý ảnh trước khi scan.")
    ready, message = readiness()
    if not ready:
        raise HTTPException(503, message)
    with lock:
        if sum(j.status in {"queued", "processing"} for j in jobs.values()) >= 3:
            raise HTTPException(429, "Demo đang xử lý nhiều ảnh. Hãy thử lại sau ít phút.")
    try:
        front_bytes = await front.read(MAX_UPLOAD + 1)
        side_bytes = await side.read(MAX_UPLOAD + 1)
    finally:
        await front.close(); await side.close()
    if len(front_bytes) > MAX_UPLOAD or len(side_bytes) > MAX_UPLOAD:
        raise HTTPException(413, "Mỗi ảnh tối đa 10 MB.")
    if sha256(front_bytes).digest() == sha256(side_bytes).digest():
        raise HTTPException(400, "Hai ảnh giống nhau. Hãy chọn một ảnh chính diện và một ảnh nghiêng.")
    try:
        front_image = decode_photo(front_bytes)
        side_image = decode_photo(side_bytes)
    except InvalidPhoto as exc:
        raise HTTPException(400, str(exc)) from exc
    del front_bytes, side_bytes

    # Identify user session or assign guest token
    user = get_optional_user(request)
    user_id = user["id"] if user else None
    guest_token = None if user_id else secrets.token_urlsafe(24)

    key = uuid4().hex
    with lock:
        # Recheck after awaiting uploads: admissions must be atomic.
        if sum(j.status in {"queued", "processing"} for j in jobs.values()) >= 3:
            raise HTTPException(429, "Hàng đợi đã đầy. Hãy thử lại sau.")
        jobs[key] = Job(
            id=key,
            user_id=user_id,
            guest_token=guest_token,
            capture_mode=capture_mode,
            height_cm=height_cm,
        )
        response = asdict(jobs[key])
    executor.submit(process, key, front_image, side_image, height_cm, capture_mode)
    return response


@app.get("/api/scans/{key}")
def get_scan(key: str, request: Request, guest_token: Optional[str] = Query(None)):
    cleanup()
    with lock:
        if key not in jobs:
            raise HTTPException(404, "Phiên đã hết hạn hoặc không tồn tại. Hãy tạo phiên mới.")
        job = jobs[key]
        check_scan_access(job, request, guest_token=guest_token)
        return asdict(job)


@app.get("/api/scans/{key}/model")
def get_model(key: str, request: Request, guest_token: Optional[str] = Query(None)):
    cleanup()
    with lock:
        job = jobs.get(key)
        if job is None or job.status != "completed":
            raise HTTPException(404, "Chưa có mô hình cho phiên này.")
        check_scan_access(job, request, guest_token=guest_token)
        path = DATA / f"{job.id}.glb"
    if not path.is_file():
        raise HTTPException(404, "Mô hình đã hết hạn.")
    return FileResponse(path, media_type="model/gltf-binary", filename="morph-body.glb", headers={"Cache-Control": "no-store"})


@app.get("/api/scans/{key}/measurements")
def download_measurements(key: str, request: Request, guest_token: Optional[str] = Query(None)):
    job = get_scan(key, request, guest_token=guest_token)
    if job["status"] != "completed":
        raise HTTPException(409, "Chưa có số đo cho phiên này.")
    return JSONResponse({"schema_version": 1, "unit": "cm", "measurements": job["measurements"], "body_fit": job["body_profile"], "warnings": job["warnings"]},
                        headers={"Cache-Control": "no-store", "Content-Disposition": 'attachment; filename="morph-measurements.json"'})


@app.post("/api/scans/{key}/size-advice")
def size_advice(key: str, chart: SizeChart, request: Request, guest_token: Optional[str] = Query(None)):
    cleanup()
    with lock:
        if key not in jobs:
            raise HTTPException(404, "Phiên đã hết hạn hoặc không tồn tại. Hãy tạo phiên mới.")
        job = jobs[key]
        check_scan_access(job, request, guest_token=guest_token)
        if job.status != "completed":
            raise HTTPException(409, "Cần hoàn thành scan trước khi đối chiếu size.")
        measurements = job.measurements
    return JSONResponse(recommend_size(measurements, chart), headers={"Cache-Control": "no-store"})


@app.post("/api/sizing/recommend")
def recommend_sizing(req: SizingRecommendRequest, request: Request):
    """
    Recommends apparel size based on product chart and body measurements.
    Measurements can come from payload, an active in-memory scan, or a saved DB scan.
    """
    # 1. Resolve chart
    target_chart: Optional[SizeChart] = req.chart
    product_id: Optional[str] = req.product_id
    product_slug: Optional[str] = req.product_slug
    product_name: Optional[str] = None

    if target_chart is None:
        target_prod_identifier = product_id or product_slug
        if not target_prod_identifier:
            raise HTTPException(
                status_code=400,
                detail="Cần cung cấp product_id, product_slug hoặc bảng size (chart).",
            )
        product = get_product_by_slug_or_id(target_prod_identifier)
        if not product:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")

        product_id = product["id"]
        product_slug = product["slug"]
        product_name = product["name"]

        if not product.get("chart"):
            raise HTTPException(status_code=400, detail="Sản phẩm không có bảng size.")
        try:
            target_chart = SizeChart(**product["chart"])
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Bảng size của sản phẩm không hợp lệ: {exc}")
    else:
        target_prod_identifier = product_id or product_slug
        if target_prod_identifier:
            product = get_product_by_slug_or_id(target_prod_identifier)
            if product:
                product_id = product["id"]
                product_slug = product["slug"]
                product_name = product["name"]

    # 2. Resolve measurements
    resolved_measurements: Optional[dict[str, Optional[float]]] = None

    if req.measurements is not None:
        resolved_measurements = req.measurements
    elif req.scan_id or req.saved_scan_id:
        target_scan_id = req.scan_id or req.saved_scan_id
        target_job = None
        with lock:
            target_job = jobs.get(target_scan_id)

        effective_guest_token = (
            req.guest_token
            or request.headers.get("X-Guest-Token")
            or request.query_params.get("guest_token")
        )

        if target_job:
            check_scan_access(target_job, request, guest_token=effective_guest_token)
            if target_job.status != "completed":
                raise HTTPException(400, "Phiên scan chưa hoàn thành.")
            resolved_measurements = target_job.measurements or {}
        else:
            with get_db_connection() as conn:
                scan_row = conn.execute(
                    """
                    SELECT id, user_id, source_scan_id
                    FROM body_scans
                    WHERE id = ? OR source_scan_id = ?
                    """,
                    (target_scan_id, target_scan_id),
                ).fetchone()

                if not scan_row:
                    raise HTTPException(404, "Không tìm thấy thông tin scan.")

                current_user = get_optional_user(request)
                if scan_row["user_id"] is not None:
                    if not current_user or current_user["id"] != scan_row["user_id"]:
                        raise HTTPException(403, "Bạn không có quyền truy cập phiên scan này.")

                m_rows = conn.execute(
                    "SELECT metric_key, value_cm FROM body_measurements WHERE body_scan_id = ?",
                    (scan_row["id"],),
                ).fetchall()
                resolved_measurements = {r["metric_key"]: r["value_cm"] for r in m_rows}
    else:
        resolved_measurements = {}

    # 3. Compute recommendation
    res = recommend_size(resolved_measurements, target_chart)
    res["product_id"] = product_id
    res["product_slug"] = product_slug
    res["product_name"] = product_name
    res["chart_name"] = target_chart.name
    res["garment"] = target_chart.garment

    return JSONResponse(res, headers={"Cache-Control": "no-store"})


@app.delete("/api/scans/{key}", status_code=204)
def delete_scan(key: str, request: Request, guest_token: Optional[str] = Query(None)):
    with lock:
        job = jobs.get(key)
        if job is not None:
            check_scan_access(job, request, guest_token=guest_token)
            jobs.pop(key, None)
            (DATA / f"{job.id}.glb").unlink(missing_ok=True)
