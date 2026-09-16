from fastapi.testclient import TestClient

from app.main import app


def test_context_endpoint_preserves_unavailable_state(monkeypatch):
    monkeypatch.setattr("app.main.get_basin_context", lambda *_: {
        "status": "unavailable",
        "message": "datasets pending",
        "missing_datasets": ["hydrobasins", "hydrorivers"],
        "limitations": ["context only"],
    })
    response = TestClient(app).get("/api/basins/context?latitude=13&longitude=80")
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["missing_datasets"] == ["hydrobasins", "hydrorivers"]


def test_context_endpoint_rejects_invalid_coordinate():
    response = TestClient(app).get("/api/basins/context?latitude=91&longitude=80")
    assert response.status_code == 422
