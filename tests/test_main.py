import json
import os
import uuid

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
        lambda: (_ for _ in ()).throw(
            AssertionError("Database should not be called")
        ),
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


def test_metrics_endpoint():
    # Generate application traffic so the metrics have observations.
    client.get("/")
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "dockerforge_http_requests_total" in response.text
    assert "dockerforge_http_request_duration_seconds" in response.text


def test_unhandled_exception_records_http_500_metric(monkeypatch):
    from prometheus_client import REGISTRY

    from app.main import HTTP_REQUESTS_TOTAL

    route_path = f"/_test-error-{uuid.uuid4().hex}"

    def fail_endpoint():
        raise RuntimeError("simulated endpoint failure")

    app.add_api_route(route_path, fail_endpoint, methods=["GET"])

    try:
        error_client = TestClient(
            app,
            raise_server_exceptions=False,
        )
        response = error_client.get(route_path)

        assert response.status_code == 500

        metric = REGISTRY.get_sample_value(
            "dockerforge_http_requests_total",
            {
                "method": "GET",
                "route": route_path,
                "status_code": "500",
            },
        )

        assert metric is not None
        assert metric >= 1
    finally:
        app.router.routes[:] = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != route_path
        ]
