"""DailyPlan model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class DailyPlan(TimestampMixin, Base):
    __tablename__ = "daily_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    main_focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_content: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string with plan details
    ai_generated: Mapped[bool] = mapped_column(default=False, nullable=False)
