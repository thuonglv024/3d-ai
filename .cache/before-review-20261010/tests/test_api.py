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
        return ["test only"]

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
        for _ in range(100):
            status = client.get(f"/api/scans/{key}").json()
            if status["status"] == "completed":
                break
            time.sleep(.01)
        assert status["status"] == "completed"
        model = client.get(status["model_url"])
        assert model.content == b"glTF-test-only"
        assert model.headers["cache-control"] == "no-store"
        assert client.get("/api/scans/does-not-exist/model").status_code == 404
        assert client.delete(f"/api/scans/{key}").status_code == 204
        assert client.get(f"/api/scans/{key}").status_code == 404
        assert not list(tmp_path.glob("*.glb"))
