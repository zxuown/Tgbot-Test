"""Task management service."""

from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.db.models.task import Task, TaskPriority, TaskStatus
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.task_repo import TaskRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TaskService:
    """Business logic for task operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.task_repo = TaskRepository(session)
        self.sub_repo = SubscriptionRepository(session)
        self.settings = get_settings()

    async def check_task_limit(self, user_id: int) -> bool:
        """Check if user can create more active tasks under their subscription."""
        is_pro = await self.sub_repo.is_pro(user_id)
        if is_pro:
            return True

        active_count = await self.task_repo.count_active_tasks(user_id)
        return active_count < self.settings.FREE_MAX_TASKS

    async def create_task(
        self,
        user_id: int,
        title: str,
        description: str | None = None,
        priority: str = TaskPriority.MEDIUM.value,
        due_date: date | None = None,
        due_time: time | None = None,
        estimated_minutes: int | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        source: str = "manual",
        parent_task_id: int | None = None,
        is_important: bool = False,
    ) -> tuple[Task | None, str | None]:
        """Create a task. Returns (task, None) on success or (None, error_message)."""
        can_create = await self.check_task_limit(user_id)
        if not can_create:
            return None, f"Достигнут лимит активных задач для тарифа Free ({self.settings.FREE_MAX_TASKS}). Перейдите на Pro."

        task = await self.task_repo.create(
            user_id=user_id,
            title=title.strip(),
            description=description,
            priority=priority,
            due_date=due_date,
            due_time=due_time,
            estimated_minutes=estimated_minutes,
            category=category,
            source=source,
            parent_task_id=parent_task_id,
            is_important=is_important,
            status=TaskStatus.PLANNED.value if due_date else TaskStatus.INBOX.value,
        )

        if tags:
            await self.task_repo.add_tags(task.id, tags)

        return task, None

    async def get_task(self, task_id: int, user_id: int) -> Task | None:
        """Get task by id, verifying user ownership."""
        return await self.task_repo.get_by_id(task_id, user_id=user_id)

    async def list_tasks(
        self,
        user_id: int,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        due_date: date | None = None,
        overdue: bool = False,
        important: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks with filters."""
        return await self.task_repo.get_user_tasks(
            user_id=user_id,
            status=status,
            priority=priority,
            category=category,
            due_date=due_date,
            overdue=overdue,
            important=important,
            limit=limit,
            offset=offset,
        )

    async def complete_task(self, task_id: int, user_id: int) -> Task | None:
        """Mark task as completed."""
        task = await self.task_repo.get_by_id(task_id, user_id=user_id)
        if not task:
            return None
        return await self.task_repo.complete_task(task)

    async def update_task(self, task_id: int, user_id: int, **kwargs: Any) -> Task | None:
        """Update task properties."""
        task = await self.task_repo.get_by_id(task_id, user_id=user_id)
        if not task:
            return None
        return await self.task_repo.update_task(task, **kwargs)

    async def delete_task(self, task_id: int, user_id: int) -> bool:
        """Delete task."""
        task = await self.task_repo.get_by_id(task_id, user_id=user_id)
        if not task:
            return False
        await self.task_repo.delete_task(task)
        return True

    async def get_today_tasks(self, user_id: int) -> list[Task]:
        """Get tasks scheduled for today."""
        return await self.task_repo.get_today_tasks(user_id)

    async def get_overdue_tasks(self, user_id: int) -> list[Task]:
        """Get overdue tasks."""
        return await self.task_repo.get_overdue_tasks(user_id)

    async def get_week_tasks(self, user_id: int) -> list[Task]:
        """Get tasks for the next 7 days."""
        return await self.task_repo.get_week_tasks(user_id)
