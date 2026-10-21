"""Statistics command handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n.texts import Texts
from app.services.analytics_service import AnalyticsService
from app.utils.helpers import format_minutes

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

router = Router(name="stats")


@router.message(Command("stats"))
@router.message(F.text == Texts.BTN_STATS)
async def cmd_stats(message: Message, user: User, session: AsyncSession) -> None:
    """Show user productivity statistics."""
    analytics = AnalyticsService(session)
    s = await analytics.get_user_stats(user.id)

    focus_mins = s["focus_week"].get("total_minutes", 0) if isinstance(s["focus_week"], dict) else 0
    focus_sessions = s["focus_week"].get("sessions_count", 0) if isinstance(s["focus_week"], dict) else 0

    text = (
        Texts.STATS_HEADER
        + Texts.STATS_TASKS.format(
            total=s["tasks_total"],
            completed=s["tasks_completed"],
            in_progress=s["tasks_active"],
            overdue=s["tasks_overdue"],
        )
        + Texts.STATS_HABITS.format(
            active=s["habits_total"],
            best_streak=0,
            week_completions=s["habits_week_completions"],
        )
        + Texts.STATS_FOCUS.format(
            sessions=focus_sessions,
            total_time=format_minutes(focus_mins),
        )
        + f"\n💎 <b>Тариф:</b> {s['subscription_tier'].upper()}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В меню", callback_data="act_main_menu")
    await message.answer(text, reply_markup=builder.as_markup())
