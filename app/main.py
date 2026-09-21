from fastapi import FastAPI


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