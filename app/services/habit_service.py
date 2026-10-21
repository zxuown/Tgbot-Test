"""Habit tracking and streak calculation service."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.db.models.habit import Habit, HabitCompletion, HabitFrequency
from app.db.repositories.habit_repo import HabitRepository
from app.db.repositories.subscription_repo import SubscriptionRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class HabitService:
    """Business logic for habit operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.habit_repo = HabitRepository(session)
        self.sub_repo = SubscriptionRepository(session)
        self.settings = get_settings()

    async def check_habit_limit(self, user_id: int) -> bool:
        """Check if user can create more habits under their subscription."""
        is_pro = await self.sub_repo.is_pro(user_id)
        if is_pro:
            return True

        active_count = await self.habit_repo.count_active_habits(user_id)
        return active_count < self.settings.FREE_MAX_HABITS

    async def create_habit(
        self,
        user_id: int,
        title: str,
        description: str | None = None,
        frequency: str = HabitFrequency.DAILY.value,
        days_of_week: str | None = None,
        times_per_week: int | None = None,
        reminder_time: str | None = None,
    ) -> tuple[Habit | None, str | None]:
        """Create a habit. Returns (habit, None) or (None, error_message)."""
        can_create = await self.check_habit_limit(user_id)
        if not can_create:
            return None, f"Достигнут лимит привычек для тарифа Free ({self.settings.FREE_MAX_HABITS}). Перейдите на Pro."

        habit = await self.habit_repo.create(
            user_id=user_id,
            title=title.strip(),
            description=description,
            frequency=frequency,
            days_of_week=days_of_week,
            times_per_week=times_per_week,
            reminder_time=reminder_time,
        )
        return habit, None

    async def get_habits(self, user_id: int, active_only: bool = True) -> list[Habit]:
        """List habits for user."""
        return await self.habit_repo.get_user_habits(user_id, active_only=active_only)

    async def get_habit(self, habit_id: int, user_id: int) -> Habit | None:
        """Get habit by id with ownership check."""
        return await self.habit_repo.get_by_id(habit_id, user_id=user_id)

    async def complete_habit(
        self,
        habit_id: int,
        user_id: int,
        target_date: date | None = None,
        skipped: bool = False,
    ) -> tuple[HabitCompletion | None, str | None]:
        """Mark habit as completed or skipped for a given date."""
        habit = await self.habit_repo.get_by_id(habit_id, user_id=user_id)
        if not habit:
            return None, "Привычка не найдена"

        try:
            completion = await self.habit_repo.complete_habit(
                habit=habit,
                completed_date=target_date,
                skipped=skipped,
            )
            return completion, None
        except ValueError as exc:
            return None, str(exc)

    def get_streak_message(self, habit: Habit) -> str:
        """Generate motivational streak message."""
        if habit.current_streak <= 0:
            return ""
        if habit.current_streak > 1 and habit.current_streak == habit.best_streak:
            return f"\n🏆 Ты выполняешь привычку {habit.current_streak} дн. подряд! Это лучшая серия за всё время!"
        return f"\n🔥 Серия: {habit.current_streak} дн. (лучшая: {habit.best_streak} дн.)"

    async def pause_habit(self, habit_id: int, user_id: int) -> bool:
        """Pause habit."""
        habit = await self.habit_repo.get_by_id(habit_id, user_id=user_id)
        if not habit:
            return False
        await self.habit_repo.update_habit(habit, is_paused=True)
        return True

    async def resume_habit(self, habit_id: int, user_id: int) -> bool:
        """Resume paused habit."""
        habit = await self.habit_repo.get_by_id(habit_id, user_id=user_id)
        if not habit:
            return False
        await self.habit_repo.update_habit(habit, is_paused=False)
        return True

    async def delete_habit(self, habit_id: int, user_id: int) -> bool:
        """Delete habit."""
        habit = await self.habit_repo.get_by_id(habit_id, user_id=user_id)
        if not habit:
            return False
        await self.habit_repo.delete_habit(habit)
        return True
