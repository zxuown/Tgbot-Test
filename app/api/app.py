"""FastAPI application factory, middleware, CORS, and unified error handling."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.ai import router as ai_router
from app.api.routes.habits import router as habits_router
from app.api.routes.health import router as health_router
from app.api.routes.me import router as me_router
from app.api.routes.settings import router as settings_router
from app.api.routes.stats import router as stats_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.today import router as today_router
from app.api.routes.webhook import router as webhook_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.session import close_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager: startup and shutdown logic."""
    setup_logging(get_settings().LOG_LEVEL)
    logger.info("FastAPI application starting up...")
    yield
    logger.info("FastAPI application shutting down...")
    await close_engine()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Фокус — AI-органайзер API",
        description="REST API and Mini App backend for Focus productivity coach.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 1. CORS Middleware (allows Telegram WebApp to query from any origin/webview)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Centralized Exception Handlers (Strictly unified format)
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            error_body = detail
        elif isinstance(detail, dict) and "code" in detail and "message" in detail:
            error_body = {"error": detail}
        else:
            error_body = {
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(detail),
                }
            }
        return JSONResponse(status_code=exc.status_code, content=error_body)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Внутренняя ошибка сервера. Пожалуйста, попробуйте позже.",
                }
            },
        )

    # 3. Mount API Routers
    app.include_router(health_router)
    app.include_router(me_router)
    app.include_router(tasks_router)
    app.include_router(habits_router)
    app.include_router(stats_router)
    app.include_router(today_router)
    app.include_router(ai_router)
    app.include_router(settings_router)

    # 4. Mount Telegram Webhook router
    settings = get_settings()
    app.include_router(webhook_router, prefix=settings.WEBHOOK_PATH)

    # 5. Mount Mini App static assets if directory exists
    miniapp_dir = Path(__file__).resolve().parent.parent.parent / "miniapp"
    if (miniapp_dir / "public").exists():
        app.mount("/app", StaticFiles(directory=str(miniapp_dir / "public"), html=True), name="miniapp")
    if (miniapp_dir / "src").exists():
        app.mount("/src", StaticFiles(directory=str(miniapp_dir / "src")), name="miniapp_src")

    return app


app = create_app()
