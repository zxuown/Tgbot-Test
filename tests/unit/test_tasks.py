"""Unit tests for TaskService."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.task import TaskPriority, TaskStatus
from app.db.models.user import User
from app.services.task_service import TaskService


@pytest.mark.asyncio
async def test_create_task(db_session: AsyncSession, test_user: User):
    service = TaskService(db_session)
    task, err = await service.create_task(
        user_id=test_user.id,
        title="Купить билеты",
        description="Поезд в Санкт-Петербург",
        priority=TaskPriority.HIGH.value,
        estimated_minutes=15,
        category="Личное",
    )

    assert err is None
    assert task is not None
    assert task.title == "Купить билеты"
    assert task.status == TaskStatus.INBOX.value
    assert task.priority == TaskPriority.HIGH.value


@pytest.mark.asyncio
async def test_complete_task(db_session: AsyncSession, test_user: User):
    service = TaskService(db_session)
    task, _ = await service.create_task(
        user_id=test_user.id,
        title="Завершаемая задача",
    )
    assert task is not None

    completed = await service.complete_task(task.id, test_user.id)
    assert completed is not None
    assert completed.status == TaskStatus.COMPLETED.value
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_delete_task(db_session: AsyncSession, test_user: User):
    service = TaskService(db_session)
    task, _ = await service.create_task(
        user_id=test_user.id,
        title="Удаляемая задача",
    )
    assert task is not None

    deleted = await service.delete_task(task.id, test_user.id)
    assert deleted is True

    fetched = await service.get_task(task.id, test_user.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_other_user_cannot_access_task(db_session: AsyncSession, test_user: User):
    service = TaskService(db_session)
    task, _ = await service.create_task(
        user_id=test_user.id,
        title="Секретная задача",
    )
    assert task is not None

    other_user_id = 99999
    # Other user cannot get, complete or delete
    assert await service.get_task(task.id, user_id=other_user_id) is None
    assert await service.complete_task(task.id, user_id=other_user_id) is None
    assert await service.delete_task(task.id, user_id=other_user_id) is False


@pytest.mark.asyncio
async def test_task_limit_free_tier(db_session: AsyncSession, test_user: User, monkeypatch):
    service = TaskService(db_session)
    monkeypatch.setattr(service.settings, "FREE_MAX_TASKS", 2)

    t1, err1 = await service.create_task(test_user.id, "Задача 1")
    assert err1 is None and t1 is not None

    t2, err2 = await service.create_task(test_user.id, "Задача 2")
    assert err2 is None and t2 is not None

    # Third should fail
    t3, err3 = await service.create_task(test_user.id, "Задача 3")
    assert t3 is None
    assert "лимит" in err3.lower()
