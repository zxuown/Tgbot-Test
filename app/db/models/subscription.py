"""Subscription model for tier management."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(20), default=SubscriptionTier.FREE.value, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)  # telegram, stripe, mock
    payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_requests_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_requests_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="subscription")  # type: ignore[name-defined]
