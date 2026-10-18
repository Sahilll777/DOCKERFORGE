
import json
import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

from app.database import check_database_connection, get_cache_demo_data
from app.redis import get_cached_value, set_cached_value


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger("dockerforge.api")

HTTP_REQUESTS_TOTAL = Counter(
    "dockerforge_http_requests_total",
    "Total HTTP requests handled by the DOCKERFORGE API.",
    ["method", "route", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "dockerforge_http_request_duration_seconds",
    "HTTP request processing duration in seconds.",
    ["method", "route"],
)


app = FastAPI(
    title="DOCKERFORGE",
    description="Production-Grade Multi-Container Application Orchestration Platform",
    version="0.1.0",
)


@app.middleware("http")
async def record_http_metrics(request: Request, call_next):
    # Avoid counting Prometheus scrapes as application traffic.
    if request.url.path == "/metrics":
        return await call_next(request)

    start_time = time.perf_counter()
    status_code = "500"

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    finally:
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            route=route_path,
            status_code=status_code,
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            route=route_path,
        ).observe(time.perf_counter() - start_time)


@app.get("/")
def root():
    return {
        "application": "DOCKERFORGE",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.get("/db-health")
def database_health():
    database, user = check_database_connection()

    logger.info("Database health check succeeded")

    return {
        "status": "healthy",
        "database": database,
        "user": user,
    }


@app.get("/cache-demo")
def cache_demo():
    cache_key = "dockerforge:cache-demo"

    try:
        cached_value = get_cached_value(cache_key)

        if cached_value:
            data = json.loads(cached_value)
            logger.info("Cache hit")

            return {
                **data,
                "cached": True,
                "cache_key": cache_key,
            }

        logger.info("Cache miss")
        data = get_cache_demo_data()

        set_cached_value(
            cache_key,
            json.dumps(data),
        )

        return {
            **data,
            "cached": False,
            "cache_key": cache_key,
        }

    except Exception as exc:
        logger.warning(
            "Cache operation failed; using database fallback "
            "(error_type=%s)",
            type(exc).__name__,
        )

        data = get_cache_demo_data()

        return {
            **data,
            "cached": False,
            "cache_key": cache_key,
            "cache_status": "bypass",
        }


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(
        content=generate_latest(),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )
