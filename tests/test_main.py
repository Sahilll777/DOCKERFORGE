import json
import os

from fastapi.testclient import TestClient


os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://dockerforge:local_test_password@localhost:5432/dockerforge",
)
os.environ.setdefault(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

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


def test_database_health_endpoint(monkeypatch):
    monkeypatch.setattr(
        "app.main.check_database_connection",
        lambda: ("dockerforge", "dockerforge"),
    )

    response = client.get("/db-health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "dockerforge",
        "user": "dockerforge",
    }


def test_cache_miss(monkeypatch):
    data = {
        "database": "dockerforge",
        "user": "dockerforge",
        "generated_at": "2026-01-01T00:00:00+00:00",
    }
    saved = {}

    monkeypatch.setattr("app.main.get_cached_value", lambda key: None)
    monkeypatch.setattr("app.main.get_cache_demo_data", lambda: data)
    monkeypatch.setattr(
        "app.main.set_cached_value",
        lambda key, value: saved.update({key: json.loads(value)}),
    )

    response = client.get("/cache-demo")

    assert response.status_code == 200
    assert response.json()["cached"] is False
    assert response.json()["cache_key"] == "dockerforge:cache-demo"
    assert saved["dockerforge:cache-demo"] == data


def test_cache_hit(monkeypatch):
    data = {
        "database": "dockerforge",
        "user": "dockerforge",
        "generated_at": "2026-01-01T00:00:00+00:00",
    }

    monkeypatch.setattr(
        "app.main.get_cached_value",
        lambda key: json.dumps(data),
    )
    monkeypatch.setattr(
        "app.main.get_cache_demo_data",
        lambda: (_ for _ in ()).throw(AssertionError("Database should not be called")),
    )

    response = client.get("/cache-demo")

    assert response.status_code == 200
    assert response.json()["cached"] is True
    assert response.json()["database"] == "dockerforge"


def test_cache_failure_uses_database_fallback(monkeypatch):
    data = {
        "database": "dockerforge",
        "user": "dockerforge",
        "generated_at": "2026-01-01T00:00:00+00:00",
    }

    def fail_cache(key):
        raise ConnectionError("simulated cache failure")

    monkeypatch.setattr("app.main.get_cached_value", fail_cache)
    monkeypatch.setattr("app.main.get_cache_demo_data", lambda: data)

    response = client.get("/cache-demo")

    assert response.status_code == 200
    assert response.json()["cached"] is False
    assert response.json()["cache_status"] == "bypass"
    assert response.json()["database"] == "dockerforge"


def test_openapi_endpoint():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    data = response.json()

    assert data["info"]["title"] == "DOCKERFORGE"
    assert data["info"]["version"] == "0.1.0"
    assert "/" in data["paths"]
    assert "/health" in data["paths"]
    assert "/db-health" in data["paths"]
    assert "/cache-demo" in data["paths"]
