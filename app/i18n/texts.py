"""Internationalization module — all user-facing text lives here."""

from __future__ import annotations


class Texts:
    """Base text collection — Russian (default)."""

    # ---- Onboarding ----
    WELCOME = (
        "👋 <b>Привет! Я Фокус</b> — твой AI-органайзер.\n\n"
        "Я помогу разобрать мысли, задачи и планы, "
        "а затем превращу их в понятную систему действий.\n\n"
        "Давай начнём! 👇"
    )
    ONBOARDING_NAME = "Как мне к тебе обращаться? Напиши своё имя:"
    ONBOARDING_TIMEZONE = (
        "🌍 Выбери свой часовой пояс.\n"
        "Это нужно, чтобы дайджесты и напоминания приходили вовремя."
    )
    ONBOARDING_ROLE = "👤 Чем ты занимаешься? Это поможет мне лучше подстроиться."
    ONBOARDING_GOAL = (
        "🎯 Какая твоя <b>главная цель</b> на ближайшие 30 дней?\n"
        "Напиши одним предложением:"
    )
    ONBOARDING_MORNING_TIME = (
        "🌅 Во сколько присылать <b>утренний дайджест</b>?\n"
        "Напиши время в формате ЧЧ:ММ (например, 08:00):"
    )
    ONBOARDING_EVENING_TIME = (
        "🌙 Во сколько присылать <b>вечерний итог</b>?\n"
        "Напиши время в формате ЧЧ:ММ (например, 21:00):"
    )
    ONBOARDING_DONE = (
        "✅ Отлично, <b>{name}</b>! Всё настроено.\n\n"
        "Теперь я готов помогать тебе быть продуктивнее.\n"
        "Используй меню ниже или просто напиши мне задачу."
    )
    ONBOARDING_SKIP = "⏭ Пропустить настройку"
    ONBOARDING_SKIPPED = (
        "👌 Хорошо, ты можешь настроить всё позже в разделе <b>Настройки</b>.\n"
        "А пока — используй меню ниже!"
    )

    # ---- Main Menu ----
    MENU_TITLE = "📋 <b>Главное меню</b>\n\nВыбери раздел:"
    BTN_TODAY = "📅 Сегодня"
    BTN_TASKS = "📝 Задачи"
    BTN_HABITS = "🔄 Привычки"
    BTN_AI = "🤖 AI-помощник"
    BTN_STATS = "📊 Статистика"
    BTN_SETTINGS = "⚙️ Настройки"
    BTN_CREATE_TASK = "➕ Создать задачу"
    BTN_PLAN_DAY = "📅 Запланировать день"
    BTN_ADD_HABIT = "🔄 Добавить привычку"
    BTN_TRY_AI = "🤖 Попробовать AI-разбор"
    BTN_DASHBOARD = "📱 Открыть дашборд"
    BTN_BACK = "◀️ Назад"
    BTN_CANCEL = "❌ Отмена"
    BTN_CONFIRM = "✅ Подтвердить"
    BTN_SKIP = "⏭ Пропустить"
    BTN_DONE = "✅ Готово"

    # ---- Tasks ----
    TASK_CREATED = "✅ Задача <b>«{title}»</b> создана!"
    TASK_ENTER_TITLE = "📝 Введи <b>название</b> задачи:"
    TASK_ENTER_DESCRIPTION = "📄 Добавь <b>описание</b> (или нажми «Пропустить»):"
    TASK_SELECT_PRIORITY = "🔺 Выбери <b>приоритет</b>:"
    TASK_ENTER_DUE_DATE = "📅 Укажи <b>дату</b> (ДД.ММ.ГГГГ) или нажми «Пропустить»:"
    TASK_ENTER_DUE_TIME = "⏰ Укажи <b>время</b> (ЧЧ:ММ) или нажми «Пропустить»:"
    TASK_ENTER_ESTIMATED = "⏱ Сколько <b>минут</b> займёт? (число или «Пропустить»):"
    TASK_ENTER_CATEGORY = "🏷 Укажи <b>категорию</b> (или «Пропустить»):"
    TASK_CONFIRM = (
        "📋 <b>Подтверди задачу:</b>\n\n"
        "📝 {title}\n"
        "{description}"
        "🔺 Приоритет: {priority}\n"
        "{due_date}"
        "{due_time}"
        "{estimated}"
        "{category}"
    )
    TASK_LIST_EMPTY = "📭 Нет задач в этом разделе."
    TASK_LIST_HEADER = "📝 <b>Задачи{filter_label}:</b>\n"
    TASK_COMPLETED = "✅ Задача <b>«{title}»</b> выполнена! 🎉"
    TASK_DELETED = "🗑 Задача удалена."
    TASK_UPDATED = "✏️ Задача обновлена."
    TASK_NOT_FOUND = "❌ Задача не найдена."
    TASK_OVERDUE_WARNING = "⚠️ У тебя {count} просроченных задач!"
    TASK_DETAIL = (
        "📋 <b>{title}</b>\n\n"
        "{description}"
        "📌 Статус: {status}\n"
        "🔺 Приоритет: {priority}\n"
        "{due_date}"
        "{due_time}"
        "{estimated}"
        "{category}"
        "{tags}"
        "📅 Создана: {created_at}\n"
    )
    PRIORITY_LOW = "🟢 Низкий"
    PRIORITY_MEDIUM = "🟡 Средний"
    PRIORITY_HIGH = "🔴 Высокий"
    PRIORITY_URGENT = "🚨 Срочный"
    STATUS_INBOX = "📥 Входящие"
    STATUS_PLANNED = "📅 Запланировано"
    STATUS_IN_PROGRESS = "🔄 В работе"
    STATUS_COMPLETED = "✅ Выполнено"
    STATUS_CANCELLED = "❌ Отменено"

    # ---- AI Task Parsing ----
    AI_TASK_PARSED = (
        "🤖 <b>Я распознал задачу:</b>\n\n"
        "📝 {title}\n"
        "{due_date}"
        "{due_time}"
        "{priority}"
        "{estimated}"
        "{category}\n"
        "Создать задачу?"
    )
    AI_ANALYZING = "🤔 Анализирую..."
    AI_ERROR = "❌ Произошла ошибка при обработке AI-запроса. Попробуй позже."
    AI_LIMIT_REACHED = (
        "⚠️ Ты использовал все <b>{limit}</b> AI-запросов на этот месяц.\n\n"
        "Перейди на <b>Pro</b>, чтобы получить безлимитный доступ! 💎"
    )
    AI_MODE_SELECT = (
        "🤖 <b>AI-помощник</b>\n\n"
        "Выбери режим или просто напиши мне свою мысль:"
    )
    BTN_AI_ANALYZE = "🔍 Разбор мысли"
    BTN_AI_PLAN = "📅 Планирование дня"
    BTN_AI_DECOMPOSE = "🌳 Декомпозиция задачи"
    BTN_AI_COACH = "💡 Коучинг"
    BTN_AI_REVIEW = "📊 Обзор недели"
    AI_CREATE_ALL = "✅ Создать все задачи"
    AI_EDIT_RESULT = "✏️ Изменить"
    AI_SAVE_NOTE = "📝 Сохранить как заметку"

    # ---- Focus Session ----
    FOCUS_SELECT_DURATION = "⏱ Выбери продолжительность фокус-сессии:"
    FOCUS_STARTED = (
        "🎯 <b>Фокус-сессия началась!</b>\n\n"
        "⏱ Продолжительность: {duration} мин\n"
        "{task}"
        "\nНе отвлекайся — я напомню, когда время закончится. 💪"
    )
    FOCUS_ENDED = (
        "🔔 <b>Время вышло!</b>\n\n"
        "⏱ Сессия: {duration} мин\n"
        "{task}\n"
        "Что дальше?"
    )
    BTN_FOCUS_DONE = "✅ Завершил"
    BTN_FOCUS_EXTEND = "➕ Ещё 15 мин"
    BTN_FOCUS_POSTPONE = "⏸ Отложить"
    BTN_FOCUS_COMPLETE_TASK = "☑️ Задача выполнена"

    # ---- Habits ----
    HABIT_ENTER_TITLE = "🔄 Введи <b>название</b> привычки:"
    HABIT_SELECT_FREQUENCY = "📅 Выбери <b>частоту</b>:"
    HABIT_ENTER_REMINDER_TIME = "⏰ Во сколько напоминать? (ЧЧ:ММ или «Пропустить»):"
    HABIT_CREATED = "✅ Привычка <b>«{title}»</b> добавлена!"
    HABIT_COMPLETED = "✅ Привычка <b>«{title}»</b> отмечена! {streak_msg}"
    HABIT_SKIPPED = "⏭ Привычка <b>«{title}»</b> пропущена на сегодня."
    HABIT_LIST_EMPTY = "📭 У тебя пока нет привычек."
    HABIT_LIST_HEADER = "🔄 <b>Твои привычки:</b>\n"
    HABIT_STREAK_MSG = "\n🔥 Серия: {current} дн. (лучшая: {best})"
    HABIT_STREAK_NEW_BEST = "\n🏆 Новый рекорд! {best} дн. подряд!"
    HABIT_DELETED = "🗑 Привычка удалена."
    HABIT_PAUSED = "⏸ Привычка приостановлена."
    HABIT_RESUMED = "▶️ Привычка возобновлена."
    FREQ_DAILY = "Ежедневно"
    FREQ_WEEKDAYS = "По будням"
    FREQ_SPECIFIC = "Определённые дни"
    FREQ_TIMES_WEEK = "N раз в неделю"

    # ---- Daily Plan ----
    TODAY_HEADER = "📅 <b>План на {date}</b>\n"
    TODAY_MAIN_FOCUS = "\n🎯 <b>Главный фокус:</b>\n{focus}\n"
    TODAY_TASKS = "\n📝 <b>Задачи:</b>\n"
    TODAY_HABITS = "\n🔄 <b>Привычки:</b>\n"
    TODAY_SUMMARY = (
        "\n📊 <b>Сводка:</b>\n"
        "• Запланировано: {planned_time}\n"
        "• Выполнено: {completed}/{total}\n"
        "• Просроченных: {overdue}\n"
    )
    BTN_REBUILD_PLAN = "🔄 Перестроить план"
    BTN_ADD_TASK_TODAY = "➕ Добавить задачу"
    BTN_START_FOCUS = "🎯 Фокус-сессия"
    BTN_SHOW_OVERDUE = "⚠️ Просроченные"
    BTN_EVENING_SUMMARY = "🌙 Вечерний итог"

    # ---- Digests ----
    MORNING_DIGEST = (
        "☀️ <b>Доброе утро, {name}!</b>\n\n"
        "📅 {date}\n"
        "{main_goal}"
        "\n📝 <b>Важные задачи:</b>\n{tasks}\n"
        "{habits}"
        "\n💪 {motivation}"
    )
    EVENING_DIGEST = (
        "🌙 <b>Вечерний итог</b>\n\n"
        "✅ Выполнено задач: {completed}\n"
        "📝 Осталось: {remaining}\n"
        "⏱ Время в фокусе: {focus_time}\n"
        "{habits}\n"
        "💭 Что сегодня получилось лучше всего?"
    )

    # ---- Stats ----
    STATS_HEADER = "📊 <b>Статистика</b>\n"
    STATS_TASKS = (
        "\n📝 <b>Задачи:</b>\n"
        "• Всего: {total}\n"
        "• Выполнено: {completed}\n"
        "• В работе: {in_progress}\n"
        "• Просрочено: {overdue}\n"
    )
    STATS_HABITS = (
        "\n🔄 <b>Привычки:</b>\n"
        "• Активных: {active}\n"
        "• Лучшая серия: {best_streak} дн.\n"
        "• Выполнений на этой неделе: {week_completions}\n"
    )
    STATS_FOCUS = (
        "\n🎯 <b>Фокус:</b>\n"
        "• Сессий на этой неделе: {sessions}\n"
        "• Общее время: {total_time}\n"
    )

    # ---- Settings ----
    SETTINGS_TITLE = "⚙️ <b>Настройки</b>"
    BTN_SETTINGS_PROFILE = "👤 Профиль"
    BTN_SETTINGS_NOTIFICATIONS = "🔔 Уведомления"
    BTN_SETTINGS_TIMEZONE = "🌍 Часовой пояс"
    BTN_SETTINGS_LANGUAGE = "🌐 Язык"
    BTN_SETTINGS_SUBSCRIPTION = "💎 Подписка"
    BTN_SETTINGS_ONBOARDING = "🔄 Пройти onboarding"

    # ---- Subscription ----
    SUB_FREE_TITLE = "📦 <b>Тариф: Free</b>\n"
    SUB_FREE_DETAILS = (
        "• До {max_tasks} активных задач\n"
        "• До {max_habits} привычек\n"
        "• {ai_limit} AI-запросов в месяц\n"
        "• Базовая статистика\n"
    )
    SUB_PRO_TITLE = "💎 <b>Тариф: Pro</b>\n"
    SUB_PRO_DETAILS = (
        "• Безлимитные задачи\n"
        "• Безлимитные привычки\n"
        "• Безлимитные AI-запросы\n"
        "• Расширенная статистика\n"
        "• Еженедельные AI-обзоры\n"
        "• Голосовые сообщения\n"
        "• Расширенное планирование\n"
    )
    BTN_UPGRADE_PRO = "💎 Перейти на Pro"
    LIMIT_TASKS_REACHED = (
        "⚠️ Ты достиг лимита — <b>{max_tasks}</b> активных задач.\n"
        "Заверши или удали задачи, или перейди на <b>Pro</b>."
    )
    LIMIT_HABITS_REACHED = (
        "⚠️ Ты достиг лимита — <b>{max_habits}</b> привычек.\n"
        "Удали привычку или перейди на <b>Pro</b>."
    )

    # ---- General ----
    CANCELLED = "❌ Действие отменено."
    ERROR_GENERIC = "😔 Произошла ошибка. Попробуй ещё раз позже."
    ERROR_INVALID_INPUT = "⚠️ Некорректный ввод. Попробуй ещё раз."
    ERROR_ACCESS_DENIED = "🚫 У тебя нет доступа к этому ресурсу."
    HELP_TEXT = (
        "📖 <b>Справка — Фокус</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — Запуск и настройка\n"
        "/menu — Главное меню\n"
        "/today — План на сегодня\n"
        "/tasks — Список задач\n"
        "/add_task — Добавить задачу\n"
        "/habits — Привычки\n"
        "/add_habit — Добавить привычку\n"
        "/ai — AI-помощник\n"
        "/stats — Статистика\n"
        "/settings — Настройки\n"
        "/help — Эта справка\n"
        "/cancel — Отменить текущее действие\n\n"
        "Или просто <b>отправь текст</b> — я разберу его как задачу!"
    )
    MAINTENANCE_MODE = "🔧 Бот на обслуживании. Пожалуйста, попробуй позже."

    # ---- Voice ----
    VOICE_PROCESSING = "🎤 Обрабатываю голосовое сообщение..."
    VOICE_RESULT = "🎤 <b>Распознано:</b>\n\n<i>{text}</i>\n\nОбработать как задачу?"
    VOICE_ERROR = "😔 Не удалось распознать голосовое сообщение. Попробуй отправить текстом."
    VOICE_PRO_ONLY = "🎤 Голосовые сообщения доступны в тарифе <b>Pro</b>."

    # ---- Admin ----
    ADMIN_PANEL = "🔐 <b>Админ-панель</b>\n"
    ADMIN_STATS = (
        "👥 Всего пользователей: {total_users}\n"
        "📱 Активных сегодня: {active_today}\n"
        "📊 Активных за неделю: {active_week}\n"
        "📝 Задач создано: {total_tasks}\n"
        "✅ Задач выполнено: {completed_tasks}\n"
        "🤖 AI-запросов: {ai_requests}\n"
    )


class TextsEn(Texts):
    """English text overrides (stub for future localization)."""
    WELCOME = (
        "👋 <b>Hi! I'm Focus</b> — your AI organizer.\n\n"
        "I'll help you sort out thoughts, tasks and plans, "
        "and turn them into a clear action system.\n\n"
        "Let's get started! 👇"
    )


# Registry for language lookup
_LANGS: dict[str, type[Texts]] = {
    "ru": Texts,
    "en": TextsEn,
}


def get_texts(lang: str = "ru") -> Texts:
    """Get text collection for the given language."""
    cls = _LANGS.get(lang, Texts)
    return cls()
