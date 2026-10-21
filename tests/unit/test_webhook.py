"""Tests for Telegram webhook endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.app import create_app
from app.api.routes.webhook import set_webhook_bot_and_dispatcher
from app.core.config import Settings


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_secret(monkeypatch):
    custom_settings = Settings(
        BOT_MODE="webhook",
        WEBHOOK_SECRET="super-secret-12345",
        WEBHOOK_PATH="/webhook",
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: custom_settings)
    monkeypatch.setattr("app.api.routes.webhook.get_settings", lambda: custom_settings)

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Request without header
        resp = await client.post("/webhook", json={"update_id": 1})
        assert resp.status_code == 403

        # Request with wrong header
        resp = await client.post(
            "/webhook",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webhook_accepts_valid_secret(monkeypatch):
    custom_settings = Settings(
        BOT_MODE="webhook",
        WEBHOOK_SECRET="my-valid-secret",
        WEBHOOK_PATH="/webhook",
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: custom_settings)
    monkeypatch.setattr("app.api.routes.webhook.get_settings", lambda: custom_settings)

    mock_bot = AsyncMock()
    mock_dp = AsyncMock()
    set_webhook_bot_and_dispatcher(mock_bot, mock_dp)

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/webhook",
            json={"update_id": 12345},
            headers={"X-Telegram-Bot-Api-Secret-Token": "my-valid-secret"},
        )
        assert resp.status_code == 200
        assert mock_dp.feed_update.called
