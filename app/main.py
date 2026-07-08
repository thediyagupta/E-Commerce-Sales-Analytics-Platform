from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis
import logging

from app.config import settings
from app.routers import revenue, cohort, rfm, delivery, sellers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("olist-api")

app = FastAPI(
    title="Olist E-Commerce Analytics API",
    description="REST API exposing SQL-heavy analytics (window functions, "
                 "CTEs, cohort/RFM analysis) over the Olist Brazilian "
                 "e-commerce dataset, with Redis-cached aggregations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before any real deployment
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(revenue.router)
app.include_router(cohort.router)
app.include_router(rfm.router)
app.include_router(delivery.router)
app.include_router(sellers.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs."},
    )


@app.get("/health")
async def health_check():
    """Checks both Postgres and Redis connectivity -- useful for
    catching 'API is up but DB/cache is down' failures, which are
    the most common real-world failure mode for this kind of service."""
    status = {"api": "ok", "database": "unknown", "redis": "unknown"}

    try:
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error: {str(e)}"

    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"

    overall_ok = status["database"] == "ok" and status["redis"] == "ok"
    return JSONResponse(status_code=200 if overall_ok else 503, content=status)


@app.get("/")
async def root():
    return {
        "message": "Olist E-Commerce Analytics API",
        "docs": "/docs",
        "health": "/health",
    }
