from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_live_health():
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ready_health():
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
