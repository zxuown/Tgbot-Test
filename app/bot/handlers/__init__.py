"""Handlers registration module."""

from __future__ import annotations

from aiogram import Router

from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.ai import router as ai_router
from app.bot.handlers.focus import router as focus_router
from app.bot.handlers.habits import router as habits_router
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.settings import router as settings_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.stats import router as stats_router
from app.bot.handlers.tasks import router as tasks_router
from app.bot.handlers.today import router as today_router
from app.bot.handlers.voice import router as voice_router


def get_main_router() -> Router:
    """Create and configure the main root router with all sub-routers."""
    main_router = Router(name="main_router")

    # Order matters: specific commands and admin first, fallbacks later
    main_router.include_router(admin_router)
    main_router.include_router(start_router)
    main_router.include_router(menu_router)
    main_router.include_router(today_router)
    main_router.include_router(tasks_router)
    main_router.include_router(habits_router)
    main_router.include_router(focus_router)
    main_router.include_router(ai_router)
    main_router.include_router(voice_router)
    main_router.include_router(stats_router)
    main_router.include_router(settings_router)

    return main_router


__all__ = ["get_main_router"]
