"""Inline and Reply keyboards for the Focus Telegram bot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.core.config import get_settings
from app.i18n.texts import Texts
from app.utils.helpers import priority_emoji, status_emoji

if TYPE_CHECKING:
    from app.db.models.habit import Habit
    from app.db.models.task import Task


# ── Callback Data Factories ─────────────────────────────────────────────────

class TaskCallback(CallbackData, prefix="task"):
    action: str  # view, complete, delete, toggle_imp, back, page, filter, create
    task_id: int = 0
    page: int = 1
    filter_type: str = "all"


class HabitCallback(CallbackData, prefix="habit"):
    action: str  # complete, skip, pause, resume, delete, create, back
    habit_id: int = 0


class FocusCallback(CallbackData, prefix="focus"):
    action: str  # start, done, extend, postpone, complete_task
    minutes: int = 25
    session_id: int = 0
    task_id: int = 0


class AICallback(CallbackData, prefix="ai"):
    action: str  # mode, create_all, cancel, edit
    mode: str = "analyze"


class OnboardingCallback(CallbackData, prefix="onboard"):
    action: str  # role, timezone, skip
    value: str = ""


class SettingsCallback(CallbackData, prefix="set"):
    action: str  # toggle_morning, toggle_evening, upgrade_pro, reonboard, lang
    value: str = ""


# ── Reply Keyboards ─────────────────────────────────────────────────────────

def reply_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply menu keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.button(text=Texts.BTN_TODAY)
    builder.button(text=Texts.BTN_TASKS)
    builder.button(text=Texts.BTN_HABITS)
    builder.button(text=Texts.BTN_AI)
    builder.button(text=Texts.BTN_STATS)
    builder.button(text=Texts.BTN_SETTINGS)
    builder.adjust(3, 3)
    return builder.as_markup(resize_keyboard=True)


# ── Main Menu Inline Keyboard ───────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu inline keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text=Texts.BTN_CREATE_TASK, callback_data="act_create_task")
    builder.button(text=Texts.BTN_PLAN_DAY, callback_data="act_plan_day")
    builder.button(text=Texts.BTN_ADD_HABIT, callback_data="act_add_habit")
    builder.button(text=Texts.BTN_TRY_AI, callback_data="act_try_ai")

    settings = get_settings()
    if settings.MINI_APP_URL:
        builder.button(text=Texts.BTN_DASHBOARD, web_app=WebAppInfo(url=settings.MINI_APP_URL))
    else:
        builder.button(text=Texts.BTN_DASHBOARD, callback_data="act_open_dashboard")

    builder.button(text=Texts.BTN_SETTINGS, callback_data="act_open_settings")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


# ── Onboarding Keyboards ────────────────────────────────────────────────────

def onboarding_timezone_keyboard() -> InlineKeyboardMarkup:
    """Popular timezones for CIS & Europe."""
    builder = InlineKeyboardBuilder()
    timezones = [
        ("Калининград (UTC+2)", "Europe/Kaliningrad"),
        ("Москва (UTC+3)", "Europe/Moscow"),
        ("Самара (UTC+4)", "Europe/Samara"),
        ("Екатеринбург (UTC+5)", "Europe/Yekaterinburg"),
        ("Омск (UTC+6)", "Europe/Omsk"),
        ("Красноярск (UTC+7)", "Europe/Krasnoyarsk"),
        ("Иркутск (UTC+8)", "Europe/Irkutsk"),
        ("Владивосток (UTC+10)", "Europe/Vladivostok"),
        ("Ташкент (UTC+5)", "Asia/Tashkent"),
        ("Алматы (UTC+5)", "Asia/Almaty"),
        ("Тбилиси (UTC+4)", "Asia/Tbilisi"),
    ]
    for label, tz in timezones:
        builder.button(text=label, callback_data=OnboardingCallback(action="timezone", value=tz))
    builder.button(text=Texts.ONBOARDING_SKIP, callback_data=OnboardingCallback(action="skip", value=""))
    builder.adjust(2, 2, 2, 2, 2, 1, 1)
    return builder.as_markup()


def onboarding_role_keyboard() -> InlineKeyboardMarkup:
    """User role selector."""
    builder = InlineKeyboardBuilder()
    roles = [
        "Фрилансер",
        "Студент",
        "Предприниматель",
        "Руководитель",
        "Другое",
    ]
    for r in roles:
        builder.button(text=r, callback_data=OnboardingCallback(action="role", value=r))
    builder.button(text=Texts.ONBOARDING_SKIP, callback_data=OnboardingCallback(action="skip", value=""))
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def skip_keyboard(allow_back: bool = False, back_data: str = "step_back") -> InlineKeyboardMarkup:
    """Skip, back (optional), and cancel buttons."""
    builder = InlineKeyboardBuilder()
    builder.button(text=Texts.BTN_SKIP, callback_data="step_skip")
    if allow_back:
        builder.button(text="◀️ Назад", callback_data=back_data)
        builder.button(text=Texts.BTN_CANCEL, callback_data="step_cancel")
        builder.adjust(2, 1)
    else:
        builder.button(text=Texts.BTN_CANCEL, callback_data="step_cancel")
        builder.adjust(1, 1)
    return builder.as_markup()


def confirm_cancel_keyboard(confirm_data: str = "confirm", cancel_data: str = "cancel") -> InlineKeyboardMarkup:
    """Standard confirm/cancel buttons."""
    builder = InlineKeyboardBuilder()
    builder.button(text=Texts.BTN_CONFIRM, callback_data=confirm_data)
    builder.button(text=Texts.BTN_CANCEL, callback_data=cancel_data)
    builder.adjust(2)
    return builder.as_markup()


# ── Task Keyboards ──────────────────────────────────────────────────────────

def task_priority_keyboard() -> InlineKeyboardMarkup:
    """Task priority selector."""
    builder = InlineKeyboardBuilder()
    builder.button(text=Texts.PRIORITY_LOW, callback_data="priority_low")
    builder.button(text=Texts.PRIORITY_MEDIUM, callback_data="priority_medium")
    builder.button(text=Texts.PRIORITY_HIGH, callback_data="priority_high")
    builder.button(text=Texts.PRIORITY_URGENT, callback_data="priority_urgent")
    builder.adjust(2, 2)
    return builder.as_markup()


def task_actions_keyboard(task: Task, filter_type: str = "all", page: int = 1) -> InlineKeyboardMarkup:
    """Action buttons for a single task."""
    builder = InlineKeyboardBuilder()
    if task.status != "completed":
        builder.button(
            text="✅ Выполнить",
            callback_data=TaskCallback(action="complete", task_id=task.id, page=page, filter_type=filter_type),
        )
    star = "⭐ Убрать важное" if task.is_important else "⭐ Пометить важной"
    builder.button(
        text=star,
        callback_data=TaskCallback(action="toggle_imp", task_id=task.id, page=page, filter_type=filter_type),
    )
    builder.button(
        text="🗑 Удалить",
        callback_data=TaskCallback(action="delete", task_id=task.id, page=page, filter_type=filter_type),
    )
    builder.button(
        text="◀️ Назад к списку",
        callback_data=TaskCallback(action="page", task_id=0, page=page, filter_type=filter_type),
    )
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def task_list_keyboard(
    tasks: list[Task],
    page: int,
    total_pages: int,
    filter_type: str = "all",
) -> InlineKeyboardMarkup:
    """Paginated task list with filter and item buttons."""
    builder = InlineKeyboardBuilder()

    # List items
    for t in tasks:
        p_emo = priority_emoji(t.priority)
        s_emo = status_emoji(t.status)
        title = t.title[:25] + ("..." if len(t.title) > 25 else "")
        label = f"{s_emo} {p_emo} {title}"
        builder.button(
            text=label,
            callback_data=TaskCallback(action="view", task_id=t.id, page=page, filter_type=filter_type),
        )

    builder.adjust(1)

    # Pagination controls
    nav_buttons: list[InlineKeyboardButton] = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=TaskCallback(action="page", page=page - 1, filter_type=filter_type).pack(),
            )
        )
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{page}/{max(1, total_pages)}",
            callback_data="noop",
        )
    )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=TaskCallback(action="page", page=page + 1, filter_type=filter_type).pack(),
            )
        )

    builder.row(*nav_buttons)

    # Filter & add task buttons
    builder.row(
        InlineKeyboardButton(
            text="🔍 Фильтры",
            callback_data=TaskCallback(action="filter", filter_type=filter_type).pack(),
        ),
        InlineKeyboardButton(
            text="➕ Добавить",
            callback_data="act_create_task",
        ),
    )

    return builder.as_markup()


def task_filter_keyboard() -> InlineKeyboardMarkup:
    """Filter selection for tasks."""
    builder = InlineKeyboardBuilder()
    filters = [
        ("Все активные", "all"),
        ("📅 На сегодня", "today"),
        ("⚠️ Просроченные", "overdue"),
        ("🗓 На 7 дней", "week"),
        ("🔴 Высокий приоритет", "high"),
        ("✅ Выполненные", "completed"),
    ]
    for label, f_type in filters:
        builder.button(
            text=label,
            callback_data=TaskCallback(action="page", filter_type=f_type, page=1),
        )
    builder.button(text="◀️ Назад", callback_data=TaskCallback(action="page", filter_type="all", page=1))
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


# ── Habit Keyboards ─────────────────────────────────────────────────────────

def habit_frequency_keyboard() -> InlineKeyboardMarkup:
    """Habit frequency selection."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Ежедневно", callback_data="freq_daily")
    builder.button(text="По будням", callback_data="freq_weekdays")
    builder.button(text="Пн, Ср, Пт", callback_data="freq_specific_mwf")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def habit_actions_keyboard(habit: Habit) -> InlineKeyboardMarkup:
    """Actions for a single habit."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Выполнено",
        callback_data=HabitCallback(action="complete", habit_id=habit.id),
    )
    builder.button(
        text="⏭ Пропустить",
        callback_data=HabitCallback(action="skip", habit_id=habit.id),
    )
    pause_text = "▶️ Возобновить" if habit.is_paused else "⏸ Пауза"
    pause_action = "resume" if habit.is_paused else "pause"
    builder.button(
        text=pause_text,
        callback_data=HabitCallback(action=pause_action, habit_id=habit.id),
    )
    builder.button(
        text="🗑 Удалить",
        callback_data=HabitCallback(action="delete", habit_id=habit.id),
    )
    builder.button(text="◀️ Назад", callback_data=HabitCallback(action="back"))
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def habit_list_keyboard(habits: list[Habit]) -> InlineKeyboardMarkup:
    """List of active habits."""
    builder = InlineKeyboardBuilder()
    for h in habits:
        status_mark = "⏸ " if h.is_paused else ""
        streak = f" 🔥{h.current_streak}" if h.current_streak > 0 else ""
        builder.button(
            text=f"{status_mark}🔄 {h.title[:24]}{streak}",
            callback_data=HabitCallback(action="view", habit_id=h.id),
        )
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="➕ Новая привычка", callback_data="act_add_habit"),
        InlineKeyboardButton(text="◀️ В меню", callback_data="act_main_menu"),
    )
    return builder.as_markup()


# ── Focus Session Keyboards ─────────────────────────────────────────────────

def focus_duration_keyboard() -> InlineKeyboardMarkup:
    """Duration selector for Pomodoro / Focus session."""
    builder = InlineKeyboardBuilder()
    durations = [(15, "15 мин"), (25, "25 мин (классика)"), (45, "45 мин (глубокий фокус)"), (60, "60 мин")]
    for mins, label in durations:
        builder.button(text=label, callback_data=FocusCallback(action="start", minutes=mins))
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def focus_end_keyboard(session_id: int, task_id: int = 0) -> InlineKeyboardMarkup:
    """Keyboard sent when focus session timer ends."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=Texts.BTN_FOCUS_DONE,
        callback_data=FocusCallback(action="done", session_id=session_id),
    )
    builder.button(
        text=Texts.BTN_FOCUS_EXTEND,
        callback_data=FocusCallback(action="extend", session_id=session_id, minutes=15),
    )
    if task_id:
        builder.button(
            text=Texts.BTN_FOCUS_COMPLETE_TASK,
            callback_data=FocusCallback(action="complete_task", session_id=session_id, task_id=task_id),
        )
    builder.adjust(2, 1)
    return builder.as_markup()


# ── AI Keyboards ────────────────────────────────────────────────────────────

def ai_mode_keyboard() -> InlineKeyboardMarkup:
    """AI feature modes selector."""
    builder = InlineKeyboardBuilder()
    builder.button(text=Texts.BTN_AI_ANALYZE, callback_data=AICallback(action="mode", mode="analyze"))
    builder.button(text=Texts.BTN_AI_PLAN, callback_data=AICallback(action="mode", mode="plan"))
    builder.button(text=Texts.BTN_AI_DECOMPOSE, callback_data=AICallback(action="mode", mode="decompose"))
    builder.button(text=Texts.BTN_AI_COACH, callback_data=AICallback(action="mode", mode="coach"))
    builder.button(text=Texts.BTN_AI_REVIEW, callback_data=AICallback(action="mode", mode="review"))
    builder.button(text="◀️ В меню", callback_data="act_main_menu")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def ai_parsed_task_keyboard() -> InlineKeyboardMarkup:
    """Confirmation buttons after parsing natural language task."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Создать задачу", callback_data="ai_confirm_task")
    builder.button(text="❌ Отмена", callback_data="ai_cancel_task")
    builder.adjust(2)
    return builder.as_markup()


# ── Settings Keyboards ──────────────────────────────────────────────────────

def settings_keyboard(is_pro: bool = False, morning_enabled: bool = True, evening_enabled: bool = True) -> InlineKeyboardMarkup:
    """Settings options."""
    builder = InlineKeyboardBuilder()
    m_icon = "🔔" if morning_enabled else "🔕"
    e_icon = "🔔" if evening_enabled else "🔕"
    builder.button(text=f"{m_icon} Утренний дайджест", callback_data=SettingsCallback(action="toggle_morning"))
    builder.button(text=f"{e_icon} Вечерний итог", callback_data=SettingsCallback(action="toggle_evening"))
    builder.button(text=Texts.BTN_SETTINGS_TIMEZONE, callback_data=SettingsCallback(action="timezone"))
    builder.button(text=Texts.BTN_SETTINGS_ONBOARDING, callback_data=SettingsCallback(action="reonboard"))

    sub_label = "💎 Подписка: PRO" if is_pro else "📦 Тариф: Free (Перейти на PRO)"
    builder.button(text=sub_label, callback_data=SettingsCallback(action="upgrade_pro"))
    builder.button(text="◀️ В главное меню", callback_data="act_main_menu")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


# ── Admin Keyboard ──────────────────────────────────────────────────────────

def admin_keyboard() -> InlineKeyboardMarkup:
    """Admin control panel buttons."""
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Найти пользователя", callback_data="admin_find_user")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="📊 Полная статистика", callback_data="admin_stats")
    builder.button(text="🔧 Режим обслуживания", callback_data="admin_maintenance")
    builder.adjust(2, 2)
    return builder.as_markup()
