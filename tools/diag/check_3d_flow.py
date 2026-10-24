"""Diagnose the scan -> 3D-model endpoint chain. Read-only, no production edits.

Usage:
    backend/.venv/Scripts/python.exe tools/diag/check_3d_flow.py --base http://127.0.0.1:8000
Optional: --engine-label v7 (recorded in the report; the server determines the real engine).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "verification" / "scripts" / "qa"
FIELDS_FRONTEND_JOB = {"id", "status", "stage", "model_url", "measurements", "body_profile", "warnings", "guest_token", "revision", "overrides", "user_id"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--engine-label", default="auto")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    front = QA / "rendered-front.png"
    side = QA / "rendered-side.png"

    with httpx.Client(base_url=base, timeout=60) as client:
        health = client.get("/api/health")
        print("health", health.status_code, health.json().get("engine"), health.json().get("ready"))
        t0 = time.perf_counter()
        with front.open("rb") as f1, side.open("rb") as f2:
            r = client.post(
                "/api/scans",
                files={"front": ("front.png", f1, "image/png"), "side": ("side.png", f2, "image/png")},
                data={"height_cm": "172", "consent": "true", "capture_mode": "full_body", "sex": "auto"},
            )
        post_time = time.perf_counter() - t0
        print("POST /api/scans", r.status_code, f"{post_time:.2f}s", json.dumps(r.json(), ensure_ascii=False)[:500])
        if r.status_code != 202:
            return 2
        created = r.json()
        key, token = created["id"], created["guest_token"]
        job = created
        deadline = time.time() + 60
        while time.time() < deadline:
            time.sleep(1)
            job = client.get(f"/api/scans/{key}", params={"guest_token": token}).json()
            if job.get("status") in {"completed", "failed"}:
                break
        print("GET job", job.get("status"), "elapsed", job.get("elapsed_seconds"), "keys", sorted(job))
        print("missing-vs-Job-type", sorted(FIELDS_FRONTEND_JOB - set(job)))
        if job.get("status") != "completed":
            return 3
        model_url = job.get("model_url")
        print("model_url", model_url)
        if model_url:
            t0 = time.perf_counter()
            m = client.get(model_url, params={"guest_token": token})
            print("GET model", m.status_code, f"{time.perf_counter()-t0:.2f}s", len(m.content), m.content[:4])
        print("measurements", json.dumps(job.get("measurements"), ensure_ascii=False))
        print("body_profile_keys", sorted((job.get("body_profile") or {}).keys()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
