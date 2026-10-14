"""User body scan history, comparison, and tracking APIs for MORPH AI."""
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import secrets
from typing import Literal, Optional, Union
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field


from .auth import get_current_user
from .db import get_db_connection, get_db_path
from .reconstruction import ENGINE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user/scans", tags=["scan_history"])

LABEL_MAP = {
    "height_cm": "Chiều cao",
    "chest_cm": "Vòng ngực",
    "waist_cm": "Vòng eo",
    "hip_cm": "Vòng mông",
    "shoulder_width_cm": "Rộng vai",
    "head_cm": "Vòng đầu",
    "neck_cm": "Vòng cổ",
    "thigh_cm": "Vòng đùi trái",
    "calf_cm": "Vòng bắp chân trái",
    "ankle_cm": "Vòng cổ chân trái",
    "arm_length_cm": "Dài tay",
    "inseam_cm": "Dài trong chân",
}

DISCLAIMER_TEXT = (
    "Số đo được ước lượng bằng thị giác máy tính từ ảnh và mô hình MakeHuman, "
    "không phải phép đo nhân trắc học chính xác hay may đo y tế. Các thông số "
    "từ template_model không thể dùng để theo dõi biến thiên cơ thể."
)


class SaveScanRequest(BaseModel):
    scan_id: str
    guest_token: Optional[str] = None
    note: Optional[str] = None


class UpdateScanRequest(BaseModel):
    note: Optional[str] = None


def persist_scan_snapshot(
    user_id: str,
    job,
    note: Optional[str] = None,
    db_path: Optional[Union[Path, str]] = None,
) -> dict:
    """
    Saves or returns existing scan record for user in SQLite.
    Atomically copies measurements snapshot; ignores client-supplied values.
    """
    now_utc = datetime.now(timezone.utc)
    now_str = now_utc.isoformat()
    captured_at = datetime.fromtimestamp(job.created, timezone.utc).isoformat() if getattr(job, "created", None) else now_str

    capture_mode = getattr(job, "capture_mode", "full_body") or "full_body"
    height_cm = float(getattr(job, "height_cm", 170.0) or 170.0)
    warnings_json = json.dumps(getattr(job, "warnings", []) or [], ensure_ascii=False)

    with get_db_connection(db_path) as conn:
        # Check idempotency: UNIQUE(user_id, source_scan_id)
        existing = conn.execute(
            """
            SELECT id, user_id, source_scan_id, captured_at, saved_at,
                   capture_mode, height_input_cm, engine_version,
                   measurement_schema_version, warnings, note
            FROM body_scans
            WHERE user_id = ? AND source_scan_id = ?
            """,
            (user_id, job.id),
        ).fetchone()

        if existing:
            if note is not None:
                conn.execute(
                    "UPDATE body_scans SET note = ? WHERE id = ?",
                    (note, existing["id"]),
                )
                conn.commit()
            return fetch_scan_detail(existing["id"], user_id, conn)

        # New scan entry
        scan_id = uuid.uuid4().hex
        conn.execute(
            """
            INSERT INTO body_scans (
                id, user_id, source_scan_id, captured_at, saved_at,
                capture_mode, height_input_cm, engine_version,
                measurement_schema_version, warnings, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                scan_id,
                user_id,
                job.id,
                captured_at,
                now_str,
                capture_mode,
                height_cm,
                ENGINE,
                warnings_json,
                note,
            ),
        )

        # Populate measurements snapshot from authoritative job memory
        details = (job.body_profile or {}).get("measurement_details")
        measurements_to_insert = []
        seen_keys = set()

        if details and isinstance(details, list):
            for item in details:
                m_key = item.get("key")
                if m_key and m_key not in seen_keys:
                    seen_keys.add(m_key)
                    val = item.get("value_cm")
                    val_float = round(float(val), 1) if val is not None else None
                    src = item.get("source", "photo_estimate")
                    measurements_to_insert.append((
                        uuid.uuid4().hex,
                        scan_id,
                        m_key,
                        val_float,
                        src,
                    ))

        # Fallback to job.measurements dict if details was empty
        if not measurements_to_insert and getattr(job, "measurements", None):
            for m_key, val in job.measurements.items():
                if m_key not in seen_keys:
                    seen_keys.add(m_key)
                    val_float = round(float(val), 1) if val is not None else None
                    if m_key == "height_cm":
                        src = "user_input"
                    elif capture_mode == "upper_body" and m_key in {"chest_cm", "waist_cm", "shoulder_width_cm"}:
                        src = "photo_with_prior"
                    elif capture_mode == "upper_body" and m_key in {"head_cm", "neck_cm", "hip_cm", "thigh_cm", "calf_cm", "ankle_cm"}:
                        src = "template_model"
                    elif val_float is not None:
                        src = "photo_estimate"
                    else:
                        src = "unavailable"
                    measurements_to_insert.append((
                        uuid.uuid4().hex,
                        scan_id,
                        m_key,
                        val_float,
                        src,
                    ))

        for row in measurements_to_insert:
            conn.execute(
                """
                INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                row,
            )

        conn.commit()
        return fetch_scan_detail(scan_id, user_id, conn)


def fetch_scan_detail(scan_id: str, user_id: str, conn) -> dict:
    """Fetches complete scan detail with all measurements."""
    scan = conn.execute(
        """
        SELECT id, user_id, source_scan_id, captured_at, saved_at,
               capture_mode, height_input_cm, engine_version,
               measurement_schema_version, warnings, note
        FROM body_scans
        WHERE id = ? AND user_id = ?
        """,
        (scan_id, user_id),
    ).fetchone()

    if not scan:
        raise HTTPException(status_code=404, detail="Không tìm thấy lần scan.")

    m_rows = conn.execute(
        """
        SELECT metric_key, value_cm, source
        FROM body_measurements
        WHERE body_scan_id = ?
        ORDER BY rowid ASC
        """,
        (scan_id,),
    ).fetchall()

    try:
        warnings = json.loads(scan["warnings"] or "[]")
    except Exception:
        warnings = []

    measurements = [
        {
            "metric_key": r["metric_key"],
            "label": LABEL_MAP.get(r["metric_key"], r["metric_key"]),
            "value_cm": r["value_cm"],
            "source": r["source"],
        }
        for r in m_rows
    ]

    return {
        "id": scan["id"],
        "source_scan_id": scan["source_scan_id"],
        "captured_at": scan["captured_at"],
        "saved_at": scan["saved_at"],
        "capture_mode": scan["capture_mode"],
        "height_input_cm": scan["height_input_cm"],
        "engine_version": scan["engine_version"],
        "measurement_schema_version": scan["measurement_schema_version"],
        "warnings": warnings,
        "note": scan["note"],
        "measurements": measurements,
    }


# --- Endpoints ---
@router.post("/save")
def save_scan(
    req: SaveScanRequest,
    x_guest_token: Optional[str] = Header(None, alias="X-Guest-Token"),
    current_user: dict = Depends(get_current_user),
    db_path: Optional[Union[Path, str]] = None,
):
    """
    Saves an in-memory scan into user's persistent history.
    Verifies ownership or guest_token claim, idempotently copies authoritative measurements.
    """
    # 1. Check if user already owns this scan or it is already saved in DB
    with get_db_connection(db_path) as conn:
        existing = conn.execute(
            """
            SELECT id FROM body_scans
            WHERE user_id = ? AND (source_scan_id = ? OR id = ?)
            """,
            (current_user["id"], req.scan_id, req.scan_id),
        ).fetchone()

        if existing:
            if req.note is not None:
                conn.execute(
                    "UPDATE body_scans SET note = ? WHERE id = ?",
                    (req.note, existing["id"]),
                )
                conn.commit()
            return fetch_scan_detail(existing["id"], current_user["id"], conn)

    from .main import jobs, lock

    target_job = None
    with lock:
        target_job = jobs.get(req.scan_id)

    # 2. Job found in memory
    if target_job:
        if target_job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chỉ có thể lưu phiên scan đã hoàn thành.",
            )

        # Check / claim ownership
        if target_job.user_id is not None:
            if target_job.user_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền lưu phiên scan này.",
                )
            with lock:
                target_job.guest_token = None
        else:
            # Guest scan -> claim requires valid guest_token
            if not target_job.guest_token or not target_job.guest_token.strip():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="guest_token không hợp lệ để nhận phiên scan này.",
                )
            req_token = (req.guest_token or x_guest_token or "").strip()
            job_token = target_job.guest_token.strip()
            if not req_token or not secrets.compare_digest(req_token, job_token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="guest_token không hợp lệ để nhận phiên scan này.",
                )
            with lock:
                target_job.user_id = current_user["id"]
                target_job.guest_token = None

        result = persist_scan_snapshot(current_user["id"], target_job, req.note, db_path)
        return result

    # 3. Job not in memory and not in DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Phiên scan không tồn tại hoặc đã hết hạn.",
    )


@router.get("")
def list_scans(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    capture_mode: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db_path: Optional[Union[Path, str]] = None,
):
    """Returns paginated body scans with key measurements summary."""
    conditions = ["user_id = ?"]
    params: list = [current_user["id"]]

    if capture_mode:
        conditions.append("capture_mode = ?")
        params.append(capture_mode.strip())

    if from_date:
        conditions.append("captured_at >= ?")
        params.append(from_date.strip())

    if to_date:
        conditions.append("captured_at <= ?")
        params.append(to_date.strip())

    where_clause = " WHERE " + " AND ".join(conditions)

    with get_db_connection(db_path) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM body_scans {where_clause}",
            params,
        ).fetchone()[0]

        offset = (page - 1) * limit
        rows = conn.execute(
            f"""
            SELECT id, source_scan_id, captured_at, saved_at,
                   capture_mode, height_input_cm, engine_version,
                   measurement_schema_version, note
            FROM body_scans
            {where_clause}
            ORDER BY captured_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        scan_ids = [r["id"] for r in rows]
        key_metrics_by_scan = {sid: {} for sid in scan_ids}

        if scan_ids:
            placeholders = ",".join("?" for _ in scan_ids)
            m_rows = conn.execute(
                f"""
                SELECT body_scan_id, metric_key, value_cm, source
                FROM body_measurements
                WHERE body_scan_id IN ({placeholders})
                  AND metric_key IN ('height_cm', 'chest_cm', 'waist_cm', 'hip_cm', 'shoulder_width_cm')
                """,
                scan_ids,
            ).fetchall()

            for mr in m_rows:
                val = mr["value_cm"]
                if (
                    mr["source"] in ("template_model", "unavailable")
                    or val is None
                    or float(val) <= 0
                ):
                    key_metrics_by_scan[mr["body_scan_id"]][mr["metric_key"]] = None
                else:
                    key_metrics_by_scan[mr["body_scan_id"]][mr["metric_key"]] = val

        items = []
        for r in rows:
            sid = r["id"]
            km = key_metrics_by_scan.get(sid, {})
            items.append({
                "id": sid,
                "source_scan_id": r["source_scan_id"],
                "captured_at": r["captured_at"],
                "saved_at": r["saved_at"],
                "capture_mode": r["capture_mode"],
                "height_input_cm": r["height_input_cm"],
                "engine_version": r["engine_version"],
                "note": r["note"],
                "key_measurements": {
                    "height_cm": km.get("height_cm") if km.get("height_cm") is not None else r["height_input_cm"],
                    "chest_cm": km.get("chest_cm"),
                    "waist_cm": km.get("waist_cm"),
                    "hip_cm": None if r["capture_mode"] == "upper_body" and km.get("hip_cm") is None else km.get("hip_cm"),
                    "shoulder_width_cm": km.get("shoulder_width_cm"),
                },
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
        }


@router.get("/chart")
def get_chart_data(
    range: Literal["30d", "90d", "all"] = "30d",
    metrics: str = Query("chest_cm,waist_cm,hip_cm,shoulder_width_cm"),
    current_user: dict = Depends(get_current_user),
    db_path: Optional[Union[Path, str]] = None,
):
    """
    Returns chronological timeline points for tracking.
    CRITICAL: Any metric with source in ('template_model', 'unavailable') or value <= 0
    returns valid_for_tracking=False and value=null so MakeHuman template dimensions
    are NOT rendered as real body variance.
    """
    target_keys = [k.strip() for k in metrics.split(",") if k.strip()]
    now = datetime.now(timezone.utc)
    cutoff = None
    if range == "30d":
        cutoff = (now - timedelta(days=30)).isoformat()
    elif range == "90d":
        cutoff = (now - timedelta(days=90)).isoformat()

    conditions = ["user_id = ?"]
    params: list = [current_user["id"]]
    if cutoff:
        conditions.append("captured_at >= ?")
        params.append(cutoff)

    where_clause = " WHERE " + " AND ".join(conditions)

    with get_db_connection(db_path) as conn:
        scans = conn.execute(
            f"""
            SELECT id, captured_at, capture_mode, engine_version
            FROM body_scans
            {where_clause}
            ORDER BY captured_at ASC
            """,
            params,
        ).fetchall()

        timeline = []
        for s in scans:
            sid = s["id"]
            m_rows = conn.execute(
                """
                SELECT metric_key, value_cm, source
                FROM body_measurements
                WHERE body_scan_id = ?
                """,
                (sid,),
            ).fetchall()

            metrics_map = {}
            row_dict = {mr["metric_key"]: mr for mr in m_rows}

            for k in target_keys:
                mr = row_dict.get(k)
                if not mr:
                    metrics_map[k] = {
                        "value": None,
                        "source": "unavailable",
                        "valid_for_tracking": False,
                    }
                    continue

                source = mr["source"]
                raw_val = mr["value_cm"]

                if (
                    source in ("template_model", "unavailable")
                    or raw_val is None
                    or float(raw_val) <= 0
                ):
                    metrics_map[k] = {
                        "value": None,
                        "source": source,
                        "valid_for_tracking": False,
                    }
                else:
                    metrics_map[k] = {
                        "value": raw_val,
                        "source": source,
                        "valid_for_tracking": True,
                    }

            timeline.append({
                "scan_id": sid,
                "captured_at": s["captured_at"],
                "capture_mode": s["capture_mode"],
                "engine_version": s["engine_version"],
                "metrics": metrics_map,
            })

    return {
        "range": range,
        "disclaimer": DISCLAIMER_TEXT,
        "timeline": timeline,
    }


@router.get("/compare")
def compare_scans(
    scan_a: str = Query(...),
    scan_b: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db_path: Optional[Union[Path, str]] = None,
):
    """
    Compares two scans, computes deltas, identifies compatibility issues,
    and produces neutral mathematical summaries without body judgment.
    """
    with get_db_connection(db_path) as conn:
        a_row = conn.execute(
            "SELECT * FROM body_scans WHERE id = ? AND user_id = ?",
            (scan_a, current_user["id"]),
        ).fetchone()

        b_row = conn.execute(
            "SELECT * FROM body_scans WHERE id = ? AND user_id = ?",
            (scan_b, current_user["id"]),
        ).fetchone()

        if not a_row or not b_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy một trong hai lần scan để so sánh.",
            )

        a_measurements = {
            r["metric_key"]: (r["value_cm"], r["source"])
            for r in conn.execute(
                "SELECT metric_key, value_cm, source FROM body_measurements WHERE body_scan_id = ?",
                (scan_a,),
            ).fetchall()
        }

        b_measurements = {
            r["metric_key"]: (r["value_cm"], r["source"])
            for r in conn.execute(
                "SELECT metric_key, value_cm, source FROM body_measurements WHERE body_scan_id = ?",
                (scan_b,),
            ).fetchall()
        }

    compatibility_warnings = []
    if a_row["capture_mode"] != b_row["capture_mode"]:
        compatibility_warnings.append(
            f"Không đồng nhất chế độ chụp ({a_row['capture_mode']} và {b_row['capture_mode']}). "
            "Các số đo có thể không tương thích để so sánh trực tiếp."
        )

    if a_row["engine_version"] != b_row["engine_version"]:
        compatibility_warnings.append(
            f"Khác phiên bản engine ({a_row['engine_version']} và {b_row['engine_version']}). "
            "Thuật toán ước lượng có thể đã thay đổi."
        )

    all_keys = list(LABEL_MAP.keys())
    # Also include any keys present in either measurement dict
    for k in list(a_measurements.keys()) + list(b_measurements.keys()):
        if k not in all_keys:
            all_keys.append(k)

    comparisons = []
    for k in all_keys:
        a_data = a_measurements.get(k)
        b_data = b_measurements.get(k)
        label = LABEL_MAP.get(k, k)

        val_a, src_a = a_data if a_data else (None, "unavailable")
        val_b, src_b = b_data if b_data else (None, "unavailable")

        if val_a is not None and val_b is not None:
            delta = round(val_b - val_a, 1)
            # If either measurement came from MakeHuman template, delta is meaningless
            if src_a == "template_model" or src_b == "template_model":
                comparisons.append({
                    "metric_key": k,
                    "label": label,
                    "value_a_cm": val_a,
                    "value_b_cm": val_b,
                    "delta_cm": None,
                    "source_a": src_a,
                    "source_b": src_b,
                    "is_comparable": False,
                    "summary_text": f"{label} sử dụng số đo mẫu template_model, không có cơ sở so sánh biến thiên cơ thể.",
                })
            else:
                sign = "+" if delta > 0 else ""
                summary_text = (
                    f"{label} thay đổi {sign}{delta} cm giữa hai lần ước lượng."
                    if delta != 0
                    else f"{label} không thay đổi giữa hai lần ước lượng."
                )
                comparisons.append({
                    "metric_key": k,
                    "label": label,
                    "value_a_cm": val_a,
                    "value_b_cm": val_b,
                    "delta_cm": delta,
                    "source_a": src_a,
                    "source_b": src_b,
                    "is_comparable": True,
                    "summary_text": summary_text,
                })
        else:
            comparisons.append({
                "metric_key": k,
                "label": label,
                "value_a_cm": val_a,
                "value_b_cm": val_b,
                "delta_cm": None,
                "source_a": src_a,
                "source_b": src_b,
                "is_comparable": False,
                "summary_text": f"{label} không đủ dữ liệu ở cả hai lần scan để so sánh.",
            })

    return {
        "scan_a": {
            "id": a_row["id"],
            "captured_at": a_row["captured_at"],
            "capture_mode": a_row["capture_mode"],
            "engine_version": a_row["engine_version"],
            "note": a_row["note"],
        },
        "scan_b": {
            "id": b_row["id"],
            "captured_at": b_row["captured_at"],
            "capture_mode": b_row["capture_mode"],
            "engine_version": b_row["engine_version"],
            "note": b_row["note"],
        },
        "compatibility_warnings": compatibility_warnings,
        "comparisons": comparisons,
        "disclaimer": DISCLAIMER_TEXT,
    }


@router.get("/{scan_id}")
def get_scan_by_id(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
    db_path: Optional[Union[Path, str]] = None,
):
    """Fetches details of a specific saved body scan."""
    with get_db_connection(db_path) as conn:
        return fetch_scan_detail(scan_id, current_user["id"], conn)


@router.patch("/{scan_id}")
def update_scan_note(
    scan_id: str,
    req: UpdateScanRequest,
    current_user: dict = Depends(get_current_user),
    db_path: Optional[Union[Path, str]] = None,
):
    """Updates the user note for a saved scan."""
    with get_db_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT id FROM body_scans WHERE id = ? AND user_id = ?",
            (scan_id, current_user["id"]),
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Không tìm thấy lần scan.")

        conn.execute(
            "UPDATE body_scans SET note = ? WHERE id = ?",
            (req.note, scan_id),
        )
        conn.commit()

        return fetch_scan_detail(scan_id, current_user["id"], conn)


@router.delete("/{scan_id}", status_code=status.HTTP_200_OK)
def delete_saved_scan(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
    db_path: Optional[Union[Path, str]] = None,
):
    """Deletes a saved scan and cascaded measurements."""
    with get_db_connection(db_path) as conn:
        res = conn.execute(
            "DELETE FROM body_scans WHERE id = ? AND user_id = ?",
            (scan_id, current_user["id"]),
        )
        conn.commit()

        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy lần scan.")

    return {"success": True, "message": "Đã xóa lần scan thành công."}
