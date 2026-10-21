"""Telegram Webhook route for incoming updates in webhook mode."""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])

_bot: Bot | None = None
_dp: Dispatcher | None = None


def set_webhook_bot_and_dispatcher(bot: Bot, dp: Dispatcher) -> None:
    """Register bot and dispatcher references for webhook processing."""
    global _bot, _dp
    _bot = bot
    _dp = dp


@router.post("")
async def telegram_webhook_handler(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> Response:
    """Handle incoming Telegram webhook updates."""
    settings = get_settings()

    # Verify secret token if configured
    if (
        settings.WEBHOOK_SECRET
        and settings.WEBHOOK_SECRET not in {"changeme", ""}
        and x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET
    ):
        logger.warning("Rejected webhook update: invalid secret token header.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret token")

    if not _bot or not _dp:
        logger.error("Webhook received update but bot or dispatcher is not initialized.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bot not initialized")

    try:
        data: dict[str, Any] = await request.json()
        update = Update.model_validate(data, context={"bot": _bot})
        await _dp.feed_update(_bot, update)
        return Response(status_code=status.HTTP_200_OK)
    except Exception as exc:
        logger.error("Error processing webhook update: %s", exc)
        return Response(status_code=status.HTTP_200_OK)
