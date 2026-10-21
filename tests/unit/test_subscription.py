"""Unit tests for SubscriptionService."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.subscription import SubscriptionTier
from app.db.models.user import User
from app.services.subscription_service import SubscriptionService


@pytest.mark.asyncio
async def test_free_tier_limits(db_session: AsyncSession, test_user: User, monkeypatch):
    service = SubscriptionService(db_session)
    monkeypatch.setattr(service.settings, "FREE_MONTHLY_AI_LIMIT", 2)

    assert await service.can_use_ai(test_user.id) is True

    # 1st request
    await service.record_ai_usage(test_user.id)
    assert await service.can_use_ai(test_user.id) is True

    # 2nd request
    await service.record_ai_usage(test_user.id)
    # Now at limit
    assert await service.can_use_ai(test_user.id) is False


@pytest.mark.asyncio
async def test_upgrade_to_pro_removes_limits(db_session: AsyncSession, test_user: User, monkeypatch):
    service = SubscriptionService(db_session)
    monkeypatch.setattr(service.settings, "FREE_MONTHLY_AI_LIMIT", 1)

    # Exhaust free limit
    await service.record_ai_usage(test_user.id)
    assert await service.can_use_ai(test_user.id) is False

    # Upgrade to Pro
    sub = await service.upgrade_to_pro(test_user.id, payment_provider="mock", payment_id="tx_123")
    assert sub.tier == SubscriptionTier.PRO.value
    assert await service.is_pro(test_user.id) is True

    # Now allowed
    assert await service.can_use_ai(test_user.id) is True
