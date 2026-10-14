"""Unit and integration tests for authentication, scan history, permissions, chart, and comparison APIs."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import secrets
import sqlite3
import time

from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.db import get_db_connection, run_migrations
from backend.app.history import persist_scan_snapshot


def create_photo_bytes(color: str = "white") -> bytes:
    output = BytesIO()
    Image.new("RGB", (200, 300), color).save(output, format="JPEG")
    return output.getvalue()


@pytest.fixture
def test_app_and_db(tmp_path, monkeypatch):
    """Sets up an isolated database and storage for each test."""
    db_file = tmp_path / "test_auth_history.db"
    run_migrations(db_file)
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setenv("MORPH_ORDERS_DB", str(db_file))
    monkeypatch.setattr(main, "readiness", lambda: (True, "Ready"))

    def fake_reconstruct(front, side, height, path, report, capture_mode="full_body"):
        report("testing")
        path.write_bytes(b"glTF-test-only")
        return (
            ["test only"],
            {"height_cm": height, "chest_cm": 95.0, "waist_cm": 75.0, "hip_cm": 100.0, "inseam_cm": None},
            {"fit_status": "matched", "validation": "not_validated", "measurement_details": []}
        )

    monkeypatch.setattr(main, "reconstruct", fake_reconstruct)

    # Clear memory jobs
    with main.lock:
        main.jobs.clear()

    return main.app, db_file


def test_auth_register_login_lifecycle_and_profile(test_app_and_db):
    app, db_file = test_app_and_db
    with TestClient(app) as client:
        # 1. Invalid registration inputs
        res_bad_email = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "password123",
            "display_name": "Nguyen Van A",
        })
        assert res_bad_email.status_code == 400

        res_short_pwd = client.post("/api/auth/register", json={
            "email": "user@example.com",
            "password": "123",
            "display_name": "Nguyen Van A",
        })
        assert res_short_pwd.status_code == 400

        res_empty_name = client.post("/api/auth/register", json={
            "email": "user@example.com",
            "password": "password123",
            "display_name": "   ",
        })
        assert res_empty_name.status_code == 400

        # 2. Successful registration
        res_reg = client.post("/api/auth/register", json={
            "email": "user1@morph.test",
            "password": "securepassword123",
            "display_name": "Nguyen Van A",
        })
        assert res_reg.status_code == 201
        reg_data = res_reg.json()
        assert reg_data["user"]["email"] == "user1@morph.test"
        assert reg_data["user"]["display_name"] == "Nguyen Van A"
        assert reg_data["user"]["auto_save_scans"] is True
        assert "morph_session" in client.cookies

        user_id = reg_data["user"]["id"]

        # 3. Duplicate registration
        res_dup = client.post("/api/auth/register", json={
            "email": "USER1@MORPH.TEST",
            "password": "anotherpassword",
            "display_name": "Nguyen Van B",
        })
        assert res_dup.status_code == 409

        # 4. Check me while logged in
        res_me = client.get("/api/auth/me")
        assert res_me.status_code == 200
        assert res_me.json()["user"]["id"] == user_id

        # 5. Update profile
        res_prof = client.patch("/api/auth/profile", json={
            "display_name": "Van A Tran",
            "auto_save_scans": False,
        })
        assert res_prof.status_code == 200
        assert res_prof.json()["user"]["display_name"] == "Van A Tran"
        assert res_prof.json()["user"]["auto_save_scans"] is False

        # 6. Logout
        res_logout = client.post("/api/auth/logout")
        assert res_logout.status_code == 200
        assert res_logout.json()["success"] is True

        # 7. Check me after logout
        res_me_logged_out = client.get("/api/auth/me")
        assert res_me_logged_out.status_code == 200
        assert res_me_logged_out.json()["user"] is None

        # 8. Login with wrong password
        res_wrong = client.post("/api/auth/login", json={
            "email": "user1@morph.test",
            "password": "wrongpassword",
        })
        assert res_wrong.status_code == 401

        # 9. Login with correct password
        res_login = client.post("/api/auth/login", json={
            "email": "user1@morph.test",
            "password": "securepassword123",
        })
        assert res_login.status_code == 200
        assert res_login.json()["user"]["display_name"] == "Van A Tran"
        assert "morph_session" in client.cookies


def test_auth_rate_limiting_lockout(test_app_and_db):
    app, db_file = test_app_and_db
    with TestClient(app) as client:
        # Register user
        client.post("/api/auth/register", json={
            "email": "lockout@morph.test",
            "password": "validpassword",
            "display_name": "Lockout Target",
        })
        client.post("/api/auth/logout")

        # 4 failed login attempts -> all 401
        for _ in range(4):
            res = client.post("/api/auth/login", json={
                "email": "lockout@morph.test",
                "password": "badpassword",
            })
            assert res.status_code == 401

        # 5th failed attempt -> 401, triggers lockout
        res_5 = client.post("/api/auth/login", json={
            "email": "lockout@morph.test",
            "password": "badpassword",
        })
        assert res_5.status_code == 401

        # 6th attempt (even with valid password!) -> 429 Too Many Requests
        res_locked = client.post("/api/auth/login", json={
            "email": "lockout@morph.test",
            "password": "validpassword",
        })
        assert res_locked.status_code == 429
        assert "khóa" in res_locked.json()["detail"].lower()


def test_guest_scan_creation_access_and_user_claim(test_app_and_db):
    app, db_file = test_app_and_db
    with TestClient(app) as guest_client:
        # Create scan as guest
        files = {
            "front": ("front.jpg", create_photo_bytes("white"), "image/jpeg"),
            "side": ("side.jpg", create_photo_bytes("gray"), "image/jpeg"),
        }
        res_scan = guest_client.post("/api/scans", files=files, data={"height_cm": 175, "consent": True})
        assert res_scan.status_code == 202
        scan_info = res_scan.json()
        scan_id = scan_info["id"]
        guest_token = scan_info.get("guest_token")
        assert guest_token is not None
        assert scan_info.get("user_id") is None

        # Access with correct guest token header -> 200
        res_get_valid = guest_client.get(f"/api/scans/{scan_id}", headers={"X-Guest-Token": guest_token})
        assert res_get_valid.status_code == 200

        # Access with wrong guest token header -> 403
        res_get_wrong = guest_client.get(f"/api/scans/{scan_id}", headers={"X-Guest-Token": "invalid_guest_token"})
        assert res_get_wrong.status_code == 403

        # Access and delete WITHOUT guest token -> 403 and job remains intact
        res_get_missing = guest_client.get(f"/api/scans/{scan_id}")
        assert res_get_missing.status_code == 403
        res_del_missing = guest_client.delete(f"/api/scans/{scan_id}")
        assert res_del_missing.status_code == 403
        with main.lock:
            assert scan_id in main.jobs

        # Mark scan completed in memory for saving test
        with main.lock:
            job = main.jobs[scan_id]
            job.status = "completed"
            job.measurements = {"height_cm": 175.0, "chest_cm": 95.0, "waist_cm": 75.0, "hip_cm": 99.0}
            job.body_profile = {
                "measurement_details": [
                    {"key": "height_cm", "label": "Chiều cao", "value_cm": 175.0, "source": "user_input"},
                    {"key": "chest_cm", "label": "Vòng ngực", "value_cm": 95.0, "source": "photo_estimate"},
                    {"key": "waist_cm", "label": "Vòng eo", "value_cm": 75.0, "source": "photo_estimate"},
                    {"key": "hip_cm", "label": "Vòng mông", "value_cm": 99.0, "source": "photo_estimate"},
                ]
            }

        # User registers and claims guest scan
        res_reg = guest_client.post("/api/auth/register", json={
            "email": "claimer@morph.test",
            "password": "password123",
            "display_name": "Claimer",
        })
        user_id = res_reg.json()["user"]["id"]

        # Claim with wrong guest token -> 403
        res_claim_bad = guest_client.post("/api/user/scans/save", json={
            "scan_id": scan_id,
            "guest_token": "wrong_token",
        })
        assert res_claim_bad.status_code == 403

        # Claim with correct guest token -> 200
        res_claim = guest_client.post("/api/user/scans/save", json={
            "scan_id": scan_id,
            "guest_token": guest_token,
            "note": "Claimed guest scan",
        })
        assert res_claim.status_code == 200
        saved_scan = res_claim.json()
        assert saved_scan["source_scan_id"] == scan_id
        assert saved_scan["note"] == "Claimed guest scan"

        # Verify job now belongs to user_id and guest_token was wiped
        with main.lock:
            assert main.jobs[scan_id].user_id == user_id
            assert main.jobs[scan_id].guest_token is None

        # GET /api/scans/{scan_id} as the logged-in owner does not leak guest_token
        res_after_claim = guest_client.get(f"/api/scans/{scan_id}")
        assert res_after_claim.status_code == 200
        assert res_after_claim.json()["guest_token"] is None


def test_user_ownership_and_permission_isolation(test_app_and_db):
    app, db_file = test_app_and_db
    with TestClient(app) as client_a, TestClient(app) as client_b:
        # Register User A
        reg_a = client_a.post("/api/auth/register", json={
            "email": "usera@morph.test",
            "password": "password123",
            "display_name": "User A",
        }).json()
        user_a_id = reg_a["user"]["id"]

        # Register User B
        reg_b = client_b.post("/api/auth/register", json={
            "email": "userb@morph.test",
            "password": "password123",
            "display_name": "User B",
        }).json()
        user_b_id = reg_b["user"]["id"]

        # User A creates a scan
        files = {
            "front": ("front.jpg", create_photo_bytes("white"), "image/jpeg"),
            "side": ("side.jpg", create_photo_bytes("gray"), "image/jpeg"),
        }
        res_scan_a = client_a.post("/api/scans", files=files, data={"height_cm": 170, "consent": True})
        assert res_scan_a.status_code == 202
        scan_a_id = res_scan_a.json()["id"]

        with main.lock:
            job_a = main.jobs[scan_a_id]
            job_a.status = "completed"
            job_a.measurements = {"height_cm": 170.0, "chest_cm": 92.0}

        # User A can access
        assert client_a.get(f"/api/scans/{scan_a_id}").status_code == 200

        # User B CANNOT access User A's scan -> 403
        valid_chart = {
            "name": "Test chart",
            "garment": "top",
            "source": "user_provided",
            "measurement_basis": "body_cm",
            "rows": [{"size": "M", "chest_cm": {"min": 90, "max": 100}, "waist_cm": {"min": 70, "max": 80}}],
        }
        assert client_b.get(f"/api/scans/{scan_a_id}").status_code == 403
        assert client_b.get(f"/api/scans/{scan_a_id}/measurements").status_code == 403
        assert client_b.get(f"/api/scans/{scan_a_id}/model").status_code == 403
        assert client_b.post(f"/api/scans/{scan_a_id}/size-advice", json=valid_chart).status_code == 403
        assert client_b.post("/api/sizing/recommend", json={"chart": valid_chart, "scan_id": scan_a_id}).status_code == 403
        assert client_b.delete(f"/api/scans/{scan_a_id}").status_code == 403

        # User A saves scan to persistent DB
        save_res = client_a.post("/api/user/scans/save", json={"scan_id": scan_a_id, "note": "Private A"})
        assert save_res.status_code == 200
        saved_db_id = save_res.json()["id"]

        # User B CANNOT view, update, or delete User A's saved scan in history -> 404
        assert client_b.get(f"/api/user/scans/{saved_db_id}").status_code == 404
        assert client_b.patch(f"/api/user/scans/{saved_db_id}", json={"note": "Hacked"}).status_code == 404
        assert client_b.delete(f"/api/user/scans/{saved_db_id}").status_code == 404

        # User A CAN view, update, delete
        assert client_a.get(f"/api/user/scans/{saved_db_id}").status_code == 200
        patch_res = client_a.patch(f"/api/user/scans/{saved_db_id}", json={"note": "Updated by A"})
        assert patch_res.status_code == 200
        assert patch_res.json()["note"] == "Updated by A"


def test_idempotent_save_and_null_preservation(test_app_and_db):
    app, db_file = test_app_and_db
    with TestClient(app) as client:
        reg = client.post("/api/auth/register", json={
            "email": "idempotent@morph.test",
            "password": "password123",
            "display_name": "Idempotent User",
        }).json()
        user_id = reg["user"]["id"]

        # Create mock completed job in memory with deliberate NULLs
        job_id = "mock_job_123"
        with main.lock:
            job = main.Job(
                id=job_id,
                user_id=user_id,
                capture_mode="upper_body",
                height_cm=168.0,
                status="completed",
                warnings=["Cảnh báo thân trên: mông lấy từ template"],
                measurements={
                    "height_cm": 168.0,
                    "chest_cm": 91.5,
                    "waist_cm": 72.0,
                    "hip_cm": None,
                    "arm_length_cm": None,
                },
                body_profile={
                    "measurement_details": [
                        {"key": "height_cm", "label": "Chiều cao", "value_cm": 168.0, "source": "user_input"},
                        {"key": "chest_cm", "label": "Vòng ngực", "value_cm": 91.5, "source": "photo_with_prior"},
                        {"key": "waist_cm", "label": "Vòng eo", "value_cm": 72.0, "source": "photo_with_prior"},
                        {"key": "hip_cm", "label": "Vòng mông", "value_cm": None, "source": "template_model"},
                        {"key": "arm_length_cm", "label": "Dài tay", "value_cm": None, "source": "unavailable"},
                    ]
                }
            )
            main.jobs[job_id] = job

        # Save scan 1st time
        res1 = client.post("/api/user/scans/save", json={"scan_id": job_id, "note": "First Save"})
        assert res1.status_code == 200
        data1 = res1.json()
        saved_id = data1["id"]

        # Save scan 2nd time -> idempotent, same DB record
        res2 = client.post("/api/user/scans/save", json={"scan_id": job_id, "note": "Updated Note"})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["id"] == saved_id
        assert data2["note"] == "Updated Note"

        # Verify only 1 record exists in DB
        with get_db_connection(db_file) as conn:
            count = conn.execute("SELECT COUNT(*) FROM body_scans WHERE user_id = ?", (user_id,)).fetchone()[0]
            assert count == 1

            # Check NULL preservation: hip_cm and arm_length_cm MUST be NULL in DB, not 0.0
            null_rows = conn.execute(
                "SELECT metric_key, value_cm, source FROM body_measurements WHERE body_scan_id = ? AND metric_key IN ('hip_cm', 'arm_length_cm')",
                (saved_id,),
            ).fetchall()
            for r in null_rows:
                assert r["value_cm"] is None, f"{r['metric_key']} value_cm must be None/NULL, got {r['value_cm']}"

        # Evict job from RAM (simulate expiration)
        with main.lock:
            main.jobs.pop(job_id, None)

        # Save again when expired from RAM -> returns existing saved DB record
        res3 = client.post("/api/user/scans/save", json={"scan_id": job_id})
        assert res3.status_code == 200
        assert res3.json()["id"] == saved_id

        # Non-existent scan ID -> 404
        res4 = client.post("/api/user/scans/save", json={"scan_id": "non_existent_key_999"})
        assert res4.status_code == 404


def test_chart_api_template_model_exclusion_and_range_filtering(test_app_and_db):
    app, db_file = test_app_and_db
    with TestClient(app) as client:
        reg = client.post("/api/auth/register", json={
            "email": "chart@morph.test",
            "password": "password123",
            "display_name": "Chart User",
        }).json()
        user_id = reg["user"]["id"]

        now = datetime.now(timezone.utc)
        timestamps = [
            (now - timedelta(days=5)).isoformat(),
            (now - timedelta(days=20)).isoformat(),
            (now - timedelta(days=60)).isoformat(),
        ]

        # Insert 3 scans into SQLite:
        # scan 0: 5 days ago (upper_body, hip is template_model)
        # scan 1: 20 days ago (full_body, hip is photo_estimate)
        # scan 2: 60 days ago (full_body)
        with get_db_connection(db_file) as conn:
            for idx, captured_time in enumerate(timestamps):
                sid = f"scan_chart_{idx}"
                mode = "upper_body" if idx == 0 else "full_body"
                conn.execute(
                    """
                    INSERT INTO body_scans (
                        id, user_id, source_scan_id, captured_at, saved_at,
                        capture_mode, height_input_cm, engine_version, measurement_schema_version
                    ) VALUES (?, ?, ?, ?, ?, ?, 172.0, 'mediapipe-two-photo-fit-v4', 1)
                    """,
                    (sid, user_id, f"src_{idx}", captured_time, captured_time, mode),
                )

                # Chest measurement
                conn.execute(
                    "INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)",
                    (f"m_chest_{idx}", sid, "chest_cm", 95.0 + idx, "photo_estimate"),
                )

                # Hip measurement: for upper_body idx 0, source is template_model!
                hip_source = "template_model" if idx == 0 else "photo_estimate"
                hip_val = 98.0 + idx
                conn.execute(
                    "INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)",
                    (f"m_hip_{idx}", sid, "hip_cm", hip_val, hip_source),
                )
            conn.commit()

        # 1. 30d range -> should return scans within 30 days (idx 0 and idx 1)
        res_30d = client.get("/api/user/scans/chart?range=30d&metrics=chest_cm,hip_cm")
        assert res_30d.status_code == 200
        chart_30d = res_30d.json()
        assert len(chart_30d["timeline"]) == 2
        assert "disclaimer" in chart_30d

        # CRITICAL TEST: idx 0 has hip_cm with source="template_model"
        # It MUST return valid_for_tracking=False and value=None!
        scan_0_point = next(pt for pt in chart_30d["timeline"] if pt["scan_id"] == "scan_chart_0")
        hip_0_metric = scan_0_point["metrics"]["hip_cm"]
        assert hip_0_metric["source"] == "template_model"
        assert hip_0_metric["valid_for_tracking"] is False
        assert hip_0_metric["value"] is None

        # idx 1 has hip_cm with source="photo_estimate" -> valid_for_tracking=True, value=99.0
        scan_1_point = next(pt for pt in chart_30d["timeline"] if pt["scan_id"] == "scan_chart_1")
        hip_1_metric = scan_1_point["metrics"]["hip_cm"]
        assert hip_1_metric["source"] == "photo_estimate"
        assert hip_1_metric["valid_for_tracking"] is True
        assert hip_1_metric["value"] == 99.0

        # 2. 90d range -> should return all 3 scans
        res_90d = client.get("/api/user/scans/chart?range=90d&metrics=chest_cm,hip_cm")
        assert res_90d.status_code == 200
        assert len(res_90d.json()["timeline"]) == 3


def test_compare_api_deltas_warnings_and_neutral_summaries(test_app_and_db):
    app, db_file = test_app_and_db
    with TestClient(app) as client:
        reg = client.post("/api/auth/register", json={
            "email": "compare@morph.test",
            "password": "password123",
            "display_name": "Compare User",
        }).json()
        user_id = reg["user"]["id"]

        scan_a_id = "comp_scan_a"
        scan_b_id = "comp_scan_b"

        # Insert scan_a (upper_body) and scan_b (full_body)
        with get_db_connection(db_file) as conn:
            conn.execute(
                """
                INSERT INTO body_scans (
                    id, user_id, source_scan_id, captured_at, saved_at,
                    capture_mode, height_input_cm, engine_version, measurement_schema_version
                ) VALUES (?, ?, ?, '2026-10-01T10:00:00Z', '2026-10-01T10:00:00Z', 'upper_body', 170.0, 'mediapipe-two-photo-fit-v4', 1)
                """,
                (scan_a_id, user_id, "src_a"),
            )
            conn.execute(
                """
                INSERT INTO body_scans (
                    id, user_id, source_scan_id, captured_at, saved_at,
                    capture_mode, height_input_cm, engine_version, measurement_schema_version
                ) VALUES (?, ?, ?, '2026-10-10T10:00:00Z', '2026-10-10T10:00:00Z', 'full_body', 170.0, 'mediapipe-two-photo-fit-v4', 1)
                """,
                (scan_b_id, user_id, "src_b"),
            )

            # Measurements for A
            conn.execute(
                "INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)",
                ("ma_waist", scan_a_id, "waist_cm", 75.0, "photo_with_prior"),
            )
            conn.execute(
                "INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)",
                ("ma_hip", scan_a_id, "hip_cm", None, "template_model"),
            )

            # Measurements for B
            conn.execute(
                "INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)",
                ("mb_waist", scan_b_id, "waist_cm", 73.8, "photo_estimate"),
            )
            conn.execute(
                "INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)",
                ("mb_hip", scan_b_id, "hip_cm", 98.0, "photo_estimate"),
            )
            conn.commit()

        # Compare scan_a and scan_b
        res_comp = client.get(f"/api/user/scans/compare?scan_a={scan_a_id}&scan_b={scan_b_id}")
        assert res_comp.status_code == 200
        comp_data = res_comp.json()

        # Check mode incompatibility warning
        warnings = comp_data["compatibility_warnings"]
        assert any("Không đồng nhất chế độ chụp" in w for w in warnings)

        # Check waist comparison: 73.8 - 75.0 = -1.2 cm
        waist_comp = next(c for c in comp_data["comparisons"] if c["metric_key"] == "waist_cm")
        assert waist_comp["value_a_cm"] == 75.0
        assert waist_comp["value_b_cm"] == 73.8
        assert waist_comp["delta_cm"] == -1.2
        assert waist_comp["is_comparable"] is True
        assert "Vòng eo thay đổi -1.2 cm giữa hai lần ước lượng." in waist_comp["summary_text"]

        # Check hip comparison: scan_a has source template_model -> NOT comparable
        hip_comp = next(c for c in comp_data["comparisons"] if c["metric_key"] == "hip_cm")
        assert hip_comp["is_comparable"] is False
        assert hip_comp["delta_cm"] is None
        assert "template_model" in hip_comp["summary_text"] or "không đủ dữ liệu" in hip_comp["summary_text"]

        # Check disclaimer exists
        assert "disclaimer" in comp_data


def test_save_scan_urlsafe_token_and_idempotency_scenarios(test_app_and_db):
    app, db_file = test_app_and_db
    with TestClient(app) as client:
        # 1. Create a guest job with secrets.token_urlsafe(24)
        guest_token = secrets.token_urlsafe(24)
        scan_id = "test_urlsafe_job_123"
        with main.lock:
            main.jobs[scan_id] = main.Job(
                id=scan_id,
                guest_token=guest_token,
                user_id=None,
                status="completed",
                measurements={"height_cm": 172.0, "chest_cm": 94.0, "waist_cm": 78.0, "hip_cm": 96.0},
            )

        # 2. Register user
        reg = client.post("/api/auth/register", json={
            "email": "urlsafe_user@morph.test",
            "password": "password123",
            "display_name": "URLSafe User",
        }).json()
        user_id = reg["user"]["id"]

        # 3. Save scan using valid guest_token -> 200
        res_save = client.post("/api/user/scans/save", json={
            "scan_id": scan_id,
            "guest_token": guest_token,
            "note": "Initial Save",
        })
        assert res_save.status_code == 200
        saved_data = res_save.json()
        saved_db_id = saved_data["id"]
        assert saved_data["note"] == "Initial Save"

        # 4. Save scan 2nd time (idempotent, note update) -> 200
        res_save2 = client.post("/api/user/scans/save", json={
            "scan_id": scan_id,
            "note": "Second Save Idempotent",
        })
        assert res_save2.status_code == 200
        assert res_save2.json()["id"] == saved_db_id
        assert res_save2.json()["note"] == "Second Save Idempotent"

        # 5. Evict job from RAM, call save with saved_db_id -> 200 idempotent
        with main.lock:
            main.jobs.pop(scan_id, None)

        res_save3 = client.post("/api/user/scans/save", json={
            "scan_id": saved_db_id,
            "note": "Third Save By DB ID",
        })
        assert res_save3.status_code == 200
        assert res_save3.json()["id"] == saved_db_id
        assert res_save3.json()["note"] == "Third Save By DB ID"


def test_sizing_recommend_with_saved_scan_in_db(test_app_and_db):
    app, db_file = test_app_and_db
    with TestClient(app) as client_owner, TestClient(app) as client_other:
        # Register owner
        reg_owner = client_owner.post("/api/auth/register", json={
            "email": "scan_owner@morph.test",
            "password": "password123",
            "display_name": "Scan Owner",
        }).json()
        owner_id = reg_owner["user"]["id"]

        # Register other user
        client_other.post("/api/auth/register", json={
            "email": "scan_other@morph.test",
            "password": "password123",
            "display_name": "Scan Other",
        })

        # Create and save a scan in DB for owner
        scan_id = "job_for_db_recommend"
        with main.lock:
            main.jobs[scan_id] = main.Job(
                id=scan_id,
                user_id=owner_id,
                status="completed",
                measurements={"height_cm": 175.0, "chest_cm": 95.0, "waist_cm": 79.0, "hip_cm": 98.0},
            )

        save_res = client_owner.post("/api/user/scans/save", json={"scan_id": scan_id})
        assert save_res.status_code == 200
        saved_db_id = save_res.json()["id"]

        # Evict from RAM so recommendation MUST query SQLite body_measurements
        with main.lock:
            main.jobs.pop(scan_id, None)

        # 1. Owner requests recommendation with saved_scan_id and real product
        p_list = client_owner.get("/api/products").json()
        prod = p_list[0]
        prod_slug = prod["slug"]

        rec_res = client_owner.post("/api/sizing/recommend", json={
            "product_slug": prod_slug,
            "saved_scan_id": saved_db_id,
        })
        assert rec_res.status_code == 200
        rec_data = rec_res.json()
        assert rec_data["product_slug"] == prod_slug
        assert "comparisons" in rec_data
        assert len(rec_data["comparisons"]) > 0

        # 2. Other user tries to use owner's saved_scan_id -> 403 Forbidden
        other_rec = client_other.post("/api/sizing/recommend", json={
            "product_slug": prod_slug,
            "saved_scan_id": saved_db_id,
        })
        assert other_rec.status_code == 403


def test_safe_redirect_validation_and_auth_continuation(test_app_and_db):
    """Verifies that return_to is validated against open redirects, protocols, and auth loops."""
    app, _ = test_app_and_db
    with TestClient(app) as client:
        # Safe paths preserved
        assert client.get("/api/auth/validate-redirect?return_to=/cart").json()["safe_url"] == "/cart"
        assert client.get("/api/auth/validate-redirect?return_to=/checkout").json()["safe_url"] == "/checkout"
        assert client.get("/api/auth/validate-redirect?return_to=/products/ao-thun-essential").json()["safe_url"] == "/products/ao-thun-essential"

        # Protocol-relative, external, backslash bypasses rejected -> fallback to /account
        assert client.get("/api/auth/validate-redirect?return_to=//evil.com").json()["safe_url"] == "/account"
        assert client.get("/api/auth/validate-redirect?return_to=https://evil.com").json()["safe_url"] == "/account"
        assert client.get(r"/api/auth/validate-redirect?return_to=/\evil.com").json()["safe_url"] == "/account"
        assert client.get("/api/auth/validate-redirect?return_to=/auth/login").json()["safe_url"] == "/account"
        assert client.get("/api/auth/validate-redirect?return_to=/auth/register").json()["safe_url"] == "/account"

        # Register and login return sanitized return_to
        reg_res = client.post("/api/auth/register", json={
            "email": "redirect_user@morph.test",
            "password": "password123",
            "display_name": "Redirect User",
            "return_to": "/cart",
        })
        assert reg_res.status_code == 201
        assert reg_res.json()["return_to"] == "/cart"

        login_res = client.post("/api/auth/login", json={
            "email": "redirect_user@morph.test",
            "password": "password123",
            "return_to": "/checkout",
        })
        assert login_res.status_code == 200
        assert login_res.json()["return_to"] == "/checkout"


def test_save_scan_with_x_guest_token_header(test_app_and_db):
    """Verifies that guest scan can be claimed and saved using X-Guest-Token header."""
    app, _ = test_app_and_db
    with TestClient(app) as client:
        guest_token = secrets.token_urlsafe(24)
        scan_id = "job_guest_header_claim"
        with main.lock:
            main.jobs[scan_id] = main.Job(
                id=scan_id,
                guest_token=guest_token,
                status="completed",
                measurements={"height_cm": 168.0, "chest_cm": 88.0, "waist_cm": 70.0, "hip_cm": 92.0},
            )

        client.post("/api/auth/register", json={
            "email": "header_user@morph.test",
            "password": "password123",
            "display_name": "Header User",
        })

        # Save with header X-Guest-Token
        res = client.post(
            "/api/user/scans/save",
            json={"scan_id": scan_id},
            headers={"X-Guest-Token": guest_token},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["source_scan_id"] == scan_id


def test_saved_upper_body_scan_with_template_model_hip_never_recommends_bottom_or_hip_dress(test_app_and_db):
    """
    Acceptance criterion #2:
    A saved upper_body scan in DB where hip_cm has value_cm = 94.5 (non-null) and
    source = 'template_model' MUST return status == 'insufficient_measurements' and
    'hip_cm' in missing when recommending size for bottom or dress requiring hip_cm,
    and list_scans must not expose template_model hip_cm in key_measurements.
    """
    app, _ = test_app_and_db
    with TestClient(app) as client:
        reg = client.post("/api/auth/register", json={
            "email": "upper_template_hip@morph.test",
            "password": "password123",
            "display_name": "Upper Template Hip User",
        }).json()
        user_id = reg["user"]["id"]

        scan_id = "upper_job_with_template_hip"
        with main.lock:
            main.jobs[scan_id] = main.Job(
                id=scan_id,
                user_id=user_id,
                capture_mode="upper_body",
                height_cm=170.0,
                status="completed",
                measurements={
                    "height_cm": 170.0,
                    "chest_cm": 92.0,
                    "waist_cm": 74.0,
                    "hip_cm": None,
                },
                body_profile={
                    "capture_mode": "upper_body",
                    "measurement_details": [
                        {"key": "height_cm", "label": "Chiều cao", "value_cm": 170.0, "source": "user_input"},
                        {"key": "chest_cm", "label": "Vòng ngực", "value_cm": 92.0, "source": "photo_with_prior"},
                        {"key": "waist_cm", "label": "Vòng eo", "value_cm": 74.0, "source": "photo_with_prior"},
                        {"key": "hip_cm", "label": "Vòng mông", "value_cm": 94.5, "source": "template_model"},
                    ],
                },
            )

        save_res = client.post("/api/user/scans/save", json={"scan_id": scan_id})
        assert save_res.status_code == 200
        saved_db_id = save_res.json()["id"]

        # Verify list_scans does NOT expose template_model hip_cm in key_measurements
        list_res = client.get("/api/user/scans")
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert len(items) == 1
        assert items[0]["key_measurements"]["chest_cm"] == 92.0
        assert items[0]["key_measurements"]["waist_cm"] == 74.0
        assert items[0]["key_measurements"]["hip_cm"] is None

        # Evict in-memory job so /api/sizing/recommend reads directly from DB body_measurements
        with main.lock:
            main.jobs.pop(scan_id, None)

        bottom_chart = {
            "name": "Quần Âu Test",
            "garment": "bottom",
            "source": "illustrative",
            "measurement_basis": "body_cm",
            "rows": [
                {"size": "M", "waist_cm": {"min": 70, "max": 78}, "hip_cm": {"min": 90, "max": 98}},
            ],
        }
        rec_bottom = client.post("/api/sizing/recommend", json={
            "chart": bottom_chart,
            "saved_scan_id": saved_db_id,
        })
        assert rec_bottom.status_code == 200
        b_data = rec_bottom.json()
        assert b_data["status"] == "insufficient_measurements"
        assert "hip_cm" in b_data["missing"]
        assert b_data["candidates"] == []

        dress_with_hip_chart = {
            "name": "Đầm Ôm Test",
            "garment": "dress",
            "source": "illustrative",
            "measurement_basis": "body_cm",
            "rows": [
                {
                    "size": "M",
                    "chest_cm": {"min": 88, "max": 96},
                    "waist_cm": {"min": 70, "max": 78},
                    "hip_cm": {"min": 90, "max": 98},
                },
            ],
        }
        rec_dress = client.post("/api/sizing/recommend", json={
            "chart": dress_with_hip_chart,
            "scan_id": scan_id,  # resolved via source_scan_id in DB
        })
        assert rec_dress.status_code == 200
        d_data = rec_dress.json()
        assert d_data["status"] == "insufficient_measurements"
        assert "hip_cm" in d_data["missing"]
        assert d_data["candidates"] == []


def test_sizing_recommend_memory_vs_db_parity_upper_and_full_body(test_app_and_db):
    """
    Acceptance criterion #3:
    Comparing POST /api/sizing/recommend while the job is in memory (jobs[scan_id])
    vs after the job is evicted from memory (jobs.pop(scan_id)) and read from DB
    (body_scans with source_scan_id = scan_id):
    For both top and bottom charts across both upper_body and full_body scans,
    both must return the exact same status, candidates, and missing!
    """
    app, _ = test_app_and_db
    with TestClient(app) as client:
        reg = client.post("/api/auth/register", json={
            "email": "parity@morph.test",
            "password": "password123",
            "display_name": "Parity User",
        }).json()
        user_id = reg["user"]["id"]

        top_chart = {
            "name": "Áo Sơ Mi Parity",
            "garment": "top",
            "source": "illustrative",
            "measurement_basis": "body_cm",
            "rows": [
                {"size": "S", "chest_cm": {"min": 84, "max": 90}, "waist_cm": {"min": 68, "max": 74}},
                {"size": "M", "chest_cm": {"min": 90, "max": 96}, "waist_cm": {"min": 74, "max": 80}},
            ],
        }
        bottom_chart = {
            "name": "Quần Tây Parity",
            "garment": "bottom",
            "source": "illustrative",
            "measurement_basis": "body_cm",
            "rows": [
                {"size": "29", "waist_cm": {"min": 68, "max": 74}, "hip_cm": {"min": 88, "max": 94}},
                {"size": "30", "waist_cm": {"min": 74, "max": 80}, "hip_cm": {"min": 94, "max": 100}},
            ],
        }

        scenarios = [
            (
                "upper_parity_job",
                "upper_body",
                {"height_cm": 170.0, "chest_cm": 93.0, "waist_cm": 76.0, "hip_cm": None},
                [
                    {"key": "height_cm", "label": "Chiều cao", "value_cm": 170.0, "source": "user_input"},
                    {"key": "chest_cm", "label": "Vòng ngực", "value_cm": 93.0, "source": "photo_with_prior"},
                    {"key": "waist_cm", "label": "Vòng eo", "value_cm": 76.0, "source": "photo_with_prior"},
                    {"key": "hip_cm", "label": "Vòng mông", "value_cm": 96.0, "source": "template_model"},
                ],
            ),
            (
                "full_parity_job",
                "full_body",
                {"height_cm": 170.0, "chest_cm": 93.0, "waist_cm": 76.0, "hip_cm": 96.0},
                [
                    {"key": "height_cm", "label": "Chiều cao", "value_cm": 170.0, "source": "user_input"},
                    {"key": "chest_cm", "label": "Vòng ngực", "value_cm": 93.0, "source": "photo_estimate"},
                    {"key": "waist_cm", "label": "Vòng eo", "value_cm": 76.0, "source": "photo_estimate"},
                    {"key": "hip_cm", "label": "Vòng mông", "value_cm": 96.0, "source": "photo_estimate"},
                ],
            ),
        ]

        for scan_id, mode, meas, details in scenarios:
            with main.lock:
                main.jobs[scan_id] = main.Job(
                    id=scan_id,
                    user_id=user_id,
                    capture_mode=mode,
                    height_cm=170.0,
                    status="completed",
                    measurements=meas,
                    body_profile={"capture_mode": mode, "measurement_details": details},
                )

            # Save to DB while still in memory
            save_res = client.post("/api/user/scans/save", json={"scan_id": scan_id})
            assert save_res.status_code == 200

            # 1. Query while in memory
            mem_top = client.post("/api/sizing/recommend", json={"chart": top_chart, "scan_id": scan_id}).json()
            mem_bottom = client.post("/api/sizing/recommend", json={"chart": bottom_chart, "scan_id": scan_id}).json()

            # 2. Evict from memory and query again using the same scan_id (resolved via source_scan_id in DB)
            with main.lock:
                main.jobs.pop(scan_id, None)

            db_top = client.post("/api/sizing/recommend", json={"chart": top_chart, "scan_id": scan_id}).json()
            db_bottom = client.post("/api/sizing/recommend", json={"chart": bottom_chart, "scan_id": scan_id}).json()

            for mem_res, db_res in [(mem_top, db_top), (mem_bottom, db_bottom)]:
                assert mem_res["status"] == db_res["status"]
                assert mem_res["candidates"] == db_res["candidates"]
                assert mem_res.get("missing") == db_res.get("missing")


