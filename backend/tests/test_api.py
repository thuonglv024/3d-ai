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

    def fake_reconstruct(front, side, height, path, report):
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
