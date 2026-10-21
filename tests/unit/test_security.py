"""Unit tests for security utilities."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

from app.core.security import escape_html, truncate_text, validate_telegram_init_data


def test_escape_html():
    raw = "<script>alert('xss');</script> & \"foo\" > bar"
    escaped = escape_html(raw)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&amp;" in escaped
    assert "&gt;" in escaped


def test_truncate_text():
    short = "Привет"
    assert truncate_text(short, 10) == "Привет"
    long_text = "А" * 50
    truncated = truncate_text(long_text, 10)
    assert len(truncated) == 10
    assert truncated.endswith("...")


def test_validate_telegram_init_data_valid():
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    auth_date = int(time.time())
    user_data = json.dumps({"id": 12345, "first_name": "Test", "username": "testuser"})

    data_pairs = [
        f"auth_date={auth_date}",
        "query_id=AAHdF6IQAAAAAN0XohDhrOrc",
        f"user={user_data}",
    ]
    data_pairs.sort()
    data_check_string = "\n".join(data_pairs)

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    init_data = f"query_id=AAHdF6IQAAAAAN0XohDhrOrc&user={user_data}&auth_date={auth_date}&hash={computed_hash}"

    parsed = validate_telegram_init_data(init_data, bot_token=bot_token)
    assert parsed is not None
    assert parsed["user"]["id"] == 12345
    assert parsed["user"]["username"] == "testuser"


def test_validate_telegram_init_data_invalid_hash():
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    init_data = "query_id=AAHdF6IQAAAAAN0XohDhrOrc&auth_date=1600000000&hash=invalid_hash"
    assert validate_telegram_init_data(init_data, bot_token=bot_token) is None


def test_validate_telegram_init_data_expired():
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    old_auth_date = int(time.time()) - 100000  # older than 24h (86400s)

    data_pairs = [f"auth_date={old_auth_date}", "query_id=AAHdF6IQ"]
    data_pairs.sort()
    data_check_string = "\n".join(data_pairs)

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    init_data = f"query_id=AAHdF6IQ&auth_date={old_auth_date}&hash={computed_hash}"
    assert validate_telegram_init_data(init_data, bot_token=bot_token) is None
