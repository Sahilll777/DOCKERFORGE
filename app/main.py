from fastapi import FastAPI

from app.database import check_database_connection


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