"""Handler for /today and daily productivity plan."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.security import escape_html
from app.db.models.task import TaskStatus
from app.i18n.texts import Texts
from app.services.digest_service import DigestService
from app.services.habit_service import HabitService
from app.services.task_service import TaskService
from app.utils.helpers import format_date_ru, format_minutes, get_user_today, priority_emoji

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

router = Router(name="today")


def today_action_keyboard() -> InlineKeyboardMarkup:
    """Action buttons for /today view."""
    builder = InlineKeyboardBuilder()
    builder.button(text=Texts.BTN_START_FOCUS, callback_data="act_start_focus")
    builder.button(text=Texts.BTN_ADD_TASK_TODAY, callback_data="act_create_task")
    builder.button(text=Texts.BTN_REBUILD_PLAN, callback_data="act_rebuild_plan")
    builder.button(text=Texts.BTN_SHOW_OVERDUE, callback_data="act_show_overdue")
    builder.button(text=Texts.BTN_EVENING_SUMMARY, callback_data="act_evening_summary")
    builder.button(text="◀️ В главное меню", callback_data="act_main_menu")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


@router.message(Command("today"))
@router.message(F.text == Texts.BTN_TODAY)
@router.callback_query(F.data == "act_plan_day")
async def cmd_today(event: Message | CallbackQuery, user: User, session: AsyncSession) -> None:
    """Display comprehensive plan for today."""
    task_service = TaskService(session)
    habit_service = HabitService(session)

    today = get_user_today(user.timezone)
    date_str = format_date_ru(today)

    # 1. Main Focus
    main_focus = user.goal_30_days or "Завершить ключевые задачи и сохранить энергию"

    # 2. Tasks for today
    today_tasks = await task_service.get_today_tasks(user.id)
    overdue_tasks = await task_service.get_overdue_tasks(user.id)

    tasks_text = ""
    total_planned_mins = 0
    completed_count = 0

    if today_tasks:
        lines = []
        for i, t in enumerate(today_tasks, 1):
            p_emo = priority_emoji(t.priority)
            dur = f" — {format_minutes(t.estimated_minutes)}" if t.estimated_minutes else ""
            status_mark = "<s>" if t.status == TaskStatus.COMPLETED.value else ""
            status_end = "</s>" if t.status == TaskStatus.COMPLETED.value else ""
            lines.append(f"{i}. {p_emo} {status_mark}{escape_html(t.title)}{status_end}{dur}")

            if t.estimated_minutes and t.status != TaskStatus.COMPLETED.value:
                total_planned_mins += t.estimated_minutes
            if t.status == TaskStatus.COMPLETED.value:
                completed_count += 1
        tasks_text = Texts.TODAY_TASKS + "\n".join(lines) + "\n"
    else:
        tasks_text = Texts.TODAY_TASKS + "• Нет запланированных задач на сегодня.\n"

    # 3. Habits
    habits = await habit_service.get_habits(user.id, active_only=True)
    habits_text = ""
    if habits:
        h_lines = [f"• 🔄 {escape_html(h.title)}" for h in habits[:4]]
        habits_text = Texts.TODAY_HABITS + "\n".join(h_lines) + "\n"

    # 4. Summary
    planned_str = format_minutes(total_planned_mins) if total_planned_mins > 0 else "0 мин"
    summary_text = Texts.TODAY_SUMMARY.format(
        planned_time=planned_str,
        completed=completed_count,
        total=len(today_tasks),
        overdue=len(overdue_tasks),
    )

    full_text = (
        Texts.TODAY_HEADER.format(date=date_str)
        + Texts.TODAY_MAIN_FOCUS.format(focus=escape_html(main_focus))
        + tasks_text
        + habits_text
        + summary_text
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(full_text, reply_markup=today_action_keyboard())
        await event.answer()
    else:
        await event.answer(full_text, reply_markup=today_action_keyboard())


@router.callback_query(F.data == "act_rebuild_plan")
async def cb_rebuild_plan(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """Use AI to suggest an optimized day plan."""
    from app.services.ai_service import AIService
    ai = AIService()
    plan = await ai.plan_day("Оптимизируй мой рабочий день с учётом привычек и главных задач")
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к плану", callback_data="act_plan_day")
    await callback.message.edit_text(plan, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "act_evening_summary")
async def cb_evening_summary(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """Show evening summary."""
    digest = DigestService(session)
    text = await digest.build_evening_digest(user)
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к плану", callback_data="act_plan_day")
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "act_show_overdue")
async def cb_show_overdue(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """Show overdue tasks directly."""
    from app.bot.handlers.tasks import _show_task_list
    await _show_task_list(callback.message, user, session, filter_type="overdue", page=1, is_edit=True)
    await callback.answer()
