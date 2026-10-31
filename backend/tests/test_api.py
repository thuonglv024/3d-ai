from io import BytesIO
import time
from PIL import Image
from fastapi.testclient import TestClient
from app import main


def photo(color):
    output = BytesIO()
    Image.new("RGB", (300, 500), color).save(output, format="JPEG")
    return output.getvalue()


def test_validation_lifecycle_and_deletion(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "readiness", lambda: (True, "Ready"))

    def fake_reconstruct(front, side, height, path, report, capture_mode="full_body", sex="auto"):
        report("testing")
        path.write_bytes(b"glTF-test-only")
        return ["test only"], {"height_cm": height, "chest_cm": 95, "waist_cm": 75, "hip_cm": 100, "inseam_cm": None}, {"fit_status": "matched", "validation": "not_validated"}

    monkeypatch.setattr(main, "reconstruct", fake_reconstruct)
    with TestClient(main.app) as client:
        assert client.get("/api/health").json()["ready"]
        files = {"front": ("front.jpg", photo("white"), "image/jpeg"), "side": ("side.jpg", photo("gray"), "image/jpeg")}
        assert client.post("/api/scans", files=files, data={"height_cm": 170}).status_code == 400
        duplicate = {"front": files["front"], "side": files["front"]}
        assert client.post("/api/scans", files=duplicate, data={"height_cm": 170, "consent": True}).status_code == 400
        assert client.post("/api/scans", files=files, data={"height_cm": 0, "consent": True}).status_code == 422
        response = client.post("/api/scans", files=files, data={"height_cm": 170, "consent": True})
        assert response.status_code == 202
        key = response.json()["id"]
        guest_token = response.json()["guest_token"]
        headers = {"X-Guest-Token": guest_token}
        for _ in range(100):
            status = client.get(f"/api/scans/{key}", headers=headers).json()
            if status["status"] == "completed":
                break
            time.sleep(.01)
        assert status["status"] == "completed"
        assert status["measurements"]["inseam_cm"] is None
        chart = {"name": "Test chart", "garment": "top", "source": "user_provided", "measurement_basis": "body_cm", "rows": [{"size": "M", "chest_cm": {"min": 90, "max": 100}, "waist_cm": {"min": 70, "max": 80}}]}
        # Verify requests WITHOUT guest_token are rejected with 403
        assert client.get(f"/api/scans/{key}").status_code == 403
        assert client.get(f"/api/scans/{key}/measurements").status_code == 403
        assert client.get(f"/api/scans/{key}/model").status_code == 403
        assert client.post(f"/api/scans/{key}/size-advice", json=chart).status_code == 403
        assert client.delete(f"/api/scans/{key}").status_code == 403
        exported = client.get(f"/api/scans/{key}/measurements", headers=headers)
        assert exported.status_code == 200
        assert exported.json()["unit"] == "cm"
        assert exported.json()["body_fit"]["validation"] == "not_validated"
        advice = client.post(f"/api/scans/{key}/size-advice", json=chart, headers=headers)
        assert advice.json()["candidates"] == ["M"]
        assert advice.json()["chart_source"] == "user_provided"
        assert client.post(f"/api/scans/{key}/size-advice", json={}, headers=headers).status_code == 422
        model = client.get(status["model_url"], headers=headers)
        assert model.content == b"glTF-test-only"
        assert model.headers["cache-control"] == "no-store"
        assert client.get("/api/scans/does-not-exist/model").status_code == 404
        assert client.delete(f"/api/scans/{key}", headers=headers).status_code == 204
        assert client.get(f"/api/scans/{key}", headers=headers).status_code == 404
        assert client.get(f"/api/scans/{key}/measurements", headers=headers).status_code == 404
        assert client.post(f"/api/scans/{key}/size-advice", json=chart, headers=headers).status_code == 404
        assert not list(tmp_path.glob("*.glb"))


def test_hung_job_timeout_and_max_stored_jobs_eviction(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DATA", tmp_path)
    now = time.time()

    with main.lock:
        main.jobs.clear()
        # 1. Create a hung processing job (> 120s old) with a partial .glb file
        hung_key = "hung_job_001"
        (tmp_path / f"{hung_key}.glb").write_bytes(b"partial-glb")
        main.jobs[hung_key] = main.Job(
            id=hung_key,
            status="processing",
            created=now - (main.JOB_PROCESSING_TIMEOUT_SECONDS + 10),
            guest_token="hung_token",
        )

    main.cleanup()

    with main.lock:
        assert main.jobs[hung_key].status == "failed"
        assert main.jobs[hung_key].finished is not None
        assert "quá thời gian chờ" in (main.jobs[hung_key].error or "").lower()
        assert not (tmp_path / f"{hung_key}.glb").exists()
        # Queue slot is now free (0 queued/processing jobs)
        assert sum(j.status in {"queued", "processing"} for j in main.jobs.values()) == 0

        # 2. Test MAX_STORED_JOBS cap on finished jobs
        main.jobs.clear()
        for idx in range(main.MAX_STORED_JOBS + 5):
            jid = f"finished_job_{idx:03d}"
            (tmp_path / f"{jid}.glb").write_bytes(b"glTF")
            main.jobs[jid] = main.Job(
                id=jid,
                status="completed",
                created=now - 300 + idx,
                finished=now - 10,
                guest_token=f"tok_{idx}",
            )

    main.cleanup()

    with main.lock:
        assert len(main.jobs) == main.MAX_STORED_JOBS
        # Oldest 5 jobs (000..004) should be evicted along with their .glb files
        for idx in range(5):
            jid = f"finished_job_{idx:03d}"
            assert jid not in main.jobs
            assert not (tmp_path / f"{jid}.glb").exists()
        for idx in range(5, main.MAX_STORED_JOBS + 5):
            jid = f"finished_job_{idx:03d}"
            assert jid in main.jobs
            assert (tmp_path / f"{jid}.glb").exists()
        main.jobs.clear()
