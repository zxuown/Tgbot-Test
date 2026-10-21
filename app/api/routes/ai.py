"""AI analysis endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas import AIAnalyzeRequest, AIAnalyzeResponse
from app.core.config import get_settings
from app.db.models.user import User
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.session import get_session
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


async def _check_ai_quota(user: User, session: AsyncSession) -> None:
    """Check if user has remaining AI quota, raise 429 if exhausted."""
    settings = get_settings()
    sub_repo = SubscriptionRepository(session)
    can_use = await sub_repo.can_use_ai(user.id, settings.FREE_MONTHLY_AI_LIMIT)
    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "AI_QUOTA_EXCEEDED",
                    "message": "Лимит AI-запросов исчерпан. Обновите подписку до PRO.",
                }
            },
        )


@router.post("/analyze", response_model=AIAnalyzeResponse)
async def analyze_text(
    body: AIAnalyzeRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AIAnalyzeResponse:
    """Analyze text using AI (extract tasks, parse intent, etc.)."""
    await _check_ai_quota(user, session)

    sub_repo = SubscriptionRepository(session)
    await sub_repo.increment_ai_usage(user.id)

    ai_service = AIService()
    mode = body.mode or "general"
    if mode == "task":
        parsed = await ai_service.parse_task_from_text(body.text)
        result = (
            f"📋 Из текста извлечена задача:\n"
            f"• Заголовок: {parsed.get('title', body.text[:100])}\n"
            f"• Приоритет: {parsed.get('priority', 'medium')}\n"
            f"• Срок: {parsed.get('due_date') or 'не указан'}"
        )
    elif mode == "plan":
        result = await ai_service.plan_day(body.text)
    else:
        result = await ai_service.analyze_thought(body.text)

    return AIAnalyzeResponse(result=result)


@router.post("/plan-day", response_model=AIAnalyzeResponse)
async def plan_day(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AIAnalyzeResponse:
    """Generate an AI-powered daily plan based on user's tasks and habits."""
    await _check_ai_quota(user, session)

    sub_repo = SubscriptionRepository(session)
    await sub_repo.increment_ai_usage(user.id)

    ai_service = AIService()
    result = await ai_service.plan_day("Запланируй мой рабочий день с учётом фокуса и задач")
    return AIAnalyzeResponse(result=result)
