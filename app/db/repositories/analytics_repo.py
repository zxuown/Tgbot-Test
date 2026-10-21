"""Analytics repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analytics import AdminAuditLog, UsageEvent


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_event(
        self,
        event_type: str,
        user_id: int | None = None,
        telegram_id: int | None = None,
        event_data: dict | None = None,
    ) -> UsageEvent:
        event = UsageEvent(
            user_id=user_id,
            telegram_id=telegram_id,
            event_type=event_type,
            event_data=json.dumps(event_data) if event_data else None,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def log_admin_action(
        self,
        admin_telegram_id: int,
        action: str,
        target: str | None = None,
        details: str | None = None,
    ) -> AdminAuditLog:
        log = AdminAuditLog(
            admin_telegram_id=admin_telegram_id,
            action=action,
            target=target,
            details=details,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_command_stats(self, days: int = 1) -> dict[str, int]:
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(UsageEvent.event_type, func.count(UsageEvent.id))
            .where(UsageEvent.created_at >= since)
            .group_by(UsageEvent.event_type)
            .order_by(func.count(UsageEvent.id).desc())
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.fetchall()}

    async def get_errors_count(self, days: int = 1) -> int:
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            select(func.count(UsageEvent.id)).where(
                UsageEvent.event_type == "error",
                UsageEvent.created_at >= since,
            )
        )
        return result.scalar_one()
