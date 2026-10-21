"""Digest service for morning planning and evening reflection messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.db.models.task import TaskPriority, TaskStatus
from app.db.repositories.focus_repo import FocusSessionRepository
from app.db.repositories.habit_repo import HabitRepository
from app.db.repositories.task_repo import TaskRepository
from app.i18n.texts import Texts
from app.utils.helpers import format_date_ru, format_minutes, get_user_today, priority_emoji

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

_MOTIVATIONAL_QUOTES = [
    "Фокус — это умение сказать «нет» сотне других хороших идей.",
    "Маленькие ежедневные победы приводят к грандиозным результатам.",
    "Секрет продуктивности не в том, чтобы делать больше, а в том, чтобы делать главное.",
    "Начни с самого важного шага — всё остальное приложится.",
    "Дисциплина — это мост между целями и достижениями.",
    "Сделай сегодняшний день шагом к своей главной цели.",
    "Не жди идеального момента, возьми этот момент и сделай его идеальным.",
]


class DigestService:
    """Builds personalized morning and evening digests."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.task_repo = TaskRepository(session)
        self.habit_repo = HabitRepository(session)
        self.focus_repo = FocusSessionRepository(session)

    async def build_morning_digest(self, user: User) -> str:
        """Construct morning digest message for user."""
        today = get_user_today(user.timezone)
        formatted_date = format_date_ru(today)
        name = user.display_name or user.first_name or "друг"

        # Goal section
        goal_text = ""
        if user.goal_30_days:
            goal_text = f"🎯 <b>Главная цель месяца:</b>\n<i>«{user.goal_30_days}»</i>\n"

        # Tasks for today (up to 3 high priority)
        tasks = await self.task_repo.get_today_tasks(user.id)
        important_tasks = sorted(
            [t for t in tasks if t.status != TaskStatus.COMPLETED.value],
            key=lambda t: (0 if t.priority == TaskPriority.URGENT.value else 1 if t.priority == TaskPriority.HIGH.value else 2),
        )[:3]

        if important_tasks:
            task_lines = []
            for i, t in enumerate(important_tasks, 1):
                p_emoji = priority_emoji(t.priority)
                dur = f" ({format_minutes(t.estimated_minutes)})" if t.estimated_minutes else ""
                time_str = f" в {t.due_time.strftime('%H:%M')}" if t.due_time else ""
                task_lines.append(f"{i}. {p_emoji} <b>{t.title}</b>{time_str}{dur}")
            tasks_section = "\n".join(task_lines)
        else:
            tasks_section = "• Задач с жёстким дедлайном на сегодня нет. Самое время запланировать важные дела!"

        # Habits for today
        habits = await self.habit_repo.get_user_habits(user.id)
        if habits:
            habit_lines = []
            for h in habits[:4]:
                streak = f" (серия: {h.current_streak} дн.)" if h.current_streak > 0 else ""
                habit_lines.append(f"• 🔄 {h.title}{streak}")
            habits_section = "\n🔄 <b>Привычки на сегодня:</b>\n" + "\n".join(habit_lines) + "\n"
        else:
            habits_section = ""

        # Motivational quote
        quote_index = today.toordinal() % len(_MOTIVATIONAL_QUOTES)
        motivation = _MOTIVATIONAL_QUOTES[quote_index]

        return Texts.MORNING_DIGEST.format(
            name=name,
            date=formatted_date,
            main_goal=goal_text,
            tasks=tasks_section,
            habits=habits_section,
            motivation=motivation,
        )

    async def build_evening_digest(self, user: User) -> str:
        """Construct evening reflection digest."""
        tasks = await self.task_repo.get_today_tasks(user.id)

        completed_count = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED.value)
        remaining_count = len(tasks) - completed_count

        # Focus time
        focus_mins = await self.focus_repo.get_today_focus_minutes(user.id)
        focus_str = format_minutes(focus_mins)

        # Habits completed today
        completions = await self.habit_repo.get_today_completions(user.id)
        completed_habits_count = sum(1 for c in completions if not c.skipped)
        total_habits = await self.habit_repo.count_active_habits(user.id)

        habits_info = ""
        if total_habits > 0:
            habits_info = f"🔄 Привычек выполнено: {completed_habits_count} из {total_habits}\n"

        return Texts.EVENING_DIGEST.format(
            completed=completed_count,
            remaining=remaining_count,
            focus_time=focus_str,
            habits=habits_info,
        )
