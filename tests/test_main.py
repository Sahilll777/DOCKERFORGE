from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "application": "DOCKERFORGE",
        "status": "running",
        "version": "0.1.0",
    }


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
    }


def test_openapi_endpoint():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    data = response.json()

    assert data["info"]["title"] == "DOCKERFORGE"
    assert data["info"]["version"] == "0.1.0"
    assert "/" in data["paths"]
    assert "/health" in data["paths"]