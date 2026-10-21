"""Handler for /start command and Onboarding FSM scenario."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    OnboardingCallback,
    main_menu_keyboard,
    onboarding_role_keyboard,
    onboarding_timezone_keyboard,
    reply_menu_keyboard,
    skip_keyboard,
)
from app.bot.states import OnboardingStates
from app.core.security import escape_html
from app.db.repositories.user_repo import UserRepository
from app.i18n.texts import Texts

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, state: FSMContext) -> None:
    """Handle /start command. Show welcome message and trigger onboarding if not completed."""
    await state.clear()

    # Always show reply keyboard
    await message.answer(
        Texts.WELCOME,
        reply_markup=reply_menu_keyboard(),
    )

    # Show inline action buttons
    await message.answer(
        "Выбери действие или начни настройку профиля:",
        reply_markup=main_menu_keyboard(),
    )

    # Trigger onboarding if user is new
    if not user.onboarding_completed:
        await state.set_state(OnboardingStates.name)
        await message.answer(
            Texts.ONBOARDING_NAME,
            reply_markup=skip_keyboard(),
        )


@router.callback_query(OnboardingCallback.filter(F.action == "skip"))
async def cb_skip_onboarding(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext) -> None:
    """Allow user to skip onboarding."""
    await state.clear()
    repo = UserRepository(session)
    await repo.update_user(user, onboarding_completed=True)
    await callback.message.edit_text(Texts.ONBOARDING_SKIPPED)
    await callback.answer()


@router.callback_query(F.data == "step_skip", StateFilter(OnboardingStates))
async def cb_step_skip(callback: CallbackQuery, user: User, state: FSMContext) -> None:
    """Skip a single step during onboarding."""
    current_state = await state.get_state()
    if current_state == OnboardingStates.name.state:
        await state.set_state(OnboardingStates.timezone)
        await callback.message.edit_text(Texts.ONBOARDING_TIMEZONE, reply_markup=onboarding_timezone_keyboard())
    elif current_state == OnboardingStates.goal_30_days.state:
        await state.set_state(OnboardingStates.morning_time)
        await callback.message.edit_text(Texts.ONBOARDING_MORNING_TIME, reply_markup=skip_keyboard())
    elif current_state in (OnboardingStates.morning_time.state, OnboardingStates.evening_time.state):
        await state.clear()
        await callback.message.edit_text(Texts.ONBOARDING_SKIPPED)
    await callback.answer()


@router.message(OnboardingStates.name)
async def process_onboarding_name(message: Message, user: User, session: AsyncSession, state: FSMContext) -> None:
    """Step 1: Save display name."""
    name = message.text.strip() if message.text else ""
    if not name or len(name) > 100:
        await message.answer(Texts.ERROR_INVALID_INPUT)
        return

    repo = UserRepository(session)
    await repo.update_user(user, display_name=name)

    await state.set_state(OnboardingStates.timezone)
    await message.answer(
        Texts.ONBOARDING_TIMEZONE,
        reply_markup=onboarding_timezone_keyboard(),
    )


@router.callback_query(OnboardingCallback.filter(F.action == "timezone"))
async def process_onboarding_timezone(
    callback: CallbackQuery,
    callback_data: OnboardingCallback,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Step 2: Save timezone."""
    tz = callback_data.value
    repo = UserRepository(session)
    await repo.update_user(user, timezone=tz)

    await state.set_state(OnboardingStates.role)
    await callback.message.edit_text(
        Texts.ONBOARDING_ROLE,
        reply_markup=onboarding_role_keyboard(),
    )
    await callback.answer()


@router.callback_query(OnboardingCallback.filter(F.action == "role"))
async def process_onboarding_role(
    callback: CallbackQuery,
    callback_data: OnboardingCallback,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Step 3: Save user role."""
    role = callback_data.value
    repo = UserRepository(session)
    await repo.update_user(user, role=role)

    await state.set_state(OnboardingStates.goal_30_days)
    await callback.message.edit_text(
        Texts.ONBOARDING_GOAL,
        reply_markup=skip_keyboard(),
    )
    await callback.answer()


@router.message(OnboardingStates.goal_30_days)
async def process_onboarding_goal(message: Message, user: User, session: AsyncSession, state: FSMContext) -> None:
    """Step 4: Save 30-day goal."""
    goal = message.text.strip() if message.text else ""
    repo = UserRepository(session)
    await repo.update_user(user, goal_30_days=goal)

    await state.set_state(OnboardingStates.morning_time)
    await message.answer(
        Texts.ONBOARDING_MORNING_TIME,
        reply_markup=skip_keyboard(),
    )


@router.message(OnboardingStates.morning_time)
async def process_onboarding_morning_time(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Step 5: Morning digest time."""
    raw = message.text.strip() if message.text else ""
    if not re.match(r"^\d{1,2}[:.]\d{2}$", raw):
        await message.answer("Пожалуйста, введи время в формате ЧЧ:ММ (например, 08:30):")
        return

    clean_time = raw.replace(".", ":")
    if len(clean_time) == 4:
        clean_time = "0" + clean_time

    if user.settings:
        user.settings.morning_digest_time = clean_time
        await session.flush()

    await state.set_state(OnboardingStates.evening_time)
    await message.answer(
        Texts.ONBOARDING_EVENING_TIME,
        reply_markup=skip_keyboard(),
    )


@router.message(OnboardingStates.evening_time)
async def process_onboarding_evening_time(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Step 6: Evening digest time and finish onboarding."""
    raw = message.text.strip() if message.text else ""
    if not re.match(r"^\d{1,2}[:.]\d{2}$", raw):
        await message.answer("Пожалуйста, введи время в формате ЧЧ:ММ (например, 21:00):")
        return

    clean_time = raw.replace(".", ":")
    if len(clean_time) == 4:
        clean_time = "0" + clean_time

    if user.settings:
        user.settings.evening_digest_time = clean_time

    repo = UserRepository(session)
    await repo.update_user(user, onboarding_completed=True)
    await session.flush()
    await state.clear()

    display_name = escape_html(user.display_name or user.first_name or "друг")
    await message.answer(
        Texts.ONBOARDING_DONE.format(name=display_name),
        reply_markup=main_menu_keyboard(),
    )
