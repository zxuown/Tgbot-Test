"""FocusSession model for Pomodoro / focus timer tracking."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class FocusSession(TimestampMixin, Base):
    __tablename__ = "focus_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extensions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    break_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # short, long

    user: Mapped[User] = relationship("User", back_populates="focus_sessions")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<FocusSession(id={self.id}, duration={self.duration_minutes}m, completed={self.is_completed})>"
