"""Today's plan endpoint."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.routes.habits import _habit_to_response
from app.api.routes.tasks import _task_to_response
from app.api.schemas import TodayResponse
from app.db.models.task import TaskStatus
from app.db.models.user import User
from app.db.repositories.focus_repo import FocusSessionRepository
from app.db.repositories.habit_repo import HabitRepository
from app.db.repositories.task_repo import TaskRepository
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/today", tags=["today"])


@router.get("", response_model=TodayResponse)
async def get_today(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TodayResponse:
    """Get today's overview: tasks, overdue tasks, habits, and focus stats."""
    task_repo = TaskRepository(session)
    habit_repo = HabitRepository(session)
    focus_repo = FocusSessionRepository(session)

    today = date.today()

    # Today's tasks
    today_tasks = await task_repo.get_today_tasks(user.id)
    overdue_tasks = await task_repo.get_overdue_tasks(user.id)

    # Habits
    habits = await habit_repo.get_user_habits(user.id)
    today_completions = await habit_repo.get_today_completions(user.id)
    completed_habit_ids = {c.habit_id for c in today_completions}

    # Focus
    focus_minutes = await focus_repo.get_today_focus_minutes(user.id)

    # Count completed today
    completed_today = sum(1 for t in today_tasks if t.status == TaskStatus.COMPLETED.value)

    return TodayResponse(
        date=today,
        tasks=[_task_to_response(t) for t in today_tasks],
        overdue_tasks=[_task_to_response(t) for t in overdue_tasks],
        habits=[_habit_to_response(h, completed_habit_ids) for h in habits],
        focus_minutes_today=focus_minutes,
        completed_today=completed_today,
        total_today=len(today_tasks),
    )
