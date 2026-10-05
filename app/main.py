import json

from fastapi import FastAPI

from app.database import check_database_connection, get_cache_demo_data
from app.redis import get_cached_value, set_cached_value


app = FastAPI(
    title="DOCKERFORGE",
    description="Production-Grade Multi-Container Application Orchestration Platform",
    version="0.1.0",
)


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

            return {
                **data,
                "cached": True,
                "cache_key": cache_key,
            }

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

    except Exception:
        data = get_cache_demo_data()

        return {
            **data,
            "cached": False,
            "cache_key": cache_key,
            "cache_status": "bypass",
        }
