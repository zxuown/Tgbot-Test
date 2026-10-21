"""Main entry point for Focus Telegram bot and API application in cloud and local environments."""

from __future__ import annotations

import asyncio
import contextlib
import signal
import sys
from typing import Any

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.api.app import create_app
from app.api.routes.webhook import set_webhook_bot_and_dispatcher
from app.bot.handlers import get_main_router
from app.bot.middlewares import (
    DbSessionMiddleware,
    MaintenanceMiddleware,
    ThrottlingMiddleware,
    UserMiddleware,
)
from app.core.config import ConfigurationError, get_settings
from app.core.logging import get_logger, setup_logging
from app.db.migrations import run_migrations
from app.db.session import close_engine
from app.scheduler.jobs import setup_scheduler

logger = get_logger(__name__)


async def get_fsm_storage(redis_url: str):
    """Attempt Redis storage with connection test, fallback to MemoryStorage."""
    try:
        redis = Redis.from_url(redis_url, socket_connect_timeout=2.0)
        await redis.ping()
        logger.info("Connected to Redis for FSM storage: %s", redis_url)
        return RedisStorage(redis=redis)
    except Exception as exc:
        logger.warning("Redis unavailable for FSM (%s), falling back to MemoryStorage", exc)
        return MemoryStorage()


def build_dispatcher(storage: Any) -> Dispatcher:
    """Build and configure Aiogram Dispatcher with routers and middlewares."""
    settings = get_settings()
    dp = Dispatcher(storage=storage)

    # Register Middlewares
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(UserMiddleware())
    dp.update.outer_middleware(MaintenanceMiddleware())
    dp.message.middleware(ThrottlingMiddleware(rate_limit=settings.RATE_LIMIT_MESSAGES_PER_MINUTE))

    # Include Handlers Router
    dp.include_router(get_main_router())
    return dp


async def main() -> None:
    """Run Telegram bot and/or API according to BOT_MODE."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    settings = get_settings()
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
        app_env=settings.APP_ENV,
    )

    # 1. Validate Configuration
    try:
        settings.validate_config()
    except ConfigurationError as exc:
        logger.error(str(exc))
        sys.exit(1)

    logger.info(
        "Starting Focus application",
        env=settings.APP_ENV,
        mode=settings.BOT_MODE,
        port=settings.server_port,
        ai_provider=settings.AI_PROVIDER,
    )

    # 2. Run Database Migrations if enabled
    if settings.AUTO_MIGRATE:
        try:
            run_migrations()
        except Exception as exc:
            logger.error("Database migration failed: %s", exc)
            if settings.is_production:
                sys.exit(1)

    # 3. Mode: API Only (No bot)
    if settings.BOT_MODE == "api":
        logger.info("Running in API-only mode on %s:%s", settings.API_HOST, settings.server_port)
        app = create_app()
        config = uvicorn.Config(
            app=app,
            host=settings.API_HOST,
            port=settings.server_port,
            log_level=settings.LOG_LEVEL.lower(),
            access_log=settings.is_development,
        )
        server = uvicorn.Server(config)
        await server.serve()
        return

    # 4. Initialize Bot & Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    storage = await get_fsm_storage(settings.REDIS_URL)
    dp = build_dispatcher(storage=storage)

    # 5. Start APScheduler
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Background scheduler started.")

    stop_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Received termination signal. Initiating graceful shutdown...")
        stop_event.set()

    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

    try:
        # 6. Mode: Webhook
        if settings.BOT_MODE == "webhook":
            webhook_url = f"{settings.WEBHOOK_URL.rstrip('/')}{settings.WEBHOOK_PATH}"
            logger.info("Setting Telegram Webhook: %s", webhook_url)
            await bot.set_webhook(
                url=webhook_url,
                secret_token=settings.WEBHOOK_SECRET,
                drop_pending_updates=True,
            )
            set_webhook_bot_and_dispatcher(bot, dp)

            app = create_app()
            config = uvicorn.Config(
                app=app,
                host=settings.API_HOST,
                port=settings.server_port,
                log_level=settings.LOG_LEVEL.lower(),
                access_log=settings.is_development,
            )
            server = uvicorn.Server(config)
            await server.serve()

        # 7. Mode: Pure Worker (Polling only, no HTTP server)
        elif settings.BOT_MODE == "worker" or not settings.RUN_API_WITH_POLLING:
            logger.info("Starting bot in pure Polling Worker mode...")
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot, handle_signals=False)

        # 8. Mode: Polling + Web API (Combined cloud runner for Web Services like Render/Railway)
        else:
            logger.info(
                "Starting combined Polling Bot + Healthcheck API on port %s...",
                settings.server_port,
            )
            await bot.delete_webhook(drop_pending_updates=True)

            app = create_app()
            config = uvicorn.Config(
                app=app,
                host=settings.API_HOST,
                port=settings.server_port,
                log_level=settings.LOG_LEVEL.lower(),
                access_log=False,
            )
            server = uvicorn.Server(config)

            # Run both polling and server concurrently
            await asyncio.gather(
                server.serve(),
                dp.start_polling(bot, handle_signals=False),
            )

    except asyncio.CancelledError:
        logger.info("Main execution task cancelled.")
    finally:
        logger.info("Performing cleanup and graceful shutdown...")
        with contextlib.suppress(Exception):
            if settings.BOT_MODE == "webhook":
                await bot.delete_webhook()

        with contextlib.suppress(Exception):
            scheduler.shutdown(wait=False)

        with contextlib.suppress(Exception):
            await bot.session.close()

        with contextlib.suppress(Exception):
            await close_engine()

        logger.info("Focus application gracefully stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application process terminated.")
