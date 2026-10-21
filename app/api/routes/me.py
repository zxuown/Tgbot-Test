"""Current user info endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas import UserResponse
from app.db.models.user import User
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.get("", response_model=UserResponse)
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """Get current authenticated user info."""
    sub_repo = SubscriptionRepository(session)
    sub = await sub_repo.get_or_create(user.id)

    return UserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        language=user.language,
        timezone=user.timezone,
        role=user.role,
        goal_30_days=user.goal_30_days,
        onboarding_completed=user.onboarding_completed,
        is_active=user.is_active,
        last_active_at=user.last_active_at,
        subscription_tier=sub.tier,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
