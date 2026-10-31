import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import logging
import os
from pathlib import Path
import secrets
import threading
import time
from typing import Literal, Optional, Union
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from .config import DATA, MAX_UPLOAD, RESULT_TTL_SECONDS
from .images import InvalidPhoto, decode_photo
from . import anny_body
from .fitmap import FitMapRequest, compute_fit_map
from .reconstruction import ENGINE, build_from_measurements, capture_feedback, close_detector, readiness, reconstruct, refit_avatar
from .sizing import (
    SizeChart,
    SizingRecommendRequest,
    VALID_SIZING_SOURCES,
    filter_valid_sizing_measurements,
    recommend_size,
)
from .catalog import router as catalog_router
from .orders import init_db as init_orders_db, router as orders_router
from .auth import get_optional_user, router as auth_router
from .history import persist_scan_snapshot, router as history_router
from .ai_scan import ai_scan_router
from .db import get_db_connection, get_product_by_slug_or_id

logger = logging.getLogger(__name__)
lock = threading.RLock()
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="morph-scan")

MAX_ACTIVE_JOBS = 8
MAX_STORED_JOBS = 50
JOB_PROCESSING_TIMEOUT_SECONDS = 120


class MeasurementModelRequest(BaseModel):
    height_cm: float = Field(..., ge=100, le=230)
    sex: Literal["auto", "female", "male"] = "auto"
    capture_mode: Literal["full_body", "upper_body"] = "full_body"
    measurements: dict[str, Optional[float]] = Field(default_factory=dict)


class SessionCancelled(Exception):
    """Raised when a job session was deleted while being processed."""


@dataclass
class Job:
    id: str
    status: str = "queued"
    stage: str = "Đang chờ xử lý…"
    created: float = field(default_factory=time.time)
    started_processing: float | None = None
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
    sex: str = "auto"
    height_cm: float = 170.0
    revision: int = 0
    fitting: dict = field(default_factory=dict)
    overrides: dict = field(default_factory=dict)


jobs: dict[str, Job] = {}


def cleanup():
    now = time.time()
    with lock:
        # 1. Detect hung queued/processing jobs exceeding JOB_PROCESSING_TIMEOUT_SECONDS
        for key, job in list(jobs.items()):
            if job.status in {"queued", "processing"} and (now - job.created) > JOB_PROCESSING_TIMEOUT_SECONDS:
                job.status = "failed"
                job.stage = "Quá thời gian xử lý"
                job.error = "Phiên xử lý quá thời gian chờ. Vui lòng thử lại."
                job.finished = now
                (DATA / f"{key}.glb").unlink(missing_ok=True)

        # 2. Remove finished jobs past RESULT_TTL_SECONDS
        expired = [key for key, job in jobs.items() if job.finished and now - job.finished > RESULT_TTL_SECONDS]
        for key in expired:
            (DATA / f"{key}.glb").unlink(missing_ok=True)
            jobs.pop(key, None)

        # 3. Enforce MAX_STORED_JOBS cap on finished jobs (completed / failed)
        finished_jobs = [job for job in jobs.values() if job.status in {"completed", "failed"}]
        if len(finished_jobs) > MAX_STORED_JOBS:
            finished_jobs.sort(key=lambda j: j.created)
            excess = len(finished_jobs) - MAX_STORED_JOBS
            for old_job in finished_jobs[:excess]:
                (DATA / f"{old_job.id}.glb").unlink(missing_ok=True)
                jobs.pop(old_job.id, None)

        # 4. Previous-process or orphaned artifacts have no session to serve and can be removed.
        for path in DATA.glob("*.glb"):
            job = jobs.get(path.stem)
            if job is None or job.status == "failed":
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
app.include_router(ai_scan_router)


def check_scan_access(job: Job, request: Request, guest_token: Optional[str] = None) -> None:
    """Verifies that the requester has permission to view this scan job."""
    if job.user_id is not None:
        user = get_optional_user(request)
        if not user or user["id"] != job.user_id:
            raise HTTPException(403, "Bạn không có quyền truy cập phiên scan này.")
    else:
        if not job.guest_token or not job.guest_token.strip():
            raise HTTPException(403, "guest_token không hợp lệ hoặc bị thiếu.")
        token = (
            guest_token
            or request.headers.get("X-Guest-Token")
            or request.query_params.get("guest_token")
        )
        if not token or not token.strip():
            raise HTTPException(403, "guest_token không hợp lệ hoặc bị thiếu.")
        token_clean = token.strip()
        job_token_clean = job.guest_token.strip()
        if not secrets.compare_digest(token_clean, job_token_clean):
            raise HTTPException(403, "guest_token không hợp lệ hoặc bị thiếu.")


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
    return {
        "ready": ready,
        "engine": ENGINE,
        "body_model": anny_body.describe(),
        "message": message,
        "retention_seconds": RESULT_TTL_SECONDS,
    }


@app.post("/api/capture-check")
async def check_capture(photo: UploadFile = File(...), view: Literal["front", "side"] = Form(...), consent: bool = Form(False), capture_mode: Literal["full_body", "upper_body"] = Form("full_body")):
    try:
        if not consent:
            raise HTTPException(400, "Cần đồng ý gửi khung hình tới backend để hướng dẫn AI.")
        cleanup()
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


def process(key: str, front_image: np.ndarray, side_image: np.ndarray, height_cm: float, capture_mode: str = "full_body", sex: str = "auto"):
    started = time.perf_counter()
    started_wall = time.time()
    with lock:
        if key not in jobs or jobs[key].status == "failed":
            return
        jobs[key].status = "processing"
        jobs[key].started_processing = started_wall

    def report(stage: str):
        with lock:
            if key not in jobs or jobs[key].status == "failed":
                raise SessionCancelled("Session deleted")
            jobs[key].stage = stage

    path = DATA / f"{key}.glb"
    try:
        result = reconstruct(front_image, side_image, height_cm, path, report, capture_mode, sex)
        if isinstance(result, tuple) and len(result) == 3:
            warnings, measurements, profile = result
        elif isinstance(result, tuple) and len(result) == 2:
            warnings, measurements = result
            profile = {}
        else:
            warnings, measurements, profile = result, {}, {}
        with lock:
            if key not in jobs or jobs[key].status == "failed":
                path.unlink(missing_ok=True)
                return
            job = jobs[key]
            job.status = "completed"
            job.stage = "Đã dựng hình"
            job.model_url = f"/api/scans/{key}/model"
            job.warnings = warnings
            job.measurements = measurements
            job.body_profile = profile
            job.fitting = profile.get("fitting", {})
            job.elapsed_seconds = round(time.perf_counter() - started, 4)
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


def process_measurements(key: str, req: MeasurementModelRequest):
    started = time.perf_counter()
    with lock:
        if key not in jobs:
            return
        jobs[key].status = "processing"
        jobs[key].started_processing = time.time()
    path = DATA / f"{key}.glb"
    try:
        profile = build_from_measurements(req.measurements, req.height_cm, req.sex, req.capture_mode, path)
        measurements = dict(req.measurements)
        measurements["height_cm"] = req.height_cm
        with lock:
            if key not in jobs or jobs[key].status == "failed":
                path.unlink(missing_ok=True)
                return
            job = jobs[key]
            job.status = "completed"
            job.stage = "Đã dựng hình"
            job.model_url = f"/api/scans/{key}/model"
            job.warnings = []
            job.measurements = measurements
            job.body_profile = profile
            job.fitting = profile.get("fitting", {})
            job.elapsed_seconds = round(time.perf_counter() - started, 4)
            job.finished = time.time()
        auto_save_scan_if_enabled(job)
    except Exception as exc:
        path.unlink(missing_ok=True)
        logger.exception("Measurement build failed for job %s", key)
        with lock:
            if key in jobs:
                jobs[key].status = "failed"
                jobs[key].stage = "Cần kiểm tra số đo"
                jobs[key].error = str(exc) if isinstance(exc, InvalidPhoto) else "Không dựng được hình từ số đo."
                jobs[key].finished = time.time()


@app.post("/api/scans/from-measurements", status_code=202)
async def create_scan_from_measurements(request: Request, req: MeasurementModelRequest):
    ready, _ = readiness()
    if not ready:
        raise HTTPException(503, "Backend chưa sẵn sàng.")
    cleanup()
    user = get_optional_user(request)
    user_id = user["id"] if user else None
    guest_token = None if user_id else secrets.token_urlsafe(24)
    key = uuid4().hex
    with lock:
        if sum(j.status in {"queued", "processing"} for j in jobs.values()) >= MAX_ACTIVE_JOBS:
            raise HTTPException(429, "Hàng đợi đã đầy. Hãy thử lại sau.")
        jobs[key] = Job(id=key, user_id=user_id, guest_token=guest_token, capture_mode=req.capture_mode, sex=req.sex, height_cm=req.height_cm)
        response = asdict(jobs[key])
    executor.submit(process_measurements, key, req)
    return response


@app.post("/api/scans", status_code=202)
async def create_scan(
    request: Request,
    front: UploadFile = File(...),
    side: UploadFile = File(...),
    height_cm: float = Form(..., ge=100, le=230),
    consent: bool = Form(False),
    capture_mode: Literal["full_body", "upper_body"] = Form("full_body"),
    sex: Literal["auto", "female", "male"] = Form("auto"),
):
    if not consent:
        raise HTTPException(400, "Cần đồng ý xử lý ảnh trước khi scan.")
    ready, message = readiness()
    if not ready:
        raise HTTPException(503, message)
    cleanup()
    with lock:
        if sum(j.status in {"queued", "processing"} for j in jobs.values()) >= MAX_ACTIVE_JOBS:
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
        if sum(j.status in {"queued", "processing"} for j in jobs.values()) >= MAX_ACTIVE_JOBS:
            raise HTTPException(429, "Hàng đợi đã đầy. Hãy thử lại sau.")
        jobs[key] = Job(
            id=key,
            user_id=user_id,
            guest_token=guest_token,
            capture_mode=capture_mode,
            sex=sex,
            height_cm=height_cm,
        )
        response = asdict(jobs[key])
    executor.submit(process, key, front_image, side_image, height_cm, capture_mode, sex)
    return response


@app.get("/api/scans/{key}")
def get_scan(key: str, request: Request, guest_token: Optional[str] = Query(None)):
    cleanup()
    with lock:
        if key not in jobs:
            raise HTTPException(404, "Phiên đã hết hạn hoặc không tồn tại. Hãy tạo phiên mới.")
        job = jobs[key]
        check_scan_access(job, request, guest_token=guest_token)
        payload = asdict(job)
        if job.user_id is not None:
            payload["guest_token"] = None
        return payload


class MeasurementPatch(BaseModel):
    height_cm: Optional[float] = Field(None, ge=100, le=230)
    chest_cm: Optional[float] = Field(None, ge=40, le=200)
    waist_cm: Optional[float] = Field(None, ge=30, le=200)
    hip_cm: Optional[float] = Field(None, ge=40, le=200)


@app.patch("/api/scans/{key}/measurements")
def patch_measurements(key: str, req: MeasurementPatch, request: Request, guest_token: Optional[str] = Query(None)):
    """Apply user-corrected measurements and rebuild the avatar without the photos."""
    cleanup()
    with lock:
        job = jobs.get(key)
        if job is None:
            raise HTTPException(404, "Phiên đã hết hạn hoặc không tồn tại.")
        check_scan_access(job, request, guest_token=guest_token)
        if job.status != "completed":
            raise HTTPException(409, "Cần hoàn tất quét trước khi sửa số đo.")
        changes = {name: value for name, value in req.model_dump().items() if value is not None}
        if not changes:
            raise HTTPException(400, "Chưa có số đo nào để cập nhật.")
        fitting = dict(job.fitting or {})
        if not fitting.get("targets"):
            raise HTTPException(409, "Phiên này không lưu dữ liệu dựng lại. Hãy quét lại.")
        measurements = dict(job.measurements or {})
        overrides = dict(job.overrides or {})
        height_cm = float(changes.pop("height_cm", measurements.get("height_cm") or job.height_cm))
        measurements.update(changes)
        measurements["height_cm"] = height_cm
        overrides.update(changes)
        if abs(height_cm - float(job.height_cm)) > 1e-6:
            overrides["height_cm"] = height_cm
        base_warnings = [warning for warning in (job.warnings or []) if "chỉnh tay" not in warning]

    path = DATA / f"{key}.glb"
    temp = DATA / f"{key}.refit.glb"
    try:
        profile = refit_avatar(fitting, measurements, overrides, height_cm, temp)
    except InvalidPhoto as exc:
        temp.unlink(missing_ok=True)
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # pragma: no cover - geometry failure path
        temp.unlink(missing_ok=True)
        logger.exception("Refit failed for job %s", key)
        raise HTTPException(500, "Không dựng lại được mô hình với số đo mới.") from exc

    os.replace(temp, path)
    with lock:
        job = jobs.get(key)
        if job is None:
            path.unlink(missing_ok=True)
            raise HTTPException(404, "Phiên đã hết hạn trong lúc dựng lại.")
        profile["quality_diagnostics"] = (job.body_profile or {}).get("quality_diagnostics", {})
        job.measurements = measurements
        job.body_profile = profile
        job.fitting = {**fitting, "height_cm": height_cm}
        job.overrides = overrides
        job.height_cm = height_cm
        job.revision = int(job.revision) + 1
        job.warnings = base_warnings + ["Số đo đã được bạn chỉnh tay; mô hình 3D và gợi ý size đã được dựng lại."]
        payload = asdict(job)
        if job.user_id is not None:
            payload["guest_token"] = None
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


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
        effective_mode = (job.body_profile or {}).get("capture_mode") or job.capture_mode
        measurements = filter_valid_sizing_measurements(
            job.measurements or {},
            (job.body_profile or {}).get("measurement_details"),
            capture_mode=effective_mode,
        )
    return JSONResponse(recommend_size(measurements, chart), headers={"Cache-Control": "no-store"})


@app.post("/api/fit-map")
def fit_map(req: FitMapRequest):
    """Estimated tight/loose regions for a size, from the size chart + measurements."""
    identifier = req.product_id or req.product_slug
    if not identifier:
        raise HTTPException(400, "Cần product_id hoặc product_slug.")
    product = get_product_by_slug_or_id(identifier)
    if not product:
        raise HTTPException(404, "Không tìm thấy sản phẩm.")
    if not product.get("chart"):
        raise HTTPException(400, "Sản phẩm không có bảng size.")
    return JSONResponse(compute_fit_map(product, req.size, req.measurements), headers={"Cache-Control": "no-store"})


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
        cleanup()
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
            effective_mode = (target_job.body_profile or {}).get("capture_mode") or target_job.capture_mode
            resolved_measurements = filter_valid_sizing_measurements(
                target_job.measurements or {},
                (target_job.body_profile or {}).get("measurement_details"),
                capture_mode=effective_mode,
            )
        else:
            with get_db_connection() as conn:
                scan_row = conn.execute(
                    """
                    SELECT id, user_id, source_scan_id, capture_mode
                    FROM body_scans
                    WHERE id = ? OR source_scan_id = ?
                    """,
                    (target_scan_id, target_scan_id),
                ).fetchone()

                if not scan_row:
                    raise HTTPException(404, "Không tìm thấy thông tin scan.")

                current_user = get_optional_user(request)
                if not current_user or current_user["id"] != scan_row["user_id"]:
                    raise HTTPException(403, "Bạn không có quyền truy cập phiên scan này.")

                m_rows = conn.execute(
                    "SELECT metric_key, value_cm, source FROM body_measurements WHERE body_scan_id = ?",
                    (scan_row["id"],),
                ).fetchall()
                resolved_measurements = {
                    r["metric_key"]: (
                        r["value_cm"]
                        if r["source"] in VALID_SIZING_SOURCES
                        and r["value_cm"] is not None
                        and float(r["value_cm"]) > 0
                        and not (
                            scan_row["capture_mode"] == "upper_body"
                            and r["metric_key"] == "hip_cm"
                            and r["source"] != "user_input"
                        )
                        else None
                    )
                    for r in m_rows
                }
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
