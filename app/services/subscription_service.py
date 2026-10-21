"""Subscription and feature access management service."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.db.models.subscription import Subscription, SubscriptionTier
from app.db.repositories.habit_repo import HabitRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.task_repo import TaskRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SubscriptionService:
    """Handles tier validation, feature limits, and mock payment upgrades."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sub_repo = SubscriptionRepository(session)
        self.task_repo = TaskRepository(session)
        self.habit_repo = HabitRepository(session)
        self.settings = get_settings()

    async def get_subscription(self, user_id: int) -> Subscription:
        """Get or create user subscription."""
        return await self.sub_repo.get_or_create(user_id)

    async def is_pro(self, user_id: int) -> bool:
        """Check if user has active PRO tier."""
        return await self.sub_repo.is_pro(user_id)

    async def can_use_ai(self, user_id: int) -> bool:
        """Check if user is allowed to make an AI request."""
        return await self.sub_repo.can_use_ai(user_id, self.settings.FREE_MONTHLY_AI_LIMIT)

    async def record_ai_usage(self, user_id: int) -> int:
        """Increment user's monthly AI usage counter."""
        return await self.sub_repo.increment_ai_usage(user_id)

    async def upgrade_to_pro(
        self,
        user_id: int,
        payment_provider: str = "mock",
        payment_id: str | None = None,
    ) -> Subscription:
        """Upgrade user to PRO tier."""
        return await self.sub_repo.upgrade_to_pro(
            user_id=user_id,
            payment_provider=payment_provider,
            payment_id=payment_id or "mock_payment_123",
        )

    async def get_tier_info(self, user_id: int) -> dict[str, Any]:
        """Get summary of subscription tier and usage limits."""
        sub = await self.get_subscription(user_id)
        is_pro = sub.tier == SubscriptionTier.PRO.value

        active_tasks = await self.task_repo.count_active_tasks(user_id)
        active_habits = await self.habit_repo.count_active_habits(user_id)

        return {
            "tier": sub.tier,
            "is_pro": is_pro,
            "ai_used_this_month": sub.ai_requests_this_month,
            "ai_monthly_limit": None if is_pro else self.settings.FREE_MONTHLY_AI_LIMIT,
            "tasks_count": active_tasks,
            "tasks_limit": None if is_pro else self.settings.FREE_MAX_TASKS,
            "habits_count": active_habits,
            "habits_limit": None if is_pro else self.settings.FREE_MAX_HABITS,
        }
