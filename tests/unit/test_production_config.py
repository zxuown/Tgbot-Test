"""Tests for production deployment configuration, validation, and URL normalization."""

from __future__ import annotations

import pytest

from app.core.config import ConfigurationError, Settings, normalize_database_url


def test_normalize_database_url_postgres():
    # Render / Heroku / Supabase default format: postgres://
    url = "postgres://focus_user:secret_pass@ep-cool-db.render.com:5432/focus_db"
    normalized = normalize_database_url(url)
    assert normalized.startswith("postgresql+asyncpg://")
    assert "focus_user:secret_pass@ep-cool-db.render.com:5432/focus_db" in normalized


def test_normalize_database_url_postgresql():
    # Standard format without async driver: postgresql://
    url = "postgresql://user:pass@localhost:5432/dbname"
    normalized = normalize_database_url(url)
    assert normalized == "postgresql+asyncpg://user:pass@localhost:5432/dbname"


def test_normalize_database_url_sslmode():
    # Asyncpg expects ssl=require instead of sslmode=require
    url = "postgres://user:pass@host:5432/db?sslmode=require"
    normalized = normalize_database_url(url)
    assert "ssl=require" in normalized
    assert "sslmode=" not in normalized


def test_normalize_database_url_sqlite():
    # Preserves or adds aiosqlite driver
    assert normalize_database_url("sqlite:///focus.db") == "sqlite+aiosqlite:///focus.db"
    assert normalize_database_url("sqlite+aiosqlite:///focus.db") == "sqlite+aiosqlite:///focus.db"


def test_validate_config_development_mode_allows_sqlite():
    # In development mode, SQLite and mock AI are allowed
    settings = Settings(
        APP_ENV="development",
        BOT_TOKEN="123456789:ABCdef-test",
        DATABASE_URL="sqlite+aiosqlite:///focus.db",
        SECRET_KEY="change-me-to-random-string",
        AI_PROVIDER="mock",
    )
    # Should not raise
    settings.validate_config()


def test_validate_config_production_rejects_insecure_secret():
    settings = Settings(
        APP_ENV="production",
        BOT_TOKEN="123456789:ABCdef-test",
        DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/focus",
        SECRET_KEY="change-me-to-random-string",
        AI_PROVIDER="mock",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        settings.validate_config()
    assert "SECRET_KEY" in str(exc_info.value)


def test_validate_config_production_rejects_sqlite():
    settings = Settings(
        APP_ENV="production",
        BOT_TOKEN="123456789:ABCdef-test",
        DATABASE_URL="sqlite+aiosqlite:///focus.db",
        SECRET_KEY="0123456789abcdef0123456789abcdef",
        AI_PROVIDER="mock",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        settings.validate_config()
    assert "SQLite" in str(exc_info.value)


def test_validate_config_production_rejects_missing_gemini_key():
    settings = Settings(
        APP_ENV="production",
        BOT_TOKEN="123456789:ABCdef-test",
        DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/focus",
        SECRET_KEY="0123456789abcdef0123456789abcdef",
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        settings.validate_config()
    assert "GEMINI_API_KEY" in str(exc_info.value)


def test_validate_config_production_rejects_invalid_webhook_url():
    settings = Settings(
        APP_ENV="production",
        BOT_MODE="webhook",
        BOT_TOKEN="123456789:ABCdef-test",
        DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/focus",
        SECRET_KEY="0123456789abcdef0123456789abcdef",
        AI_PROVIDER="mock",
        WEBHOOK_URL="http://not-https.com",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        settings.validate_config()
    assert "WEBHOOK_URL" in str(exc_info.value)


def test_validate_config_production_success():
    settings = Settings(
        APP_ENV="production",
        BOT_TOKEN="123456789:ABCdef-test",
        DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/focus",
        SECRET_KEY="0123456789abcdef0123456789abcdef",
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="AIzaSyValidProductionKey12345",
        BOT_MODE="polling",
    )
    # Should pass without raising
    settings.validate_config()


def test_server_port_uses_cloud_port_when_injected():
    s1 = Settings(API_PORT=8000, PORT=10000)
    assert s1.server_port == 10000

    s2 = Settings(API_PORT=8000, PORT=None)
    assert s2.server_port == 8000
