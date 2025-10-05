import importlib
from fastapi.testclient import TestClient

def test_import_and_health():
    m = importlib.import_module("app.main")
    assert hasattr(m, "app")
    client = TestClient(m.app)
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["health"] == "ok"

def test_root_ok():
    m = importlib.import_module("app.main")
    client = TestClient(m.app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
