"""Integration tests for FastAPI endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.app import create_app
from app.db.models.user import User
from app.db.session import get_session


def make_valid_init_data(telegram_id: int, bot_token: str) -> str:
    """Generate cryptographically valid Telegram initData for tests."""
    auth_date = int(time.time())
    user_data = json.dumps({"id": telegram_id, "first_name": "Test", "username": "testuser"})
    data_pairs = [
        f"auth_date={auth_date}",
        "query_id=AAHdF6IQAAAAAN0XohDhrOrc",
        f"user={user_data}",
    ]
    data_pairs.sort()
    data_check_string = "\n".join(data_pairs)

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    return f"query_id=AAHdF6IQAAAAAN0XohDhrOrc&user={user_data}&auth_date={auth_date}&hash={computed_hash}"


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncClient:
    """Create test client with overridden DB session."""
    test_app = create_app()

    async def override_get_session():
        yield db_session

    test_app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_endpoints(api_client: AsyncClient):
    res = await api_client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_unauthorized_without_header(api_client: AsyncClient):
    res = await api_client.get("/api/v1/tasks")
    assert res.status_code == 422 or res.status_code == 401
    data = res.json()
    assert "error" in data or "detail" in data


@pytest.mark.asyncio
async def test_tasks_crud_with_auth(api_client: AsyncClient, test_user: User, monkeypatch):
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "BOT_TOKEN", "test_token_123")

    init_data = make_valid_init_data(test_user.telegram_id, "test_token_123")
    headers = {"X-Telegram-Init-Data": init_data}

    # 1. Create Task
    create_res = await api_client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"title": "Интеграционная задача", "priority": "high", "estimated_minutes": 45},
    )
    assert create_res.status_code == 201
    task_data = create_res.json()
    assert task_data["title"] == "Интеграционная задача"
    task_id = task_data["id"]

    # 2. Get Tasks List
    list_res = await api_client.get("/api/v1/tasks", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 3. Update Task
    update_res = await api_client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=headers,
        json={"status": "completed"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "completed"

    # 4. Delete Task
    del_res = await api_client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_today_and_stats_endpoints(api_client: AsyncClient, test_user: User, monkeypatch):
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "BOT_TOKEN", "test_token_123")

    init_data = make_valid_init_data(test_user.telegram_id, "test_token_123")
    headers = {"X-Telegram-Init-Data": init_data}

    # Today
    today_res = await api_client.get("/api/v1/today", headers=headers)
    assert today_res.status_code == 200
    assert "date" in today_res.json()

    # Stats
    stats_res = await api_client.get("/api/v1/stats", headers=headers)
    assert stats_res.status_code == 200
    assert "tasks_total" in stats_res.json()


@pytest.mark.asyncio
async def test_ai_analyze_endpoint(api_client: AsyncClient, test_user: User, monkeypatch):
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "BOT_TOKEN", "test_token_123")

    init_data = make_valid_init_data(test_user.telegram_id, "test_token_123")
    headers = {"X-Telegram-Init-Data": init_data}

    res = await api_client.post(
        "/api/v1/ai/analyze",
        headers=headers,
        json={"text": "Подготовить отчет к среде", "mode": "task"},
    )
    assert res.status_code == 200
    assert "result" in res.json()
