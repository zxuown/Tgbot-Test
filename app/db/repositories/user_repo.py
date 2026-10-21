"""User repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.subscription import Subscription, SubscriptionTier
from app.db.models.user import User, UserSettings


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.settings), selectinload(User.subscription))
            .where(User.telegram_id == telegram_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.settings), selectinload(User.subscription))
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language: str = "ru",
        timezone_str: str = "Europe/Moscow",
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language,
            timezone=timezone_str,
            last_active_at=datetime.now(UTC),
        )
        self.session.add(user)
        await self.session.flush()

        # Create default settings
        settings = UserSettings(user_id=user.id)
        self.session.add(settings)
        await self.session.flush()

        # Create default free subscription
        sub = Subscription(user_id=user.id, tier=SubscriptionTier.FREE.value)
        self.session.add(sub)
        await self.session.flush()

        user.settings = settings
        user.subscription = sub

        return user

    async def update_user(self, user: User, **kwargs: object) -> User:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.updated_at = datetime.now(UTC)
        await self.session.flush()
        return user

    async def update_last_active(self, user_id: int) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_active_at=datetime.now(UTC))
        )
        await self.session.execute(stmt)

    async def get_total_count(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def get_active_count(self, days: int = 1) -> int:
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            select(func.count(User.id)).where(
                User.last_active_at >= since,
                User.is_active == True,
            )
        )
        return result.scalar_one()

    async def get_all_active_users_with_settings(self) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.settings))
            .where(User.is_active == True, User.is_blocked == False)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.get_by_telegram_id(telegram_id)
