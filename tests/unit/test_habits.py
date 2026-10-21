"""Unit tests for HabitService."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.services.habit_service import HabitService


@pytest.mark.asyncio
async def test_create_habit(db_session: AsyncSession, test_user: User):
    service = HabitService(db_session)
    habit, err = await service.create_habit(
        user_id=test_user.id,
        title="Читать 20 минут",
        description="Каждый день перед сном",
    )

    assert err is None
    assert habit is not None
    assert habit.title == "Читать 20 минут"
    assert habit.current_streak == 0
    assert habit.best_streak == 0


@pytest.mark.asyncio
async def test_complete_habit_and_streak(db_session: AsyncSession, test_user: User):
    service = HabitService(db_session)
    habit, _ = await service.create_habit(test_user.id, "Пить воду")
    assert habit is not None

    completion, err = await service.complete_habit(habit.id, test_user.id)
    assert err is None
    assert completion is not None

    # Check updated streak
    updated = await service.get_habit(habit.id, test_user.id)
    assert updated.current_streak == 1
    assert updated.best_streak == 1
    assert updated.total_completions == 1

    # Check streak message
    msg = service.get_streak_message(updated)
    assert "1 дн" in msg


@pytest.mark.asyncio
async def test_cannot_complete_twice_same_day(db_session: AsyncSession, test_user: User):
    service = HabitService(db_session)
    habit, _ = await service.create_habit(test_user.id, "Зарядка")
    assert habit is not None

    c1, err1 = await service.complete_habit(habit.id, test_user.id)
    assert err1 is None and c1 is not None

    c2, err2 = await service.complete_habit(habit.id, test_user.id)
    assert c2 is None
    assert "уже отмечена" in err2.lower()


@pytest.mark.asyncio
async def test_habit_limit_free_tier(db_session: AsyncSession, test_user: User, monkeypatch):
    service = HabitService(db_session)
    monkeypatch.setattr(service.settings, "FREE_MAX_HABITS", 1)

    h1, err1 = await service.create_habit(test_user.id, "Привычка 1")
    assert err1 is None and h1 is not None

    h2, err2 = await service.create_habit(test_user.id, "Привычка 2")
    assert h2 is None
    assert "лимит" in err2.lower()
