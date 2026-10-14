import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import logging
import threading
import time
from uuid import uuid4

import numpy as np

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .config import DATA, MAX_UPLOAD, RESULT_TTL_SECONDS
from .images import InvalidPhoto, decode_photo
from .reconstruction import ENGINE, close_detector, readiness, reconstruct

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
    measurements: dict[str, float] = field(default_factory=dict)
    body_profile: dict = field(default_factory=dict)
    elapsed_seconds: float | None = None


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
    DATA.mkdir(exist_ok=True, parents=True)
    cleanup()

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


@app.get("/api/health")
def health():
    ready, message = readiness()
    return {"ready": ready, "engine": ENGINE, "message": message, "retention_seconds": RESULT_TTL_SECONDS}


def process(key: str, front_image: np.ndarray, side_image: np.ndarray, height_cm: float):
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
        result = reconstruct(front_image, side_image, height_cm, path, report)
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
async def create_scan(front: UploadFile = File(...), side: UploadFile = File(...), height_cm: float = Form(..., ge=100, le=230), consent: bool = Form(False)):
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
    key = uuid4().hex
    with lock:
        # Recheck after awaiting uploads: admissions must be atomic.
        if sum(j.status in {"queued", "processing"} for j in jobs.values()) >= 3:
            raise HTTPException(429, "Hàng đợi đã đầy. Hãy thử lại sau.")
        jobs[key] = Job(id=key)
        response = asdict(jobs[key])
    executor.submit(process, key, front_image, side_image, height_cm)
    return response


@app.get("/api/scans/{key}")
def get_scan(key: str):
    cleanup()
    with lock:
        if key not in jobs:
            raise HTTPException(404, "Phiên đã hết hạn hoặc không tồn tại. Hãy tạo phiên mới.")
        return asdict(jobs[key])


@app.get("/api/scans/{key}/model")
def get_model(key: str):
    cleanup()
    with lock:
        job = jobs.get(key)
        if job is None or job.status != "completed":
            raise HTTPException(404, "Chưa có mô hình cho phiên này.")
        path = DATA / f"{job.id}.glb"
    if not path.is_file():
        raise HTTPException(404, "Mô hình đã hết hạn.")
    return FileResponse(path, media_type="model/gltf-binary", filename="morph-body.glb", headers={"Cache-Control": "no-store"})


@app.delete("/api/scans/{key}", status_code=204)
def delete_scan(key: str):
    with lock:
        job = jobs.pop(key, None)
        if job is not None:
            (DATA / f"{job.id}.glb").unlink(missing_ok=True)
