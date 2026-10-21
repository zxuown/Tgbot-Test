"""Notification service handling safe delivery and Telegram errors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter

from app.db.repositories.user_repo import UserRepository
from app.services.digest_service import DigestService

if TYPE_CHECKING:
    from aiogram import Bot
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Delivers scheduled and immediate notifications via Telegram Bot API."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.digest_service = DigestService(session)

    async def send_message_safe(
        self,
        bot: Bot,
        telegram_id: int,
        text: str,
        reply_markup: Any = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """Send message safely, handling Telegram errors without failing."""
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return True
        except TelegramForbiddenError:
            logger.info("User %s blocked the bot. Marking as blocked.", telegram_id)
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if user:
                await self.user_repo.update_user(user, is_blocked=True)
            return False
        except TelegramRetryAfter as exc:
            logger.warning("Rate limit hit while sending to %s. Retry after %ss.", telegram_id, exc.retry_after)
            return False
        except TelegramNetworkError as exc:
            logger.warning("Telegram network error sending to %s: %s", telegram_id, exc)
            return False
        except Exception as exc:
            logger.error("Failed to send message to %s: %s", telegram_id, type(exc).__name__)
            return False

    async def send_digest(self, bot: Bot, user: User, digest_type: str = "morning") -> bool:
        """Build and send a morning or evening digest to user."""
        if user.is_blocked:
            return False

        if digest_type == "morning":
            text = await self.digest_service.build_morning_digest(user)
        else:
            text = await self.digest_service.build_evening_digest(user)

        return await self.send_message_safe(bot, user.telegram_id, text)
