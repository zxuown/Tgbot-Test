"""Task repository."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.task import Task, TaskStatus, TaskTag


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: int, **kwargs: object) -> Task:
        task = Task(user_id=user_id, **kwargs)
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_by_id(self, task_id: int, user_id: int | None = None) -> Task | None:
        stmt = select(Task).options(selectinload(Task.tags), selectinload(Task.subtasks)).where(Task.id == task_id)
        if user_id is not None:
            stmt = stmt.where(Task.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_tasks(
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
        stmt = (
            select(Task)
            .options(selectinload(Task.tags))
            .where(Task.user_id == user_id)
            .order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
        )

        if status:
            stmt = stmt.where(Task.status == status)
        else:
            # Exclude cancelled by default
            stmt = stmt.where(Task.status != TaskStatus.CANCELLED.value)

        if priority:
            stmt = stmt.where(Task.priority == priority)
        if category:
            stmt = stmt.where(Task.category == category)
        if due_date:
            stmt = stmt.where(Task.due_date == due_date)
        if overdue:
            stmt = stmt.where(
                Task.due_date < date.today(),
                Task.status.notin_([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]),
            )
        if important:
            stmt = stmt.where(Task.is_important == True)

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_today_tasks(self, user_id: int) -> list[Task]:
        today = date.today()
        stmt = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.due_date == today,
                Task.status.notin_([TaskStatus.CANCELLED.value]),
            )
            .order_by(Task.due_time.asc().nullslast())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_overdue_tasks(self, user_id: int) -> list[Task]:
        today = date.today()
        stmt = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.due_date < today,
                Task.status.notin_([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]),
            )
            .order_by(Task.due_date.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_week_tasks(self, user_id: int) -> list[Task]:
        today = date.today()
        week_end = today + timedelta(days=7)
        stmt = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.due_date >= today,
                Task.due_date <= week_end,
                Task.status.notin_([TaskStatus.CANCELLED.value]),
            )
            .order_by(Task.due_date.asc(), Task.due_time.asc().nullslast())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_task(self, task: Task, **kwargs: object) -> Task:
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now(UTC)
        await self.session.flush()
        return task

    async def complete_task(self, task: Task) -> Task:
        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        await self.session.flush()
        return task

    async def delete_task(self, task: Task) -> None:
        await self.session.delete(task)
        await self.session.flush()

    async def count_active_tasks(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status.notin_([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]),
            )
        )
        return result.scalar_one()

    async def count_user_tasks(
        self,
        user_id: int,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        due_date: date | None = None,
        overdue: bool = False,
        important: bool = False,
    ) -> int:
        stmt = select(func.count(Task.id)).where(Task.user_id == user_id)
        if status:
            stmt = stmt.where(Task.status == status)
        else:
            stmt = stmt.where(Task.status != TaskStatus.CANCELLED.value)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        if category:
            stmt = stmt.where(Task.category == category)
        if due_date:
            stmt = stmt.where(Task.due_date == due_date)
        if overdue:
            stmt = stmt.where(
                Task.due_date < date.today(),
                Task.status.notin_([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]),
            )
        if important:
            stmt = stmt.where(Task.is_important == True)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_completed_tasks(self, user_id: int, since: datetime | None = None) -> int:
        stmt = select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED.value,
        )
        if since:
            stmt = stmt.where(Task.completed_at >= since)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_total_tasks_count(self) -> int:
        result = await self.session.execute(select(func.count(Task.id)))
        return result.scalar_one()

    async def get_total_completed_count(self) -> int:
        result = await self.session.execute(
            select(func.count(Task.id)).where(Task.status == TaskStatus.COMPLETED.value)
        )
        return result.scalar_one()

    async def add_tags(self, task_id: int, tags: list[str]) -> None:
        for tag_name in tags:
            tag = TaskTag(task_id=task_id, tag=tag_name)
            self.session.add(tag)
        await self.session.flush()
