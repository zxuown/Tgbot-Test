"""User statistics endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas import StatsResponse
from app.api.schemas.schemas import FocusStatsResponse
from app.db.models.user import User
from app.db.repositories.focus_repo import FocusSessionRepository
from app.db.repositories.habit_repo import HabitRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.task_repo import TaskRepository
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StatsResponse:
    """Get aggregated statistics for the current user."""
    task_repo = TaskRepository(session)
    habit_repo = HabitRepository(session)
    focus_repo = FocusSessionRepository(session)
    sub_repo = SubscriptionRepository(session)

    # Task stats
    active_tasks = await task_repo.count_active_tasks(user.id)
    completed_all = await task_repo.count_completed_tasks(user.id)
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = await task_repo.count_completed_tasks(user.id, since=today_start)
    overdue = await task_repo.get_overdue_tasks(user.id)

    # Habit stats
    habits_count = await habit_repo.count_active_habits(user.id)
    today_completions = await habit_repo.get_today_completions(user.id)
    week_completions = await habit_repo.get_week_completions_count(user.id)

    # Focus stats
    focus_today = await focus_repo.get_today_focus_minutes(user.id)
    focus_week = await focus_repo.get_week_stats(user.id)

    # Subscription
    sub = await sub_repo.get_or_create(user.id)

    return StatsResponse(
        tasks_total=active_tasks + completed_all,
        tasks_active=active_tasks,
        tasks_completed=completed_all,
        tasks_completed_today=completed_today,
        tasks_overdue=len(overdue),
        habits_total=habits_count,
        habits_completed_today=len(today_completions),
        habits_week_completions=week_completions,
        focus_minutes_today=focus_today,
        focus_week=FocusStatsResponse(**focus_week),
        subscription_tier=sub.tier,
    )
