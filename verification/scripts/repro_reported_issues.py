"""
Reproduction and Verification of Reported Issues:
1. Guest scan token bypass in check_scan_access
2. Missing token access vs invalid token access
3. Delete scan unauthorized access
"""
import sys
import os
import secrets
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import DATA, app, jobs, Job, lock

print("=" * 60)
print("TEST SUITE: GUEST SCAN ACCESS TOKEN VERIFICATION")
print("=" * 60)

with TestClient(app) as client:
    # Set up a guest scan with a valid guest_token and a mock .glb file on disk
    token = secrets.token_urlsafe(24)
    scan_id = f"repro_guest_{secrets.token_hex(4)}"
    DATA.mkdir(exist_ok=True, parents=True)
    glb_path = DATA / f"{scan_id}.glb"
    glb_path.write_bytes(b"glTF-repro-test")
    try:
        with lock:
            jobs[scan_id] = Job(
                id=scan_id,
                guest_token=token,
                user_id=None,
                status="completed",
                measurements={"height_cm": 175.0, "chest_cm": 95.0, "waist_cm": 80.0},
            )

        print(f"\n[SETUP] Created guest scan: {scan_id}")
        print(f"[SETUP] Authoritative guest_token: {token}")

        # Case 1: Access WITH valid token
        res_valid = client.get(f"/api/scans/{scan_id}", headers={"X-Guest-Token": token})
        print(f"\n1. GET /api/scans/{scan_id} with VALID token:")
        print(f"   Status Code: {res_valid.status_code}")
        assert res_valid.status_code == 200, f"Expected 200, got {res_valid.status_code}"
        print("   -> PASSED (200 OK as expected)")

        # Case 2: Access WITH invalid token
        res_invalid = client.get(f"/api/scans/{scan_id}", headers={"X-Guest-Token": "bad_token_xyz"})
        print(f"\n2. GET /api/scans/{scan_id} with INVALID token:")
        print(f"   Status Code: {res_invalid.status_code}")
        assert res_invalid.status_code == 403, f"Expected 403, got {res_invalid.status_code}"
        print("   -> PASSED (403 Forbidden as expected)")

        # Case 3: Access WITHOUT token (Previously bypassed access check)
        res_no_token = client.get(f"/api/scans/{scan_id}")
        print(f"\n3. GET /api/scans/{scan_id} WITHOUT ANY token:")
        print(f"   Status Code: {res_no_token.status_code}")
        assert res_no_token.status_code == 403, f"Expected 403, got {res_no_token.status_code}"
        print("   -> PASSED (403 Forbidden - Missing token blocked as expected)")

        # Case 4: DELETE scan WITHOUT token (Destructive unauthorized action)
        res_delete_no_token = client.delete(f"/api/scans/{scan_id}")
        print(f"\n4. DELETE /api/scans/{scan_id} WITHOUT ANY token:")
        print(f"   Status Code: {res_delete_no_token.status_code}")
        assert res_delete_no_token.status_code == 403, f"Expected 403, got {res_delete_no_token.status_code}"
        with lock:
            still_exists = scan_id in jobs
        assert still_exists is True, "Expected job to remain in memory after blocked DELETE"
        assert glb_path.is_file(), "Expected .glb file on disk to remain intact after blocked DELETE"
        print(f"   -> PASSED (403 Forbidden - Scan and .glb protected, scan_id in jobs: {still_exists})")

        # Case 5: Sizing recommend with target_scan_id WITHOUT token
        res_sizing_no_token = client.post("/api/sizing/recommend", json={
            "scan_id": scan_id,
            "chart": {
                "name": "Test chart",
                "garment": "top",
                "source": "user_provided",
                "measurement_basis": "body_cm",
                "rows": [{"size": "M", "chest_cm": {"min": 90, "max": 100}, "waist_cm": {"min": 75, "max": 85}}],
            },
        })
        print(f"\n5. POST /api/sizing/recommend with target_scan_id WITHOUT token:")
        print(f"   Status Code: {res_sizing_no_token.status_code}")
        assert res_sizing_no_token.status_code == 403, f"Expected 403, got {res_sizing_no_token.status_code}"
        print("   -> PASSED (403 Forbidden - Sizing recommendation blocked without token)")
    finally:
        with lock:
            jobs.pop(scan_id, None)
        glb_path.unlink(missing_ok=True)

print("\n" + "=" * 60)
print("ALL SECURITY VERIFICATION TESTS PASSED")
print("=" * 60)


