"""Focus session (Pomodoro) handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import FocusCallback, focus_duration_keyboard, focus_end_keyboard
from app.db.repositories.focus_repo import FocusSessionRepository
from app.db.repositories.task_repo import TaskRepository
from app.i18n.texts import Texts

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

router = Router(name="focus")


@router.message(Command("focus"))
@router.callback_query(F.data == "act_start_focus")
async def cmd_focus(event: Message | CallbackQuery) -> None:
    """Prompt user to choose focus duration."""
    text = f"🎯 <b>Режим фокуса (Pomodoro):</b>\n\n{Texts.FOCUS_SELECT_DURATION}"
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=focus_duration_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=focus_duration_keyboard())


@router.callback_query(FocusCallback.filter(F.action == "start"))
async def cb_start_focus_session(
    callback: CallbackQuery,
    callback_data: FocusCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Start focus session record and confirm."""
    repo = FocusSessionRepository(session)
    duration = callback_data.minutes

    fs = await repo.create(
        user_id=user.id,
        duration_minutes=duration,
    )

    msg = Texts.FOCUS_STARTED.format(
        duration=duration,
        task="",
    )
    await callback.message.edit_text(msg)
    await callback.answer(f"🎯 Фокус на {duration} мин начался!")

    # In a real environment with background scheduler or polling,
    # APScheduler triggers notification. For immediate UX and testing,
    # show finish controls:
    finish_prompt = f"⏱ Сессия #{fs.id} активна. Когда завершишь — нажми кнопку ниже:"
    await callback.message.answer(finish_prompt, reply_markup=focus_end_keyboard(session_id=fs.id))


@router.callback_query(FocusCallback.filter(F.action == "done"))
async def cb_focus_done(
    callback: CallbackQuery,
    callback_data: FocusCallback,
    session: AsyncSession,
) -> None:
    """Complete focus session."""
    repo = FocusSessionRepository(session)
    active = await repo.get_active_session(callback.from_user.id)
    if active:
        await repo.complete_session(active)
    await callback.message.edit_text("🎉 <b>Отличная работа!</b> Фокус-сессия успешно завершена и записана в статистику.")
    await callback.answer()


@router.callback_query(FocusCallback.filter(F.action == "extend"))
async def cb_focus_extend(
    callback: CallbackQuery,
    callback_data: FocusCallback,
    session: AsyncSession,
) -> None:
    """Extend focus session by 15 minutes."""
    repo = FocusSessionRepository(session)
    active = await repo.get_active_session(callback.from_user.id)
    if active:
        await repo.extend_session(active, extra_minutes=15)
        await callback.answer("➕ Продлено на 15 минут!")
        await callback.message.edit_text(
            f"⏱ Фокус-сессия продлена на 15 мин (всего {active.duration_minutes} мин). Продолжай работу!",
            reply_markup=focus_end_keyboard(session_id=active.id),
        )
    else:
        await callback.answer("Активная сессия не найдена.")


@router.callback_query(FocusCallback.filter(F.action == "complete_task"))
async def cb_focus_complete_task(
    callback: CallbackQuery,
    callback_data: FocusCallback,
    session: AsyncSession,
) -> None:
    """Complete associated task."""
    task_repo = TaskRepository(session)
    if callback_data.task_id:
        task = await task_repo.get_by_id(callback_data.task_id)
        if task:
            await task_repo.complete_task(task)
            await callback.answer("✅ Задача отмечена как выполненная!")
    await cb_focus_done(callback, callback_data, session)
