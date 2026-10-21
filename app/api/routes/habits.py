"""Habit endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas import HabitCompleteRequest, HabitCreate, HabitResponse
from app.db.models.habit import Habit
from app.db.models.user import User
from app.db.repositories.habit_repo import HabitRepository
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/habits", tags=["habits"])


def _habit_to_response(habit: Habit, today_completed_ids: set[int] | None = None) -> HabitResponse:
    """Convert a Habit ORM object to a HabitResponse schema."""
    completed_today = False
    if today_completed_ids is not None:
        completed_today = habit.id in today_completed_ids
    elif hasattr(habit, "completions") and habit.completions:
        today = date.today()
        completed_today = any(c.completed_date == today for c in habit.completions)

    return HabitResponse(
        id=habit.id,
        title=habit.title,
        description=habit.description,
        frequency=habit.frequency,
        days_of_week=habit.days_of_week,
        times_per_week=habit.times_per_week,
        reminder_time=habit.reminder_time,
        current_streak=habit.current_streak,
        best_streak=habit.best_streak,
        total_completions=habit.total_completions,
        start_date=habit.start_date,
        is_active=habit.is_active,
        is_paused=habit.is_paused,
        completed_today=completed_today,
        created_at=habit.created_at,
        updated_at=habit.updated_at,
    )


@router.get("", response_model=list[HabitResponse])
async def list_habits(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[HabitResponse]:
    """List all active habits for the current user."""
    repo = HabitRepository(session)
    habits = await repo.get_user_habits(user.id)

    # Fetch today's completions to mark completed_today
    today_completions = await repo.get_today_completions(user.id)
    completed_ids = {c.habit_id for c in today_completions}

    return [_habit_to_response(h, completed_ids) for h in habits]


@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
async def create_habit(
    body: HabitCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HabitResponse:
    """Create a new habit."""
    repo = HabitRepository(session)
    habit = await repo.create(
        user_id=user.id,
        title=body.title,
        description=body.description,
        frequency=body.frequency,
        days_of_week=body.days_of_week,
        times_per_week=body.times_per_week,
        reminder_time=body.reminder_time,
    )
    return _habit_to_response(habit)


@router.post("/{habit_id}/complete", response_model=HabitResponse)
async def complete_habit(
    habit_id: int,
    body: HabitCompleteRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HabitResponse:
    """Mark a habit as completed for a given date (default: today)."""
    repo = HabitRepository(session)
    habit = await repo.get_by_id(habit_id, user_id=user.id)

    if habit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "HABIT_NOT_FOUND", "message": "Привычка не найдена"}},
        )

    try:
        await repo.complete_habit(habit, completed_date=body.date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "ALREADY_COMPLETED", "message": str(exc)}},
        )

    # Refresh to get updated streaks
    habit = await repo.get_by_id(habit_id, user_id=user.id)
    completed_ids = {habit_id}  # We just completed it
    return _habit_to_response(habit, completed_ids)  # type: ignore[arg-type]


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(
    habit_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a habit. Only the owner can delete."""
    repo = HabitRepository(session)
    habit = await repo.get_by_id(habit_id, user_id=user.id)

    if habit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "HABIT_NOT_FOUND", "message": "Привычка не найдена"}},
        )

    await repo.delete_habit(habit)
