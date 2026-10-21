"""Settings command and callback handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.keyboards import SettingsCallback, onboarding_timezone_keyboard, settings_keyboard
from app.bot.states import OnboardingStates
from app.core.security import escape_html
from app.i18n.texts import Texts
from app.services.subscription_service import SubscriptionService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

router = Router(name="settings")


@router.message(Command("settings"))
@router.message(F.text == Texts.BTN_SETTINGS)
@router.callback_query(F.data == "act_open_settings")
async def cmd_settings(event: Message | CallbackQuery, user: User, session: AsyncSession) -> None:
    """Show settings menu."""
    sub_service = SubscriptionService(session)
    is_pro = await sub_service.is_pro(user.id)

    s = user.settings
    m_on = s.morning_digest_enabled if s else True
    e_on = s.evening_digest_enabled if s else True
    m_time = s.morning_digest_time if s else "08:00"
    e_time = s.evening_digest_time if s else "21:00"

    name = escape_html(user.display_name or user.first_name or "друг")
    tz = escape_html(user.timezone)

    text = (
        f"⚙️ <b>Настройки профиля:</b>\n\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"🌍 <b>Часовой пояс:</b> {tz}\n"
        f"🌅 <b>Утренний дайджест:</b> {'Вкл' if m_on else 'Выкл'} ({m_time})\n"
        f"🌙 <b>Вечерний итог:</b> {'Вкл' if e_on else 'Выкл'} ({e_time})\n"
        f"💎 <b>Тариф:</b> {'PRO' if is_pro else 'Free'}\n"
    )

    kb = settings_keyboard(is_pro=is_pro, morning_enabled=m_on, evening_enabled=e_on)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb)


@router.callback_query(SettingsCallback.filter(F.action == "toggle_morning"))
async def cb_toggle_morning(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """Toggle morning digest setting."""
    if user.settings:
        user.settings.morning_digest_enabled = not user.settings.morning_digest_enabled
        await session.flush()
    await cmd_settings(callback, user, session)


@router.callback_query(SettingsCallback.filter(F.action == "toggle_evening"))
async def cb_toggle_evening(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """Toggle evening digest setting."""
    if user.settings:
        user.settings.evening_digest_enabled = not user.settings.evening_digest_enabled
        await session.flush()
    await cmd_settings(callback, user, session)


@router.callback_query(SettingsCallback.filter(F.action == "timezone"))
async def cb_settings_timezone(callback: CallbackQuery) -> None:
    """Change timezone from settings."""
    await callback.message.edit_text(Texts.ONBOARDING_TIMEZONE, reply_markup=onboarding_timezone_keyboard())
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == "reonboard"))
async def cb_reonboard(callback: CallbackQuery, state: FSMContext) -> None:
    """Re-run onboarding flow."""
    await state.clear()
    await state.set_state(OnboardingStates.name)
    await callback.message.edit_text(Texts.ONBOARDING_NAME)
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == "upgrade_pro"))
async def cb_upgrade_pro(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """Show PRO upgrade screen and handle mock payment."""
    sub_service = SubscriptionService(session)
    is_pro = await sub_service.is_pro(user.id)

    if is_pro:
        await callback.answer("У тебя уже активна подписка PRO! 💎", show_alert=True)
        return

    text = (
        Texts.SUB_PRO_TITLE + "\n"
        + Texts.SUB_PRO_DETAILS + "\n"
        "💳 <i>(В тестовом режиме подключение происходит моментально в 1 клик)</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Активировать PRO (Тест)", callback_data="do_mock_upgrade")
    builder.button(text="◀️ Назад", callback_data="act_open_settings")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "do_mock_upgrade")
async def cb_do_mock_upgrade(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """Perform mock upgrade to Pro."""
    sub_service = SubscriptionService(session)
    await sub_service.upgrade_to_pro(user.id, payment_provider="mock", payment_id="demo_checkout")

    await callback.message.edit_text(
        "🎉 <b>Поздравляем! Тариф PRO успешно активирован!</b>\n\n"
        "Теперь тебе доступны:\n"
        "• Безлимитные AI-разборы и коучинг\n"
        "• Безлимитные задачи и привычки\n"
        "• Еженедельные аналитические отчеты",
        reply_markup=settings_keyboard(is_pro=True),
    )
    await callback.answer("PRO активирован! 💎", show_alert=True)
