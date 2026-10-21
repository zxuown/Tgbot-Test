"""Application configuration via Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class ConfigurationError(Exception):
    """Raised when environment configuration is invalid for the current environment."""

    pass


def normalize_database_url(url: str) -> str:
    """
    Normalize database URL for SQLAlchemy asyncpg engine.

    Converts standard cloud URLs (postgres://, postgresql://) to asyncpg driver,
    and replaces sslmode=require with ssl=require for asyncpg compatibility.
    """
    if not url:
        return url
    trimmed = url.strip()
    if trimmed.startswith("postgres://"):
        trimmed = "postgresql+asyncpg://" + trimmed[len("postgres://") :]
    elif trimmed.startswith("postgresql://") and not trimmed.startswith("postgresql+asyncpg://"):
        trimmed = "postgresql+asyncpg://" + trimmed[len("postgresql://") :]
    elif trimmed.startswith("sqlite://") and not trimmed.startswith("sqlite+aiosqlite://"):
        trimmed = "sqlite+aiosqlite://" + trimmed[len("sqlite://") :]

    if "sslmode=" in trimmed:
        trimmed = (
            trimmed.replace("sslmode=require", "ssl=require")
            .replace("sslmode=prefer", "ssl=prefer")
            .replace("sslmode=disable", "ssl=disable")
        )
    return trimmed


class Settings(BaseSettings):
    """Main application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Mode & Cloud Worker ---
    # Options: "polling" (bot + scheduler + optional API), "webhook" (FastAPI + webhook),
    #          "worker" (pure background worker, no HTTP), "api" (FastAPI only)
    BOT_MODE: str = "polling"
    AUTO_MIGRATE: bool = True
    RUN_API_WITH_POLLING: bool = True

    # --- Telegram ---
    BOT_TOKEN: str = ""
    WEBHOOK_URL: str = ""
    WEBHOOK_SECRET: str = "changeme"
    WEBHOOK_PATH: str = "/webhook"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://focus:focus@localhost:5432/focus"
    DATABASE_ECHO: bool = False

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Application ---
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "auto"  # "auto", "json", "console"
    SECRET_KEY: str = "change-me-to-random-string"

    # --- AI Provider ---
    AI_PROVIDER: str = "mock"
    AI_API_KEY: str = ""
    AI_API_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    AI_MAX_INPUT_CHARS: int = 2000

    # --- STT ---
    STT_PROVIDER: str = "mock"
    STT_API_KEY: str = ""
    STT_API_BASE_URL: str = ""

    # --- Admin ---
    ADMIN_TELEGRAM_IDS: str = ""

    # --- Mini App ---
    MINI_APP_URL: str = ""

    # --- Limits ---
    FREE_MONTHLY_AI_LIMIT: int = 10
    FREE_MAX_TASKS: int = 30
    FREE_MAX_HABITS: int = 5

    # --- Defaults ---
    DEFAULT_TIMEZONE: str = "Europe/Moscow"
    DEFAULT_LANGUAGE: str = "ru"

    # --- Rate Limits ---
    RATE_LIMIT_MESSAGES_PER_MINUTE: int = 30
    RATE_LIMIT_AI_PER_MINUTE: int = 5

    # --- Server / Cloud Port ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    PORT: int | None = None  # Injected by Render/Railway

    @property
    def server_port(self) -> int:
        """Effective server port, prioritizing cloud $PORT over API_PORT."""
        return self.PORT if self.PORT is not None else self.API_PORT

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def use_webhook(self) -> bool:
        return self.BOT_MODE == "webhook" or bool(self.WEBHOOK_URL and self.BOT_MODE != "polling")

    @property
    def admin_ids(self) -> list[int]:
        if not self.ADMIN_TELEGRAM_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_TELEGRAM_IDS.split(",") if x.strip()]

    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for tools requiring non-async drivers."""
        url = self.DATABASE_URL
        if "+asyncpg" in url:
            return url.replace("+asyncpg", "")
        if "+aiosqlite" in url:
            return url.replace("+aiosqlite", "")
        return url

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_and_normalize_database_url(cls, v: str) -> str:
        return normalize_database_url(v)

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return upper

    @field_validator("BOT_MODE")
    @classmethod
    def validate_bot_mode(cls, v: str) -> str:
        allowed = {"polling", "webhook", "worker", "api"}
        lower = v.lower().strip()
        if lower not in allowed:
            raise ValueError(f"BOT_MODE must be one of {allowed}")
        return lower

    def validate_config(self) -> None:
        """Validate environment configuration, enforcing strict production rules."""
        errors: list[str] = []

        placeholder_tokens = {"", "your-bot-token-here", "PUT_YOUR_TOKEN_HERE"}
        if self.BOT_MODE != "api" and (not self.BOT_TOKEN or self.BOT_TOKEN in placeholder_tokens):
            errors.append("BOT_TOKEN не задан или содержит шаблонное значение.")

        if self.is_production:
            insecure_secrets = {"", "change-me-to-random-string", "changeme", "secret", "123456"}
            if self.SECRET_KEY in insecure_secrets or len(self.SECRET_KEY) < 16:
                errors.append(
                    "SECRET_KEY имеет небезопасное или слишком короткое (<16 симв.) значение. "
                    "В production сгенерируйте надежный ключ (например: openssl rand -hex 32)."
                )

            if self.DATABASE_URL.startswith("sqlite"):
                errors.append(
                    "В production-режиме (APP_ENV=production) запрещено использовать локальный SQLite. "
                    "Укажите внешний DATABASE_URL для PostgreSQL (например: postgresql+asyncpg://...)."
                )

            if self.AI_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
                errors.append(
                    "AI_PROVIDER='gemini', но GEMINI_API_KEY не задан! "
                    "В production-режиме автоматический откат на Mock AI запрещен."
                )

            if self.AI_PROVIDER == "openai" and not self.AI_API_KEY:
                errors.append(
                    "AI_PROVIDER='openai', но AI_API_KEY не задан! "
                    "В production-режиме автоматический откат на Mock AI запрещен."
                )

            if self.BOT_MODE == "webhook" and (not self.WEBHOOK_URL or not self.WEBHOOK_URL.startswith("https://")):
                errors.append(
                    "Для BOT_MODE='webhook' требуется валидный публичный HTTPS URL в WEBHOOK_URL "
                    "(например: https://focus-bot.onrender.com)."
                )

        if errors:
            formatted = "\n".join(f"  [-] {err}" for err in errors)
            raise ConfigurationError(
                f"\n{'=' * 65}\nОШИБКА КОНФИГУРАЦИИ ПРИЛОЖЕНИЯ ({self.APP_ENV.upper()}):\n{formatted}\n{'=' * 65}\n"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
