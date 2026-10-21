"""AI Assistant handlers: thoughts analysis, decomposition, coaching, review, plan."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.keyboards import AICallback, ai_mode_keyboard
from app.bot.states import AIStates
from app.i18n.texts import Texts
from app.services.ai_service import AIService
from app.services.analytics_service import AnalyticsService
from app.services.subscription_service import SubscriptionService
from app.services.task_service import TaskService
from app.utils.helpers import clean_telegram_html

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

router = Router(name="ai")


@router.message(Command("ai"))
@router.message(F.text == Texts.BTN_AI)
@router.callback_query(F.data == "act_try_ai")
async def cmd_ai(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Show AI Assistant main hub and modes."""
    await state.clear()
    text = Texts.AI_MODE_SELECT
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=ai_mode_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=ai_mode_keyboard())


@router.callback_query(AICallback.filter(F.action == "mode"))
async def cb_select_ai_mode(
    callback: CallbackQuery,
    callback_data: AICallback,
    state: FSMContext,
) -> None:
    """Handle mode selection."""
    mode = callback_data.mode
    await state.update_data(ai_mode=mode)
    await state.set_state(AIStates.waiting_input)

    prompts = {
        "analyze": "🔍 <b>Разбор хаотичной мысли:</b>\n\nНапиши всё, что крутится в голове (мысли, задачи, звонки). Я разложу это по полочкам:",
        "plan": "📅 <b>Планирование дня:</b>\n\nНапиши свои вводные на сегодня (сколько есть времени, главная цель, встречи):",
        "decompose": "🌳 <b>Декомпозиция задачи:</b>\n\nНапиши сложную задачу, которую не знаешь как начать, и я разобью её на понятные шаги:",
        "coach": "💡 <b>Коучинг продуктивности:</b>\n\nЗадай любой вопрос (например: «Почему я прокрастинирую?», «Как спланировать неделю?»):",
        "review": "📊 <b>Обзор недели:</b>\n\nНажми кнопку ниже или отправь свои заметки о прошедшей неделе:",
    }

    builder = InlineKeyboardBuilder()
    if mode == "review":
        builder.button(text="🚀 Запустить анализ недели", callback_data="run_weekly_review")
    builder.button(text="◀️ Назад", callback_data="act_try_ai")
    builder.adjust(1)

    prompt_text = prompts.get(mode, "Напиши свой запрос для AI:")
    await callback.message.edit_text(prompt_text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "run_weekly_review")
async def cb_run_weekly_review(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Generate weekly review from real stats."""
    sub_service = SubscriptionService(session)
    can_ai = await sub_service.can_use_ai(user.id)
    if not can_ai:
        settings = sub_service.settings
        await callback.message.edit_text(
            Texts.AI_LIMIT_REACHED.format(limit=settings.FREE_MONTHLY_AI_LIMIT),
            reply_markup=ai_mode_keyboard(),
        )
        await callback.answer()
        return

    await sub_service.record_ai_usage(user.id)

    analytics = AnalyticsService(session)
    stats = await analytics.get_user_stats(user.id)
    summary_text = (
        f"Выполнено задач: {stats['tasks_completed']}, "
        f"активно: {stats['tasks_active']}, "
        f"сессий фокуса: {stats['focus_week'].get('sessions_count', 0)}, "
        f"время фокуса: {stats['focus_week'].get('total_minutes', 0)} мин, "
        f"привычек выполнено на неделе: {stats['habits_week_completions']}."
    )

    ai = AIService()
    review = await ai.weekly_review(summary_text)

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В меню AI", callback_data="act_try_ai")
    cleaned_review = clean_telegram_html(review)
    try:
        await callback.message.edit_text(cleaned_review, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as exc:
        logger.warning("Failed to send formatted weekly review (%s). Sending plain text.", exc)
        plain = re.sub(r"<[^>]+>", "", cleaned_review)
        await callback.message.edit_text(plain, reply_markup=builder.as_markup(), parse_mode=None)
    await callback.answer()


@router.message(AIStates.waiting_input)
async def process_ai_input(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Process user message in selected AI mode."""
    data = await state.get_data()
    mode = data.get("ai_mode", "analyze")

    # Check quota
    sub_service = SubscriptionService(session)
    can_ai = await sub_service.can_use_ai(user.id)
    if not can_ai:
        settings = sub_service.settings
        await message.answer(
            Texts.AI_LIMIT_REACHED.format(limit=settings.FREE_MONTHLY_AI_LIMIT),
            reply_markup=ai_mode_keyboard(),
        )
        await state.clear()
        return

    await sub_service.record_ai_usage(user.id)
    await message.answer(Texts.AI_ANALYZING)

    ai = AIService()
    user_text = message.text.strip() if message.text else ""

    if mode == "plan":
        result = await ai.plan_day(user_text)
    elif mode == "decompose":
        result = await ai.decompose_task(user_text)
    elif mode == "coach":
        result = await ai.coaching(user_text)
    elif mode == "review":
        result = await ai.weekly_review(user_text)
    else:  # analyze
        result = await ai.analyze_thought(user_text)

    await state.set_state(AIStates.confirm_result)
    await state.update_data(last_ai_result=result, last_user_text=user_text)

    builder = InlineKeyboardBuilder()
    if mode in ("analyze", "decompose"):
        builder.button(text=Texts.AI_CREATE_ALL, callback_data="ai_create_tasks_from_result")
    builder.button(text=Texts.AI_SAVE_NOTE, callback_data="ai_save_as_note")
    builder.button(text="◀️ В меню AI", callback_data="act_try_ai")
    builder.adjust(1)

    cleaned_result = clean_telegram_html(result)
    try:
        await message.answer(cleaned_result, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as exc:
        logger.warning("Failed to send formatted AI response (%s). Sending plain text.", exc)
        plain = re.sub(r"<[^>]+>", "", cleaned_result)
        await message.answer(plain, reply_markup=builder.as_markup(), parse_mode=None)


@router.callback_query(F.data == "ai_create_tasks_from_result")
async def cb_create_tasks_from_ai(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Create tasks extracted from thought analysis."""
    data = await state.get_data()
    user_text = data.get("last_user_text", "")
    await state.clear()

    ai = AIService()
    parsed = await ai.parse_task_from_text(user_text)

    task_service = TaskService(session)
    created_count = 0

    # Create main task
    t, _ = await task_service.create_task(
        user_id=user.id,
        title=parsed.get("title", user_text[:60]),
        priority=parsed.get("priority", "medium"),
        estimated_minutes=parsed.get("estimated_minutes", 30),
        category=parsed.get("category", "AI-разбор"),
        source="ai",
    )
    if t:
        created_count += 1
        # Create subtasks if present
        for sub_title in parsed.get("subtasks", [])[:3]:
            sub_t, _ = await task_service.create_task(
                user_id=user.id,
                title=sub_title,
                parent_task_id=t.id,
                priority="medium",
                source="ai",
            )
            if sub_t:
                created_count += 1

    await callback.message.answer(
        f"✅ Успешно создано задач: <b>{created_count}</b>. Они доступны в разделе «Задачи»!",
        reply_markup=ai_mode_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "ai_save_as_note")
async def cb_save_as_note(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext) -> None:
    """Save AI analysis as inbox task note."""
    data = await state.get_data()
    res = data.get("last_ai_result", "Заметка")
    await state.clear()

    task_service = TaskService(session)
    await task_service.create_task(
        user_id=user.id,
        title="Заметка AI-анализа",
        description=res[:1000],
        category="Заметки",
        source="ai",
    )
    await callback.answer("✅ Сохранено как заметка в Входящие!")
