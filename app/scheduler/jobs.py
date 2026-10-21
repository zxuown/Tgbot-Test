"""Background scheduled jobs for morning/evening digests and focus timers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.bot.keyboards import focus_end_keyboard
from app.db.models.focus_session import FocusSession
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db_session
from app.i18n.texts import Texts
from app.services.notification_service import NotificationService
from app.utils.helpers import get_user_now

if TYPE_CHECKING:
    from aiogram import Bot

logger = logging.getLogger(__name__)


async def morning_digest_job(bot: Bot) -> None:
    """Check each user's local time and send morning digest when due."""
    try:
        async with get_db_session() as session:
            user_repo = UserRepository(session)
            users = await user_repo.get_all_active_users_with_settings()
            notif_service = NotificationService(session)

            for user in users:
                s = user.settings
                if not s or not s.morning_digest_enabled or s.notifications_paused:
                    continue

                user_local_now = get_user_now(user.timezone)
                current_hhmm = user_local_now.strftime("%H:%M")

                if current_hhmm == s.morning_digest_time:
                    logger.info("Sending morning digest to user %s (time: %s)", user.id, current_hhmm)
                    await notif_service.send_digest(bot, user, digest_type="morning")
    except Exception as exc:
        logger.error("Error running morning_digest_job: %s", exc)


async def evening_digest_job(bot: Bot) -> None:
    """Check each user's local time and send evening reflection when due."""
    try:
        async with get_db_session() as session:
            user_repo = UserRepository(session)
            users = await user_repo.get_all_active_users_with_settings()
            notif_service = NotificationService(session)

            for user in users:
                s = user.settings
                if not s or not s.evening_digest_enabled or s.notifications_paused:
                    continue

                user_local_now = get_user_now(user.timezone)
                current_hhmm = user_local_now.strftime("%H:%M")

                if current_hhmm == s.evening_digest_time:
                    logger.info("Sending evening digest to user %s (time: %s)", user.id, current_hhmm)
                    await notif_service.send_digest(bot, user, digest_type="evening")
    except Exception as exc:
        logger.error("Error running evening_digest_job: %s", exc)


async def focus_timer_job(bot: Bot) -> None:
    """Check expired active focus sessions and send completion prompt."""
    try:
        async with get_db_session() as session:
            stmt = select(FocusSession).where(
                FocusSession.finished_at.is_(None),
                FocusSession.is_completed == False,
            )
            result = await session.execute(stmt)
            sessions = list(result.scalars().all())

            now = datetime.now(UTC)
            user_repo = UserRepository(session)
            notif_service = NotificationService(session)

            for fs in sessions:
                started_at = fs.started_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=UTC)
                elapsed_minutes = (now - started_at).total_seconds() / 60
                if elapsed_minutes >= fs.duration_minutes:
                    user = await user_repo.get_by_id(fs.user_id)
                    if user and not user.is_blocked:
                        msg = Texts.FOCUS_ENDED.format(
                            duration=fs.duration_minutes,
                            task="",
                        )
                        kb = focus_end_keyboard(session_id=fs.id, task_id=fs.task_id or 0)
                        await notif_service.send_message_safe(bot, user.telegram_id, msg, reply_markup=kb)

                        # Auto-finish session in DB
                        fs.finished_at = now
                        fs.actual_minutes = int(elapsed_minutes)
                        fs.is_completed = True
                        await session.flush()
    except Exception as exc:
        logger.error("Error running focus_timer_job: %s", exc)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Initialize APScheduler with all scheduled recurring background jobs."""
    scheduler = AsyncIOScheduler()

    # Run check every minute for digests
    scheduler.add_job(
        morning_digest_job,
        trigger=IntervalTrigger(seconds=60),
        args=[bot],
        id="morning_digest_job",
        replace_existing=True,
    )
    scheduler.add_job(
        evening_digest_job,
        trigger=IntervalTrigger(seconds=60),
        args=[bot],
        id="evening_digest_job",
        replace_existing=True,
    )
    # Check focus timers every 30 seconds
    scheduler.add_job(
        focus_timer_job,
        trigger=IntervalTrigger(seconds=30),
        args=[bot],
        id="focus_timer_job",
        replace_existing=True,
    )

    return scheduler
