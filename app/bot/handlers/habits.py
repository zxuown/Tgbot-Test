"""Habits handlers: listing, creation FSM, completion, streaks, pause and delete."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    HabitCallback,
    habit_actions_keyboard,
    habit_frequency_keyboard,
    habit_list_keyboard,
    skip_keyboard,
)
from app.bot.states import HabitCreationStates
from app.core.security import escape_html
from app.db.models.habit import HabitFrequency
from app.i18n.texts import Texts
from app.services.habit_service import HabitService
from app.utils.helpers import validate_time_input

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

router = Router(name="habits")


@router.message(Command("habits"))
@router.message(F.text == Texts.BTN_HABITS)
async def cmd_habits(message: Message, user: User, session: AsyncSession) -> None:
    """Show user's habits list."""
    service = HabitService(session)
    habits = await service.get_habits(user.id, active_only=False)

    if not habits:
        await message.answer(
            Texts.HABIT_LIST_EMPTY,
            reply_markup=habit_list_keyboard([]),
        )
        return

    text = Texts.HABIT_LIST_HEADER
    for h in habits:
        status_icon = "⏸ " if h.is_paused else "• "
        streak_str = f" (🔥 {h.current_streak} дн.)" if h.current_streak > 0 else ""
        text += f"{status_icon}<b>{escape_html(h.title)}</b>{streak_str}\n"

    await message.answer(text, reply_markup=habit_list_keyboard(habits))


@router.callback_query(HabitCallback.filter(F.action == "back"))
async def cb_habits_back(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """Return to habits list."""
    service = HabitService(session)
    habits = await service.get_habits(user.id, active_only=False)
    text = Texts.HABIT_LIST_HEADER if habits else Texts.HABIT_LIST_EMPTY
    await callback.message.edit_text(text, reply_markup=habit_list_keyboard(habits))
    await callback.answer()


@router.callback_query(HabitCallback.filter(F.action == "view"))
async def cb_habit_view(
    callback: CallbackQuery,
    callback_data: HabitCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Show single habit details and actions."""
    service = HabitService(session)
    habit = await service.get_habit(callback_data.habit_id, user.id)
    if not habit:
        await callback.answer("Привычка не найдена", show_alert=True)
        return

    desc = f"📄 <i>{escape_html(habit.description)}</i>\n\n" if habit.description else ""
    freq = f"📅 Частота: {habit.frequency}\n"
    rem = f"⏰ Напоминание: {habit.reminder_time}\n" if habit.reminder_time else ""
    streak = f"🔥 Текущая серия: <b>{habit.current_streak}</b> дн.\n"
    best = f"🏆 Лучшая серия: <b>{habit.best_streak}</b> дн.\n"
    total = f"✅ Всего выполнений: {habit.total_completions}\n"
    paused = "⏸ <b>Привычка на паузе</b>\n" if habit.is_paused else ""

    text = (
        f"🔄 <b>{escape_html(habit.title)}</b>\n\n"
        f"{desc}{freq}{rem}{streak}{best}{total}{paused}"
    )
    await callback.message.edit_text(text, reply_markup=habit_actions_keyboard(habit))
    await callback.answer()


@router.callback_query(HabitCallback.filter(F.action == "complete"))
async def cb_habit_complete(
    callback: CallbackQuery,
    callback_data: HabitCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Mark habit as completed today."""
    service = HabitService(session)
    completion, err = await service.complete_habit(callback_data.habit_id, user.id)

    if err:
        await callback.answer(f"⚠️ {err}", show_alert=True)
        return

    habit = await service.get_habit(callback_data.habit_id, user.id)
    await callback.answer(f"✅ Отмечено! Серия: {habit.current_streak} дн.", show_alert=False)
    # Refresh view
    await cb_habit_view(callback, callback_data, user, session)


@router.callback_query(HabitCallback.filter(F.action == "skip"))
async def cb_habit_skip(
    callback: CallbackQuery,
    callback_data: HabitCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Skip habit today."""
    service = HabitService(session)
    completion, err = await service.complete_habit(callback_data.habit_id, user.id, skipped=True)
    if err:
        await callback.answer(f"⚠️ {err}", show_alert=True)
    else:
        await callback.answer("Привычка пропущена на сегодня.")
        await cb_habit_view(callback, callback_data, user, session)


@router.callback_query(HabitCallback.filter(F.action == "pause"))
async def cb_habit_pause(
    callback: CallbackQuery,
    callback_data: HabitCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Pause habit."""
    service = HabitService(session)
    await service.pause_habit(callback_data.habit_id, user.id)
    await callback.answer(Texts.HABIT_PAUSED)
    await cb_habit_view(callback, callback_data, user, session)


@router.callback_query(HabitCallback.filter(F.action == "resume"))
async def cb_habit_resume(
    callback: CallbackQuery,
    callback_data: HabitCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Resume habit."""
    service = HabitService(session)
    await service.resume_habit(callback_data.habit_id, user.id)
    await callback.answer(Texts.HABIT_RESUMED)
    await cb_habit_view(callback, callback_data, user, session)


@router.callback_query(HabitCallback.filter(F.action == "delete"))
async def cb_habit_delete(
    callback: CallbackQuery,
    callback_data: HabitCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Delete habit."""
    service = HabitService(session)
    await service.delete_habit(callback_data.habit_id, user.id)
    await callback.answer(Texts.HABIT_DELETED)
    await cb_habits_back(callback, user, session)


# ── Step-by-Step Creation ──────────────────────────────────────────────────

@router.message(Command("add_habit"))
@router.callback_query(F.data == "act_add_habit")
async def cmd_add_habit(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Start habit creation."""
    await state.clear()
    await state.set_state(HabitCreationStates.title)
    text = f"🔄 <b>Добавление новой привычки:</b>\n\n{Texts.HABIT_ENTER_TITLE}"
    if isinstance(event, CallbackQuery):
        await event.message.answer(text)
        await event.answer()
    else:
        await event.answer(text)


@router.message(HabitCreationStates.title)
async def process_habit_title(message: Message, state: FSMContext) -> None:
    """Step 1: Habit title."""
    title = message.text.strip() if message.text else ""
    if not title:
        await message.answer(Texts.ERROR_INVALID_INPUT)
        return

    await state.update_data(title=title)
    await state.set_state(HabitCreationStates.frequency)
    await message.answer(Texts.HABIT_SELECT_FREQUENCY, reply_markup=habit_frequency_keyboard())


@router.callback_query(F.data.startswith("freq_"))
async def process_habit_frequency(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: Habit frequency."""
    freq_key = callback.data.replace("freq_", "")
    freq = HabitFrequency.DAILY.value
    days = None

    if freq_key == "weekdays":
        freq = HabitFrequency.WEEKDAYS.value
        days = "1,2,3,4,5"
    elif freq_key == "specific_mwf":
        freq = HabitFrequency.SPECIFIC_DAYS.value
        days = "1,3,5"

    await state.update_data(frequency=freq, days_of_week=days)
    await state.set_state(HabitCreationStates.reminder_time)
    await callback.message.edit_text(Texts.HABIT_ENTER_REMINDER_TIME, reply_markup=skip_keyboard())
    await callback.answer()


@router.message(HabitCreationStates.reminder_time)
async def process_habit_reminder(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Step 3: Reminder time & finish creation."""
    parsed, err_code, err_msg = validate_time_input(message.text or "")
    if not parsed:
        prompt = err_msg or "Не удалось распознать время. Напиши, например, «09:00» или «20:00» (или нажми «Пропустить»):"
        await message.answer(prompt, reply_markup=skip_keyboard())
        return

    rem = parsed.strftime("%H:%M")
    data = await state.get_data()

    try:
        service = HabitService(session)
        habit, err = await service.create_habit(
            user_id=user.id,
            title=data.get("title", "Привычка"),
            frequency=data.get("frequency", HabitFrequency.DAILY.value),
            days_of_week=data.get("days_of_week"),
            reminder_time=rem,
        )

        if err:
            await message.answer(f"⚠️ {err}")
        else:
            await message.answer(
                Texts.HABIT_CREATED.format(title=escape_html(habit.title)),
                reply_markup=habit_actions_keyboard(habit),
            )
    finally:
        await state.clear()


@router.callback_query(F.data == "step_skip", HabitCreationStates.reminder_time)
async def cb_habit_skip_reminder(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Skip reminder time and finish habit creation."""
    data = await state.get_data()

    try:
        service = HabitService(session)
        habit, err = await service.create_habit(
            user_id=user.id,
            title=data.get("title", "Привычка"),
            frequency=data.get("frequency", HabitFrequency.DAILY.value),
            days_of_week=data.get("days_of_week"),
            reminder_time=None,
        )

        if err:
            await callback.message.edit_text(f"⚠️ {err}")
        else:
            await callback.message.edit_text(
                Texts.HABIT_CREATED.format(title=escape_html(habit.title)),
                reply_markup=habit_actions_keyboard(habit),
            )
    finally:
        await state.clear()
        await callback.answer()
