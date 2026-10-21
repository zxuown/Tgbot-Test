"""Unit tests for AIService, MockAIProvider, and GeminiProvider."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.services.ai_schemas import AITaskParseSchema
from app.services.ai_service import (
    AINetworkError,
    AIQuotaError,
    AIService,
    AITimeoutError,
    GeminiProvider,
    MockAIProvider,
)


@pytest.mark.asyncio
async def test_mock_ai_provider_parse_task():
    provider = MockAIProvider()
    service = AIService(provider=provider)

    text = "Подготовить презентацию для клиента к пятнице, выделить 2 часа, высокий приоритет"
    parsed = await service.parse_task_from_text(text)

    assert parsed is not None
    assert "title" in parsed
    assert parsed["priority"] == "high"
    assert parsed["estimated_minutes"] == 120
    assert parsed["category"] == "Работа"
    assert parsed["due_date"] is not None
    assert len(parsed.get("subtasks", [])) > 0


@pytest.mark.asyncio
async def test_mock_ai_provider_analyze_thought():
    service = AIService(provider=MockAIProvider())
    thought = "Нужно разобраться с сайтом, поговорить с дизайнером, проверить рекламу и налоги"
    result = await service.analyze_thought(thought)

    assert "AI-разбор" in result
    assert "задачи" in result.lower()
    assert "дедлайн" in result.lower()


@pytest.mark.asyncio
async def test_mock_ai_provider_plan_day():
    service = AIService(provider=MockAIProvider())
    result = await service.plan_day("У меня 4 часа, нужно сделать презентацию")

    assert "план на день" in result.lower()
    assert "фокус" in result.lower()


@pytest.mark.asyncio
async def test_mock_ai_provider_decompose():
    service = AIService(provider=MockAIProvider())
    result = await service.decompose_task("Запуск интернет-магазина", "Полный цикл от дизайна до оплаты")

    assert "декомпозиция" in result.lower()
    assert "этап" in result.lower()


@pytest.mark.asyncio
async def test_mock_ai_provider_coaching():
    service = AIService(provider=MockAIProvider())
    result = await service.coaching("Почему я постоянно откладываю эту задачу?")

    assert "коучинг" in result.lower()
    assert "шаг" in result.lower()


@pytest.mark.asyncio
async def test_mock_ai_provider_weekly_review():
    service = AIService(provider=MockAIProvider())
    result = await service.weekly_review("Выполнено 12 задач, 3 фокус-сессии")

    assert "обзор" in result.lower()
    assert "достижения" in result.lower()


# ── GeminiProvider Unit Tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gemini_provider_complete_success():
    """Test successful Gemini response parsing."""
    provider = GeminiProvider(api_key="AIzaSyTestKey12345678", model="gemini-1.5-flash")

    mock_resp_data = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Привет! Это ответ Gemini."}]
                },
                "finishReason": "STOP",
            }
        ]
    }
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_data
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        result = await provider.complete(
            system_prompt="Ты полезный ассистент.",
            user_message="Привет!",
            response_format="text",
        )

        assert result == "Привет! Это ответ Gemini."
        assert mock_post.called
        kwargs = mock_post.call_args.kwargs
        assert kwargs["headers"]["x-goog-api-key"] == "AIzaSyTestKey12345678"
        assert kwargs["json"]["contents"][0]["parts"][0]["text"] == "Привет!"
        assert kwargs["json"]["system_instruction"]["parts"][0]["text"] == "Ты полезный ассистент."


@pytest.mark.asyncio
async def test_gemini_provider_json_mode():
    """Test Gemini JSON mode sets responseMimeType to application/json."""
    provider = GeminiProvider(api_key="AIzaSyTestKey12345678")

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"title": "Тест"}'}]}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        await provider.complete("sys", "usr", response_format="json")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.asyncio
async def test_gemini_provider_rate_limit_429():
    """Test HTTP 429 raises AIQuotaError."""
    provider = GeminiProvider(api_key="AIzaSyTestKey12345678")

    req = httpx.Request("POST", "https://api.test")
    resp = httpx.Response(429, text="Resource has been exhausted", request=req)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPStatusError("Rate limit", request=req, response=resp)

        with pytest.raises(AIQuotaError) as exc_info:
            await provider.complete("sys", "usr")
        assert "429" in str(exc_info.value) or "лимит" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_gemini_provider_timeout():
    """Test timeout raises AITimeoutError."""
    provider = GeminiProvider(api_key="AIzaSyTestKey12345678", timeout=5.0)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Read timed out")

        with pytest.raises(AITimeoutError):
            await provider.complete("sys", "usr")


@pytest.mark.asyncio
async def test_gemini_provider_network_error():
    """Test connection error raises AINetworkError."""
    provider = GeminiProvider(api_key="AIzaSyTestKey12345678")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(AINetworkError):
            await provider.complete("sys", "usr")


def test_gemini_provider_never_logs_api_key():
    """Verify raw API key is never exposed in repr or str."""
    raw_key = "AIzaSySecretLongKey987654321"
    provider = GeminiProvider(api_key=raw_key)

    repr_str = repr(provider)
    assert raw_key not in repr_str
    assert "..." in repr_str


# ── AIService Gemini Integration & Schema Validation ──────────────────────

def test_pydantic_schema_validation():
    """Test AITaskParseSchema parses and validates structured JSON."""
    raw_json = json.dumps({
        "title": "Сдать налоговый отчёт",
        "due_date": "2026-10-30",
        "due_time": "18:00",
        "priority": "high",
        "estimated_minutes": 60,
        "category": "Работа",
        "subtasks": ["Собрать выписки", "Заполнить форму"],
    })
    model = AITaskParseSchema.model_validate_json(raw_json)
    assert model.title == "Сдать налоговый отчёт"
    assert model.priority == "high"
    assert model.estimated_minutes == 60
    assert len(model.subtasks) == 2


@pytest.mark.asyncio
async def test_ai_service_gemini_selection(monkeypatch):
    """Test AIService selects GeminiProvider when AI_PROVIDER='gemini' and key is present."""
    fake_settings = Settings(
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="AIzaSyValidKey12345",
        GEMINI_MODEL="gemini-1.5-flash",
    )
    monkeypatch.setattr("app.services.ai_service.get_settings", lambda: fake_settings)

    service = AIService()
    assert isinstance(service.provider, GeminiProvider)
    assert service.provider.model == "gemini-1.5-flash"


@pytest.mark.asyncio
async def test_ai_service_gemini_fallback_when_no_key(monkeypatch):
    """Test AIService falls back to MockAIProvider when GEMINI_API_KEY is empty."""
    fake_settings = Settings(
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="",
        APP_ENV="development",
    )
    monkeypatch.setattr("app.services.ai_service.get_settings", lambda: fake_settings)

    service = AIService()
    assert isinstance(service.provider, MockAIProvider)


@pytest.mark.asyncio
async def test_parse_task_json_repair_retry():
    """Test that AIService retries when model first returns broken JSON, and recovers."""
    mock_provider = AsyncMock(spec=GeminiProvider)

    # First attempt: broken JSON
    # Second attempt (repair): valid JSON
    valid_json = json.dumps({
        "title": "Купить билеты в театр",
        "due_date": "2026-11-01",
        "due_time": "20:00",
        "priority": "medium",
        "estimated_minutes": 15,
        "category": "Личное",
        "subtasks": [],
    })
    mock_provider.complete.side_effect = [
        "Вот ваш ответ: {title: 'Купить билеты', broken...}",  # Malformed
        valid_json,  # Clean JSON on retry
    ]

    service = AIService(provider=mock_provider)
    result = await service.parse_task_from_text("Купить билеты в театр к 1 ноября в 20:00")

    assert mock_provider.complete.call_count == 2
    assert result["title"] == "Купить билеты в театр"
    assert result["due_time"] == "20:00"


@pytest.mark.asyncio
async def test_parse_task_fallback_on_total_failure():
    """Test that AIService falls back to local parsing without crashing if all retries fail."""
    mock_provider = AsyncMock(spec=GeminiProvider)
    mock_provider.complete.side_effect = [
        "Broken attempt 1",
        "Broken attempt 2",
    ]

    service = AIService(provider=mock_provider)
    # Should not raise exception
    result = await service.parse_task_from_text("Позвонить клиенту завтра в 14:00")

    assert result is not None
    assert "Позвонить клиенту" in result["title"]
    assert result["due_time"] == "14:00"


def test_ai_input_truncation(monkeypatch):
    """Test that input text exceeding AI_MAX_INPUT_CHARS is truncated."""
    fake_settings = Settings(AI_MAX_INPUT_CHARS=100)
    monkeypatch.setattr("app.services.ai_service.get_settings", lambda: fake_settings)

    service = AIService(provider=MockAIProvider())
    long_text = "А" * 500
    truncated = service._truncate_input(long_text)

    assert len(truncated) == 100


@pytest.mark.asyncio
async def test_gemini_provider_fallback_on_503(monkeypatch):
    """Test that GeminiProvider automatically tries fallback models when the primary model returns 503."""
    provider = GeminiProvider(api_key="AIzaSyTestKey12345678", model="gemini-3.8-flash")

    # Mock _call_api to fail on gemini-3.8-flash and succeed on gemini-flash-lite-latest
    calls = []

    async def mock_call(model, system_prompt, user_message, response_format):
        calls.append(model)
        if model == "gemini-3.8-flash":
            req = httpx.Request("POST", "https://generativelanguage.googleapis.com")
            resp = httpx.Response(503, text='{"error": {"code": 503, "message": "High demand"}}', request=req)
            raise httpx.HTTPStatusError("503 Service Unavailable", request=req, response=resp)
        return "Успешный ответ от резервной модели"

    monkeypatch.setattr(provider, "_call_api", mock_call)

    result = await provider.complete("sys", "user")
    assert result == "Успешный ответ от резервной модели"
    assert calls[0] == "gemini-3.8-flash"
    assert "gemini-flash-lite-latest" in calls
    # Check that active model switched to the working fallback model
    assert provider.model == "gemini-flash-lite-latest"
