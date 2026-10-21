"""Health-check and readiness endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from redis.asyncio import Redis

from app.api.schemas import HealthResponse
from app.core.config import get_settings
from app.db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple liveness probe — always returns ok."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Deep readiness probe — checks DB and Redis connectivity."""
    db_status = "ok"
    redis_status = "ok"

    # Check database
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception as exc:
        logger.warning("Database readiness check failed: %s", exc)
        db_status = "error"

    # Check Redis
    try:
        settings = get_settings()
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await redis.ping()
        finally:
            await redis.aclose()
    except Exception as exc:
        logger.warning("Redis readiness check failed: %s", exc)
        redis_status = "error"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return HealthResponse(status=overall, database=db_status, redis=redis_status)
