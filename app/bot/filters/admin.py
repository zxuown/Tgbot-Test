"""Admin filter checking administrator Telegram IDs."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.core.config import get_settings


class AdminFilter(BaseFilter):
    """Filter that matches only if user is listed in ADMIN_TELEGRAM_IDS."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if not user:
            return False
        admin_ids = get_settings().admin_ids
        return user.id in admin_ids
