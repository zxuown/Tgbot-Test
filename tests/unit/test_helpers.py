"""Unit tests for app.utils.helpers."""

from __future__ import annotations

from datetime import date, time, timedelta

from app.utils.helpers import (
    format_date_ru,
    format_minutes,
    parse_date_ru,
    parse_time,
    parse_time_input,
    priority_emoji,
    status_emoji,
    validate_time_input,
)


def test_format_minutes():
    assert format_minutes(0) == "0 мин"
    assert format_minutes(None) == "0 мин"
    assert format_minutes(30) == "30 мин"
    assert format_minutes(60) == "1 ч"
    assert format_minutes(90) == "1 ч 30 мин"
    assert format_minutes(150) == "2 ч 30 мин"


def test_format_date_ru():
    d = date(2026, 10, 21)  # Wednesday
    res = format_date_ru(d)
    assert "среда" in res
    assert "21" in res
    assert "октября" in res


def test_parse_date_ru_relative():
    base = date(2026, 10, 21)
    assert parse_date_ru("сегодня", base) == base
    assert parse_date_ru("завтра", base) == base + timedelta(days=1)
    assert parse_date_ru("послезавтра", base) == base + timedelta(days=2)
    assert parse_date_ru("вчера", base) == base - timedelta(days=1)


def test_parse_date_ru_weekdays():
    base = date(2026, 10, 21)  # Wednesday
    # Friday is 2 days ahead
    friday = parse_date_ru("к пятнице", base)
    assert friday == base + timedelta(days=2)
    assert friday.weekday() == 4


def test_parse_date_ru_formats():
    base = date(2026, 10, 21)
    assert parse_date_ru("25.10.2026", base) == date(2026, 10, 25)
    assert parse_date_ru("2026-11-05", base) == date(2026, 11, 5)
    assert parse_date_ru("15 ноября", base) == date(2026, 11, 15)


def test_parse_time():
    assert parse_time("14:00") == time(14, 0)
    assert parse_time("9:30") == time(9, 30)
    assert parse_time("в 18:45") == time(18, 45)
    assert parse_time("14.30") == time(14, 30)
    assert parse_time("в 15") == time(15, 0)
    assert parse_time("не указано") is None


def test_parse_time_input_all_required_cases():
    # Valid cases
    assert parse_time_input("14:00") == time(14, 0)
    assert parse_time_input("14.00") == time(14, 0)
    assert parse_time_input("14") == time(14, 0)
    assert parse_time_input("8:05") == time(8, 5)
    assert parse_time_input("08:05") == time(8, 5)
    assert parse_time_input("8 05") == time(8, 5)
    assert parse_time_input("00:00") == time(0, 0)
    assert parse_time_input("23:59") == time(23, 59)
    assert parse_time_input("  14:00  ") == time(14, 0)

    # Invalid cases
    assert parse_time_input("30:00") is None
    assert parse_time_input("24:00") is None
    assert parse_time_input("25") is None
    assert parse_time_input("14:60") is None
    assert parse_time_input("14:70") is None
    assert parse_time_input("12:99") is None
    assert parse_time_input("abc") is None
    assert parse_time_input("") is None
    assert parse_time_input("   ") is None
    assert parse_time_input(None) is None


def test_validate_time_input_error_messages():
    # Invalid hour
    t, err, msg = validate_time_input("30:00")
    assert t is None
    assert err == "INVALID_HOUR"
    assert "00:00 до 23:59" in msg

    t, err, msg = validate_time_input("24:00")
    assert t is None
    assert err == "INVALID_HOUR"

    t, err, msg = validate_time_input("25")
    assert t is None
    assert err == "INVALID_HOUR"

    # Invalid minute
    t, err, msg = validate_time_input("14:70")
    assert t is None
    assert err == "INVALID_MINUTE"
    assert "Минуты должны быть от 00 до 59" in msg

    t, err, msg = validate_time_input("14:60")
    assert t is None
    assert err == "INVALID_MINUTE"

    t, err, msg = validate_time_input("12:99")
    assert t is None
    assert err == "INVALID_MINUTE"

    # Invalid format / letters
    t, err, msg = validate_time_input("abc")
    assert t is None
    assert err == "INVALID_FORMAT"

    # Empty
    t, err, msg = validate_time_input("")
    assert t is None
    assert err == "EMPTY"
    t, err, msg = validate_time_input("   ")
    assert t is None
    assert err == "EMPTY"


def test_emojis():
    assert priority_emoji("high") == "🔴"
    assert priority_emoji("low") == "🟢"
    assert status_emoji("completed") == "✅"
    assert status_emoji("in_progress") == "🔄"


def test_clean_telegram_html():
    from app.utils.helpers import clean_telegram_html

    assert clean_telegram_html("") == ""
    assert clean_telegram_html(None) == ""

    # Replaces <li> with bullet point and removes <ul>/<ol>
    raw = "<ul><li>Первый пункт</li><li>Второй пункт</li></ul>"
    cleaned = clean_telegram_html(raw)
    assert "• Первый пункт" in cleaned
    assert "• Второй пункт" in cleaned
    assert "<ul>" not in cleaned
    assert "<li>" not in cleaned

    # Replaces <br> with newline
    assert clean_telegram_html("Привет<br>мир!") == "Привет\nмир!"

    # Preserves valid Telegram tags
    valid = "<b>Жирный</b> <i>Курсив</i> <code>Код</code>"
    assert clean_telegram_html(valid) == valid
