"""Focus session repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.focus_session import FocusSession


class FocusSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: int, duration_minutes: int, task_id: int | None = None) -> FocusSession:
        fs = FocusSession(
            user_id=user_id,
            task_id=task_id,
            duration_minutes=duration_minutes,
            started_at=datetime.now(UTC),
        )
        self.session.add(fs)
        await self.session.flush()
        return fs

    async def get_active_session(self, user_id: int) -> FocusSession | None:
        stmt = (
            select(FocusSession)
            .where(
                FocusSession.user_id == user_id,
                FocusSession.finished_at.is_(None),
            )
            .order_by(FocusSession.started_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def complete_session(self, session: FocusSession) -> FocusSession:
        now = datetime.now(UTC)
        session.finished_at = now
        session.is_completed = True
        if session.started_at:
            started = session.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            delta = now - started
            session.actual_minutes = int(delta.total_seconds() / 60)
        await self.session.flush()
        return session

    async def extend_session(self, session: FocusSession, extra_minutes: int = 15) -> FocusSession:
        session.duration_minutes += extra_minutes
        session.extensions_count += 1
        await self.session.flush()
        return session

    async def get_week_sessions(self, user_id: int) -> list[FocusSession]:
        week_ago = datetime.now(UTC) - timedelta(days=7)
        stmt = (
            select(FocusSession)
            .where(
                FocusSession.user_id == user_id,
                FocusSession.started_at >= week_ago,
            )
            .order_by(FocusSession.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_today_focus_minutes(self, user_id: int) -> int:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(
                FocusSession.user_id == user_id,
                FocusSession.started_at >= today_start,
                FocusSession.is_completed == True,
            )
        )
        return result.scalar_one()

    async def get_week_stats(self, user_id: int) -> dict:
        sessions = await self.get_week_sessions(user_id)
        completed = [s for s in sessions if s.is_completed]
        total_minutes = sum(s.actual_minutes or 0 for s in completed)
        return {
            "sessions_count": len(completed),
            "total_minutes": total_minutes,
        }
