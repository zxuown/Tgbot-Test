"""Subscription repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.subscription import Subscription, SubscriptionTier


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, user_id: int) -> Subscription:
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await self.session.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=user_id, tier=SubscriptionTier.FREE.value)
            self.session.add(sub)
            await self.session.flush()
        return sub

    async def increment_ai_usage(self, user_id: int) -> int:
        sub = await self.get_or_create(user_id)

        # Reset counter monthly
        now = datetime.now(UTC)
        if sub.ai_requests_reset_at is None or sub.ai_requests_reset_at.month != now.month:
            sub.ai_requests_this_month = 0
            sub.ai_requests_reset_at = now

        sub.ai_requests_this_month += 1
        await self.session.flush()
        return sub.ai_requests_this_month

    async def can_use_ai(self, user_id: int, limit: int) -> bool:
        sub = await self.get_or_create(user_id)
        if sub.tier == SubscriptionTier.PRO.value:
            return True

        now = datetime.now(UTC)
        if sub.ai_requests_reset_at is None or sub.ai_requests_reset_at.month != now.month:
            return True

        return sub.ai_requests_this_month < limit

    async def is_pro(self, user_id: int) -> bool:
        sub = await self.get_or_create(user_id)
        return sub.tier == SubscriptionTier.PRO.value

    async def upgrade_to_pro(self, user_id: int, payment_provider: str = "mock", payment_id: str | None = None) -> Subscription:
        sub = await self.get_or_create(user_id)
        sub.tier = SubscriptionTier.PRO.value
        sub.started_at = datetime.now(UTC)
        sub.payment_provider = payment_provider
        sub.payment_id = payment_id
        await self.session.flush()
        return sub

    async def get_total_ai_requests(self) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Subscription.ai_requests_this_month), 0))
        )
        return result.scalar_one()
