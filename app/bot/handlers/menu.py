"""Main menu navigation, cancel, and help command handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_menu_keyboard
from app.i18n.texts import Texts

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

router = Router(name="menu")


@router.message(Command("cancel"))
@router.message(F.text.lower().in_(["/cancel", "отмена", "❌ отмена", "cancel"]))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Universal cancel command that aborts any active FSM state."""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer(Texts.CANCELLED, reply_markup=main_menu_keyboard())
    else:
        await message.answer("Нет активного действия для отмены.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "step_cancel")
async def cb_step_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel button callback."""
    await state.clear()
    await callback.message.edit_text(Texts.CANCELLED, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    """Show main interactive menu."""
    await state.clear()
    await message.answer(Texts.MENU_TITLE, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "act_main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to main menu via inline button."""
    await state.clear()
    await callback.message.edit_text(Texts.MENU_TITLE, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show help and available commands."""
    await message.answer(Texts.HELP_TEXT, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    """Acknowledge no-op pagination counter buttons."""
    await callback.answer()


# ── Global Reply Menu Interceptors (Prevents FSM Freezing) ────────────────

@router.message(F.text == Texts.BTN_TODAY)
async def menu_nav_today(message: Message, user: User, session: AsyncSession, state: FSMContext) -> None:
    """Navigate to Today view from any state."""
    await state.clear()
    from app.bot.handlers.today import cmd_today
    await cmd_today(message, user, session)


@router.message(F.text == Texts.BTN_TASKS)
async def menu_nav_tasks(message: Message, user: User, session: AsyncSession, state: FSMContext) -> None:
    """Navigate to Tasks list from any state."""
    await state.clear()
    from app.bot.handlers.tasks import cmd_tasks
    await cmd_tasks(message, user, session)


@router.message(F.text == Texts.BTN_HABITS)
async def menu_nav_habits(message: Message, user: User, session: AsyncSession, state: FSMContext) -> None:
    """Navigate to Habits from any state."""
    await state.clear()
    from app.bot.handlers.habits import cmd_habits
    await cmd_habits(message, user, session)


@router.message(F.text == Texts.BTN_AI)
async def menu_nav_ai(message: Message, state: FSMContext) -> None:
    """Navigate to AI Assistant from any state."""
    await state.clear()
    from app.bot.handlers.ai import cmd_ai
    await cmd_ai(message, state)


@router.message(F.text == Texts.BTN_STATS)
async def menu_nav_stats(message: Message, user: User, session: AsyncSession, state: FSMContext) -> None:
    """Navigate to Stats from any state."""
    await state.clear()
    from app.bot.handlers.stats import cmd_stats
    await cmd_stats(message, user, session)


@router.message(F.text == Texts.BTN_SETTINGS)
async def menu_nav_settings(message: Message, user: User, session: AsyncSession, state: FSMContext) -> None:
    """Navigate to Settings from any state."""
    await state.clear()
    from app.bot.handlers.settings import cmd_settings
    await cmd_settings(message, user, session)
