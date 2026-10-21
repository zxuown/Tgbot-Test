"""AI conversation and message models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class AiConversation(TimestampMixin, Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)  # analyze, plan, decompose, coach, review
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    user: Mapped[User] = relationship("User", back_populates="ai_conversations")  # type: ignore[name-defined]
    messages: Mapped[list[AiMessage]] = relationship("AiMessage", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AiConversation(id={self.id}, mode={self.mode})>"


class AiMessage(TimestampMixin, Base):
    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    conversation: Mapped[AiConversation] = relationship("AiConversation", back_populates="messages")
