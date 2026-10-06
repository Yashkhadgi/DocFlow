from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_not_found_error_format() -> None:
    response = client.get("/api/v1/nonexistent-route-for-testing")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"
    assert data["error"]["message"] == "Not Found"


def test_validation_error_format() -> None:
    response = client.post("/api/v1/auth/login", json={"email": "invalid"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"
