"""Middlewares for database session, user injection, maintenance and throttling."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.config import get_settings
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db_session
from app.i18n.texts import Texts

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _extract_from_user(event: TelegramObject, data: dict[str, Any]) -> Any:
    """Extract Telegram user from event, update or aiogram data context."""
    user = data.get("event_from_user")
    if user:
        return user
    if hasattr(event, "from_user") and getattr(event, "from_user", None):
        return event.from_user
    if hasattr(event, "event") and hasattr(event.event, "from_user"):
        return getattr(event.event, "from_user", None)
    for attr in ("message", "callback_query", "inline_query", "chosen_inline_result", "my_chat_member", "chat_member"):
        sub = getattr(event, attr, None)
        if sub and getattr(sub, "from_user", None):
            return sub.from_user
    return None


class DbSessionMiddleware(BaseMiddleware):
    """Injects an AsyncSession into handler data and handles commits/rollbacks."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with get_db_session() as session:
            data["session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Retrieves or creates User from DB and passes it to handler data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = _extract_from_user(event, data)
        session: AsyncSession | None = data.get("session")

        if from_user and session:
            repo = UserRepository(session)
            user = await repo.get_by_telegram_id(from_user.id)

            if not user:
                user = await repo.create(
                    telegram_id=from_user.id,
                    username=from_user.username,
                    first_name=from_user.first_name,
                    last_name=from_user.last_name,
                    language=from_user.language_code or "ru",
                )
            else:
                await repo.update_last_active(user.id)

            data["user"] = user

        return await handler(event, data)


class MaintenanceMiddleware(BaseMiddleware):
    """Blocks non-admin requests when maintenance mode is active."""

    is_maintenance: bool = False

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not self.is_maintenance:
            return await handler(event, data)

        from_user = _extract_from_user(event, data)
        admin_ids = get_settings().admin_ids

        if from_user and from_user.id in admin_ids:
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer(Texts.MAINTENANCE_MODE)
        elif isinstance(event, CallbackQuery):
            await event.answer(Texts.MAINTENANCE_MODE, show_alert=True)
        elif hasattr(event, "message") and event.message:
            await event.message.answer(Texts.MAINTENANCE_MODE)
        elif hasattr(event, "callback_query") and event.callback_query:
            await event.callback_query.answer(Texts.MAINTENANCE_MODE, show_alert=True)
        return None


class ThrottlingMiddleware(BaseMiddleware):
    """In-memory rate limiting to prevent spam and flooding."""

    def __init__(self, rate_limit: int = 30, window_seconds: int = 60) -> None:
        self.rate_limit = rate_limit
        self.window = window_seconds
        self.user_requests: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = _extract_from_user(event, data)
        if not from_user:
            return await handler(event, data)

        now = time.time()
        requests = self.user_requests[from_user.id]

        # Prune older than window
        self.user_requests[from_user.id] = [t for t in requests if now - t < self.window]

        if len(self.user_requests[from_user.id]) >= self.rate_limit:
            if isinstance(event, Message):
                await event.answer("⚠️ Слишком много сообщений. Пожалуйста, подождите минуту.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⚠️ Подождите немного.", show_alert=False)
            elif hasattr(event, "message") and event.message:
                await event.message.answer("⚠️ Слишком много сообщений. Пожалуйста, подождите минуту.")
            elif hasattr(event, "callback_query") and event.callback_query:
                await event.callback_query.answer("⚠️ Подождите немного.", show_alert=False)
            return None

        self.user_requests[from_user.id].append(now)
        return await handler(event, data)
