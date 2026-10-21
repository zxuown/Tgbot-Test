"""Utility functions for date/time formatting, natural language parsing, and visual helpers."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_RU_MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

_RU_MONTHS_NAMES = {
    "январ": 1,
    "феврал": 2,
    "март": 3,
    "апрел": 4,
    "ма": 5,
    "мая": 5,
    "июн": 6,
    "июл": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}

_RU_WEEKDAYS = {
    0: "понедельник",
    1: "вторник",
    2: "среда",
    3: "четверг",
    4: "пятница",
    5: "суббота",
    6: "воскресенье",
}

_WEEKDAY_NAMES = {
    "понедельник": 0,
    "пн": 0,
    "вторник": 1,
    "вт": 1,
    "сред": 2,
    "ср": 2,
    "среду": 2,
    "четверг": 3,
    "чт": 3,
    "пятниц": 4,
    "пятницу": 4,
    "пт": 4,
    "суббот": 5,
    "субботу": 5,
    "сб": 5,
    "воскресень": 6,
    "воскресенье": 6,
    "вс": 6,
}


def get_user_now(timezone_str: str = "Europe/Moscow") -> datetime:
    """Get current datetime localized to user's timezone."""
    try:
        tz = ZoneInfo(timezone_str)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("Europe/Moscow")
    return datetime.now(tz)


def get_user_today(timezone_str: str = "Europe/Moscow") -> date:
    """Get today's date in user's timezone."""
    return get_user_now(timezone_str).date()


def format_date_ru(d: date) -> str:
    """Format date to friendly Russian string, e.g. 'вторник, 21 октября'."""
    weekday = _RU_WEEKDAYS.get(d.weekday(), "")
    month = _RU_MONTHS.get(d.month, "")
    return f"{weekday}, {d.day} {month}"


def format_minutes(minutes: int | None) -> str:
    """Format minutes to readable string, e.g. '2 ч 30 мин' or '45 мин'."""
    if not minutes or minutes <= 0:
        return "0 мин"
    hours = minutes // 60
    rem = minutes % 60
    if hours > 0 and rem > 0:
        return f"{hours} ч {rem} мин"
    if hours > 0:
        return f"{hours} ч"
    return f"{rem} мин"


def priority_emoji(priority: str) -> str:
    """Get emoji for priority level."""
    mapping = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🔴",
        "urgent": "🚨",
    }
    return mapping.get(priority.lower(), "🟡")


def status_emoji(status: str) -> str:
    """Get emoji for task status."""
    mapping = {
        "inbox": "📥",
        "planned": "📅",
        "in_progress": "🔄",
        "completed": "✅",
        "cancelled": "❌",
    }
    return mapping.get(status.lower(), "📌")


def validate_time_input(value: str | None) -> tuple[time | None, str | None, str | None]:
    """
    Validate and parse user-entered time string.

    Returns:
        tuple of (parsed_time, error_code, error_message)
        error_code: None, 'EMPTY', 'INVALID_HOUR', 'INVALID_MINUTE', 'INVALID_FORMAT'
    """
    if value is None:
        return None, "EMPTY", "Время не указано."

    cleaned = value.strip()
    if not cleaned:
        return None, "EMPTY", "Время не указано."

    # Strip common Russian prepositions: "в 14", "к 14:00", "до 18.00"
    cleaned = re.sub(r"^(?:в|к|до)\s+", "", cleaned, flags=re.IGNORECASE).strip()
    if not cleaned:
        return None, "EMPTY", "Время не указано."

    # Pattern 1: HH:MM, HH.MM, HH MM
    match_two = re.fullmatch(r"(\d{1,2})[:.\s](\d{1,2})", cleaned)
    if match_two:
        h, m = int(match_two.group(1)), int(match_two.group(2))
        if not (0 <= h <= 23):
            return None, "INVALID_HOUR", "Время должно быть в диапазоне от 00:00 до 23:59. Например: 14:00 или 8"
        if not (0 <= m <= 59):
            return None, "INVALID_MINUTE", "Минуты должны быть от 00 до 59. Например: 14:30"
        return time(hour=h, minute=m), None, None

    # Pattern 2: bare hour "14", "8", "08"
    match_one = re.fullmatch(r"(\d{1,2})", cleaned)
    if match_one:
        h = int(match_one.group(1))
        if not (0 <= h <= 23):
            return None, "INVALID_HOUR", "Время должно быть в диапазоне от 00:00 до 23:59. Например: 14:00 или 8"
        return time(hour=h, minute=0), None, None

    return None, "INVALID_FORMAT", "Не удалось распознать время. Напиши, например, «14:00», «14.00» или «14»:"


def parse_time_input(value: str | None) -> time | None:
    """
    Parse time string into datetime.time safely.
    Accepts: '14:00', '14.00', '14', '8:05', '08:05', '8 05', '00:00', '23:59'.
    Rejects: '30:00', '14:70', '25', '12:99', 'abc', ''.
    Never raises an exception; returns None on invalid.
    """
    try:
        t, _, _ = validate_time_input(value)
        return t
    except Exception:
        return None


def parse_time(text: str | None) -> time | None:
    """
    Search and parse time from arbitrary text/sentence (e.g. 'Позвонить завтра в 14:00').
    Uses parse_time_input if standalone, or regex search within sentence.
    """
    if not text:
        return None

    # Try exact/clean match first
    direct = parse_time_input(text)
    if direct:
        return direct

    # Search within natural language sentence
    match = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", text)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        return time(hour=h, minute=m)

    match_hour = re.search(r"\b(?:в|к)\s+([01]?\d|2[0-3])\b", text.lower())
    if match_hour:
        return time(hour=int(match_hour.group(1)), minute=0)

    return None


def parse_date_ru(text: str, base_date: date | None = None) -> date | None:
    """Parse relative or absolute date from Russian text."""
    if not text:
        return None
    today = base_date or date.today()
    lower = text.strip().lower()

    if "сегодня" in lower:
        return today
    if "послезавтра" in lower:
        return today + timedelta(days=2)
    if "завтра" in lower:
        return today + timedelta(days=1)
    if "вчера" in lower:
        return today - timedelta(days=1)

    # Check weekdays: e.g. "к пятнице", "в субботу", "пятница"
    for word, target_weekday in _WEEKDAY_NAMES.items():
        if re.search(r"\b" + re.escape(word), lower):
            current_weekday = today.weekday()
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # Target day already happened this week, move to next week
                days_ahead += 7
            return today + timedelta(days=days_ahead)

    # Format: DD.MM.YYYY
    match_dmy = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", lower)
    if match_dmy:
        try:
            return date(int(match_dmy.group(3)), int(match_dmy.group(2)), int(match_dmy.group(1)))
        except ValueError:
            pass

    # Format: DD.MM
    match_dm = re.search(r"\b(\d{1,2})\.(\d{1,2})\b", lower)
    if match_dm:
        try:
            day, month = int(match_dm.group(1)), int(match_dm.group(2))
            year = today.year
            res = date(year, month, day)
            if res < today:
                res = date(year + 1, month, day)
            return res
        except ValueError:
            pass

    # Format: YYYY-MM-DD
    match_iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", lower)
    if match_iso:
        try:
            return date(int(match_iso.group(1)), int(match_iso.group(2)), int(match_iso.group(3)))
        except ValueError:
            pass

    # Format: "21 октября", "5 мая"
    match_text_month = re.search(r"\b(\d{1,2})\s+([а-яё]+)\b", lower)
    if match_text_month:
        day = int(match_text_month.group(1))
        month_word = match_text_month.group(2)
        for prefix, month_num in _RU_MONTHS_NAMES.items():
            if month_word.startswith(prefix):
                try:
                    res = date(today.year, month_num, day)
                    if res < today:
                        res = date(today.year + 1, month_num, day)
                    return res
                except ValueError:
                    pass

    return None


def clean_telegram_html(text: str | None) -> str:
    """
    Clean text for safe rendering in Telegram with HTML parse mode.

    - Replaces <br> tags with newlines
    - Converts <li> tags to bullet points ('• ')
    - Strips unsupported tags (<ul>, <ol>, <p>, <div>, etc.)
    - Leaves supported tags intact: <b>, <i>, <code>, <pre>, <a>, <u>, <s>, <blockquote>
    """
    if not text:
        return ""
    cleaned = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*li\s*>", "• ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*/\s*li\s*>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*/?\s*(?:ul|ol|p|div|span|h[1-6]|table|tr|td|th)[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
