"""Habit and HabitCompletion models."""

from __future__ import annotations

import enum
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class HabitFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    SPECIFIC_DAYS = "specific_days"
    TIMES_PER_WEEK = "times_per_week"
    CUSTOM = "custom"


class Habit(TimestampMixin, Base):
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency: Mapped[str] = mapped_column(String(30), default=HabitFrequency.DAILY.value, nullable=False)
    days_of_week: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. "1,3,5" for Mon,Wed,Fri
    times_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "HH:MM"
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_completions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="habits")  # type: ignore[name-defined]
    completions: Mapped[list[HabitCompletion]] = relationship("HabitCompletion", back_populates="habit", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Habit(id={self.id}, title='{self.title[:30]}')>"


class HabitCompletion(Base):
    __tablename__ = "habit_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    habit_id: Mapped[int] = mapped_column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True)
    completed_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    habit: Mapped[Habit] = relationship("Habit", back_populates="completions")
