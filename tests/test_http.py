from fastapi.testclient import TestClient

from app import db
from app.main import app


def test_state_change_requires_app_header():
    db.connect(":memory:")
    client = TestClient(app)
    assert client.post("/api/items/1/reject").status_code == 403
    assert client.post("/api/items/1/reject", headers={"X-Action-Graph": "1"}).status_code == 404


def test_untrusted_host_rejected():
    client = TestClient(app)
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
