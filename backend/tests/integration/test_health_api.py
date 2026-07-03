from fastapi.testclient import TestClient

from src.main import app


def test_health_endpoint_returns_runtime_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "pipeline",
    }


def test_root_endpoint_is_not_registered() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 404
