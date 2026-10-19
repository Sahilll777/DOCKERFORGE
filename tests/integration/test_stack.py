import os

import httpx
import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("DOCKERFORGE_INTEGRATION") != "1",
    reason="Set DOCKERFORGE_INTEGRATION=1 to run live stack tests.",
)

BASE_URL = os.getenv("DOCKERFORGE_BASE_URL", "http://localhost:8088")
PROMETHEUS_URL = os.getenv(
    "DOCKERFORGE_PROMETHEUS_URL",
    "http://localhost:9092",
)


def test_nginx_reaches_api_health():
    response = httpx.get(f"{BASE_URL}/health", timeout=10)

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_real_postgresql_connection():
    response = httpx.get(f"{BASE_URL}/db-health", timeout=10)

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "dockerforge"
    assert data["user"] == "dockerforge"


def test_redis_cache_hit_on_repeated_request():
    first = httpx.get(f"{BASE_URL}/cache-demo", timeout=10)
    second = httpx.get(f"{BASE_URL}/cache-demo", timeout=10)

    assert first.status_code == 200
    assert second.status_code == 200

    first_data = first.json()
    second_data = second.json()

    assert first_data["database"] == "dockerforge"
    assert first_data["user"] == "dockerforge"
    assert second_data["cached"] is True
    assert second_data["generated_at"] == first_data["generated_at"]


def test_prometheus_reports_api_target_up():
    response = httpx.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        params={"query": 'up{job="dockerforge-api"}'},
        timeout=10,
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "success"

    results = payload["data"]["result"]
    assert any(
        result["metric"].get("instance") == "api:8000"
        and result["value"][1] == "1"
        for result in results
    )