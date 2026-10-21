"""FastAPI dependencies for authentication and database access."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import validate_telegram_init_data
from app.db.models.user import User
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session

logger = logging.getLogger(__name__)


async def get_current_user(
    x_telegram_init_data: Annotated[str, Header()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Authenticate user via Telegram WebApp initData.

    Reads the ``X-Telegram-Init-Data`` header, validates it against the
    bot token, then looks up the user in the database by ``telegram_id``.
    Raises HTTP 401 if any step fails.
    """
    # 1. Validate the Telegram init data
    data = validate_telegram_init_data(x_telegram_init_data)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_INIT_DATA", "message": "Невалидные данные авторизации Telegram"}},
        )

    # 2. Extract telegram user
    tg_user = data.get("user")
    if not tg_user or "id" not in tg_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "MISSING_USER", "message": "Данные пользователя отсутствуют"}},
        )

    telegram_id: int = int(tg_user["id"])

    # 3. Lookup user in DB
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "Пользователь не найден. Сначала запустите бота."}},
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "USER_BLOCKED", "message": "Аккаунт заблокирован"}},
        )

    # 4. Update last active timestamp
    await user_repo.update_last_active(user.id)

    return user
