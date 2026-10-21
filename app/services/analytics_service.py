"""Analytics service aggregating metrics for users and administrators."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.db.repositories.analytics_repo import AnalyticsRepository
from app.db.repositories.focus_repo import FocusSessionRepository
from app.db.repositories.habit_repo import HabitRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.task_repo import TaskRepository
from app.db.repositories.user_repo import UserRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AnalyticsService:
    """Provides user and system-level productivity statistics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.analytics_repo = AnalyticsRepository(session)
        self.user_repo = UserRepository(session)
        self.task_repo = TaskRepository(session)
        self.habit_repo = HabitRepository(session)
        self.focus_repo = FocusSessionRepository(session)
        self.sub_repo = SubscriptionRepository(session)

    async def log_event(
        self,
        event_type: str,
        user_id: int | None = None,
        telegram_id: int | None = None,
        event_data: dict[str, Any] | None = None,
    ) -> None:
        """Log an event for analytics."""
        await self.analytics_repo.log_event(
            event_type=event_type,
            user_id=user_id,
            telegram_id=telegram_id,
            event_data=event_data,
        )

    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        """Collect productivity dashboard metrics for a user."""
        active_tasks = await self.task_repo.count_active_tasks(user_id)
        completed_all = await self.task_repo.count_completed_tasks(user_id)

        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        completed_today = await self.task_repo.count_completed_tasks(user_id, since=today_start)
        overdue_tasks = await self.task_repo.get_overdue_tasks(user_id)

        active_habits = await self.habit_repo.count_active_habits(user_id)
        today_completions = await self.habit_repo.get_today_completions(user_id)
        week_completions = await self.habit_repo.get_week_completions_count(user_id)

        focus_today = await self.focus_repo.get_today_focus_minutes(user_id)
        focus_week = await self.focus_repo.get_week_stats(user_id)

        sub = await self.sub_repo.get_or_create(user_id)

        return {
            "tasks_total": active_tasks + completed_all,
            "tasks_active": active_tasks,
            "tasks_completed": completed_all,
            "tasks_completed_today": completed_today,
            "tasks_overdue": len(overdue_tasks),
            "habits_total": active_habits,
            "habits_completed_today": len(today_completions),
            "habits_week_completions": week_completions,
            "focus_minutes_today": focus_today,
            "focus_week": focus_week,
            "subscription_tier": sub.tier,
        }

    async def get_admin_stats(self) -> dict[str, Any]:
        """Collect system-wide administrator statistics."""
        total_users = await self.user_repo.get_total_count()
        active_today = await self.user_repo.get_active_count(days=1)
        active_week = await self.user_repo.get_active_count(days=7)

        total_tasks = await self.task_repo.get_total_tasks_count()
        completed_tasks = await self.task_repo.get_total_completed_count()
        total_ai = await self.sub_repo.get_total_ai_requests()

        commands_usage = await self.analytics_repo.get_command_stats(days=7)
        errors_24h = await self.analytics_repo.get_errors_count(days=1)

        return {
            "total_users": total_users,
            "active_today": active_today,
            "active_week": active_week,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "ai_requests": total_ai,
            "errors_24h": errors_24h,
            "top_commands": commands_usage,
        }
