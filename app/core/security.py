"""Security utilities: Telegram WebApp initData validation, text escaping, etc."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qs, unquote

from aiogram.utils.markdown import hbold, hitalic  # noqa: F401

from app.core.config import get_settings


def validate_telegram_init_data(init_data: str, bot_token: str | None = None) -> dict[str, Any] | None:
    """
    Validate Telegram WebApp initData and return parsed data.
    Returns None if validation fails.
    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    token = bot_token or get_settings().BOT_TOKEN
    if not token or not init_data:
        return None

    try:
        parsed = parse_qs(init_data, keep_blank_values=True)
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return None

        # Build data check string
        data_pairs = []
        for key, values in sorted(parsed.items()):
            if key == "hash":
                continue
            data_pairs.append(f"{key}={values[0]}")
        data_check_string = "\n".join(data_pairs)

        # Compute HMAC
        secret_key = hmac.new(
            b"WebAppData", token.encode("utf-8"), hashlib.sha256
        ).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        # Check auth_date is not too old (allow 24h)
        auth_date_str = parsed.get("auth_date", [None])[0]
        if auth_date_str:
            auth_date = int(auth_date_str)
            if time.time() - auth_date > 86400:
                return None

        # Parse user data
        result: dict[str, Any] = {}
        for key, values in parsed.items():
            val = unquote(values[0])
            if key == "user":
                result[key] = json.loads(val)
            else:
                result[key] = val

        return result

    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def truncate_text(text: str, max_length: int = 4000) -> str:
    """Truncate text to fit Telegram message limits."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
