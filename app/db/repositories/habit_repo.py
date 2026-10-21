"""Habit repository."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.habit import Habit, HabitCompletion


class HabitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: int, **kwargs: object) -> Habit:
        habit = Habit(user_id=user_id, start_date=date.today(), **kwargs)
        self.session.add(habit)
        await self.session.flush()
        return habit

    async def get_by_id(self, habit_id: int, user_id: int | None = None) -> Habit | None:
        stmt = select(Habit).options(selectinload(Habit.completions)).where(Habit.id == habit_id)
        if user_id is not None:
            stmt = stmt.where(Habit.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_habits(self, user_id: int, active_only: bool = True) -> list[Habit]:
        stmt = select(Habit).where(Habit.user_id == user_id).order_by(Habit.created_at.asc())
        if active_only:
            stmt = stmt.where(Habit.is_active == True, Habit.is_paused == False)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active_habits(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(Habit.id)).where(
                Habit.user_id == user_id,
                Habit.is_active == True,
            )
        )
        return result.scalar_one()

    async def complete_habit(self, habit: Habit, completed_date: date | None = None, skipped: bool = False) -> HabitCompletion:
        target_date = completed_date or date.today()

        # Check if already completed today
        existing = await self.session.execute(
            select(HabitCompletion).where(
                HabitCompletion.habit_id == habit.id,
                HabitCompletion.completed_date == target_date,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Привычка уже отмечена на эту дату.")

        completion = HabitCompletion(
            habit_id=habit.id,
            completed_date=target_date,
            skipped=skipped,
        )
        self.session.add(completion)

        if not skipped:
            habit.total_completions += 1
            habit.current_streak += 1
            if habit.current_streak > habit.best_streak:
                habit.best_streak = habit.current_streak
        else:
            habit.current_streak = 0

        await self.session.flush()
        return completion

    async def get_today_completions(self, user_id: int) -> list[HabitCompletion]:
        today = date.today()
        stmt = (
            select(HabitCompletion)
            .join(Habit)
            .where(
                Habit.user_id == user_id,
                HabitCompletion.completed_date == today,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_week_completions_count(self, user_id: int) -> int:
        week_start = date.today() - timedelta(days=date.today().weekday())
        result = await self.session.execute(
            select(func.count(HabitCompletion.id))
            .join(Habit)
            .where(
                Habit.user_id == user_id,
                HabitCompletion.completed_date >= week_start,
                HabitCompletion.skipped == False,
            )
        )
        return result.scalar_one()

    async def update_habit(self, habit: Habit, **kwargs: object) -> Habit:
        for key, value in kwargs.items():
            if hasattr(habit, key):
                setattr(habit, key, value)
        habit.updated_at = datetime.now(UTC)
        await self.session.flush()
        return habit

    async def delete_habit(self, habit: Habit) -> None:
        await self.session.delete(habit)
        await self.session.flush()

    async def recalculate_streak(self, habit: Habit) -> int:
        """Recalculate current streak from completions history."""
        stmt = (
            select(HabitCompletion.completed_date)
            .where(
                HabitCompletion.habit_id == habit.id,
                HabitCompletion.skipped == False,
            )
            .order_by(HabitCompletion.completed_date.desc())
        )
        result = await self.session.execute(stmt)
        dates = [row[0] for row in result.fetchall()]

        if not dates:
            habit.current_streak = 0
            return 0

        streak = 0
        expected = date.today()
        for d in dates:
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d < expected:
                break

        habit.current_streak = streak
        if streak > habit.best_streak:
            habit.best_streak = streak
        await self.session.flush()
        return streak
