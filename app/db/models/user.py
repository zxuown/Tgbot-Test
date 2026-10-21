"""User and UserSettings models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.ai import AiConversation
    from app.db.models.focus_session import FocusSession
    from app.db.models.habit import Habit
    from app.db.models.subscription import Subscription
    from app.db.models.task import Task


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow", nullable=False)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)  # freelancer/student/entrepreneur/manager/other
    goal_30_days: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    settings: Mapped[UserSettings | None] = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    tasks: Mapped[list[Task]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]
    habits: Mapped[list[Habit]] = relationship("Habit", back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]
    focus_sessions: Mapped[list[FocusSession]] = relationship("FocusSession", back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]
    subscription: Mapped[Subscription | None] = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")  # type: ignore[name-defined]
    ai_conversations: Mapped[list[AiConversation]] = relationship("AiConversation", back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"


class UserSettings(TimestampMixin, Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    morning_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    morning_digest_time: Mapped[str] = mapped_column(String(5), default="08:00", nullable=False)
    evening_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    evening_digest_time: Mapped[str] = mapped_column(String(5), default="21:00", nullable=False)
    notifications_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    working_hours_start: Mapped[str] = mapped_column(String(5), default="09:00", nullable=False)
    working_hours_end: Mapped[str] = mapped_column(String(5), default="18:00", nullable=False)

    user: Mapped[User] = relationship("User", back_populates="settings")
