"""Task CRUD endpoints."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from app.db.models.task import Task, TaskStatus
from app.db.models.user import User
from app.db.repositories.task_repo import TaskRepository
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _task_to_response(task: Task) -> TaskResponse:
    """Convert a Task ORM object to a TaskResponse schema."""
    tags: list[str] = []
    if hasattr(task, "tags") and task.tags:
        tags = [t.tag for t in task.tags]
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        due_time=task.due_time,
        estimated_minutes=task.estimated_minutes,
        category=task.category,
        is_important=task.is_important,
        source=task.source,
        parent_task_id=task.parent_task_id,
        completed_at=task.completed_at,
        comment=task.comment,
        tags=tags,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    category: str | None = Query(None),
    due_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> TaskListResponse:
    """List tasks with optional filters and pagination."""
    repo = TaskRepository(session)
    offset = (page - 1) * per_page

    tasks = await repo.get_user_tasks(
        user_id=user.id,
        status=status_filter,
        priority=priority,
        category=category,
        due_date=due_date,
        limit=per_page,
        offset=offset,
    )

    # Get total count for pagination
    total = await repo.count_user_tasks(
        user_id=user.id,
        status=status_filter,
        priority=priority,
        category=category,
        due_date=due_date,
    )
    pages = max(1, math.ceil(total / per_page))

    return TaskListResponse(
        tasks=[_task_to_response(t) for t in tasks],
        total=total,
        page=page,
        pages=pages,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskResponse:
    """Create a new task."""
    repo = TaskRepository(session)
    task = await repo.create(
        user_id=user.id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        due_date=body.due_date,
        due_time=body.due_time,
        estimated_minutes=body.estimated_minutes,
        category=body.category,
        source="webapp",
    )

    if body.tags:
        await repo.add_tags(task.id, body.tags)

    # Re-fetch with tags loaded
    task = await repo.get_by_id(task.id, user_id=user.id)  # type: ignore[assignment]
    return _task_to_response(task)  # type: ignore[arg-type]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskResponse:
    """Get a single task by ID. Only the owner can access it."""
    repo = TaskRepository(session)
    task = await repo.get_by_id(task_id, user_id=user.id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Задача не найдена"}},
        )

    return _task_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    body: TaskUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskResponse:
    """Update a task partially. Only the owner can update."""
    repo = TaskRepository(session)
    task = await repo.get_by_id(task_id, user_id=user.id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Задача не найдена"}},
        )

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return _task_to_response(task)

    # Handle status=completed specially
    if update_data.get("status") == TaskStatus.COMPLETED.value and task.status != TaskStatus.COMPLETED.value:
        update_data["completed_at"] = datetime.now(UTC)

    task = await repo.update_task(task, **update_data)
    return _task_to_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a task. Only the owner can delete."""
    repo = TaskRepository(session)
    task = await repo.get_by_id(task_id, user_id=user.id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Задача не найдена"}},
        )

    await repo.delete_task(task)
