"""User settings endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas import SettingsResponse, SettingsUpdate
from app.db.models.user import User
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def _build_settings_response(user: User) -> SettingsResponse:
    """Build a SettingsResponse from User + UserSettings."""
    s = user.settings
    return SettingsResponse(
        timezone=user.timezone,
        language=user.language,
        morning_digest_enabled=s.morning_digest_enabled if s else True,
        morning_digest_time=s.morning_digest_time if s else "08:00",
        evening_digest_enabled=s.evening_digest_enabled if s else True,
        evening_digest_time=s.evening_digest_time if s else "21:00",
        notifications_paused=s.notifications_paused if s else False,
        working_hours_start=s.working_hours_start if s else "09:00",
        working_hours_end=s.working_hours_end if s else "18:00",
    )


@router.get("", response_model=SettingsResponse)
async def get_settings(
    user: Annotated[User, Depends(get_current_user)],
) -> SettingsResponse:
    """Get current user settings."""
    return _build_settings_response(user)


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SettingsResponse:
    """Update user settings partially."""
    user_repo = UserRepository(session)
    update_data = body.model_dump(exclude_unset=True)

    if not update_data:
        return _build_settings_response(user)

    # Separate user-level fields from settings-level fields
    user_fields = {"timezone", "language"}
    user_updates = {k: v for k, v in update_data.items() if k in user_fields}
    settings_updates = {k: v for k, v in update_data.items() if k not in user_fields}

    # Update user fields
    if user_updates:
        await user_repo.update_user(user, **user_updates)

    # Update settings fields
    if settings_updates and user.settings:
        for key, value in settings_updates.items():
            if hasattr(user.settings, key):
                setattr(user.settings, key, value)
        await session.flush()

    # Re-fetch user with settings
    refreshed_user = await user_repo.get_by_id(user.id)
    if refreshed_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Ошибка обновления настроек"}},
        )

    return _build_settings_response(refreshed_user)
