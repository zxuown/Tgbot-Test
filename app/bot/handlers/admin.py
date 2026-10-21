"""Admin panel and management handlers (protected by AdminFilter)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.filters.admin import AdminFilter
from app.bot.keyboards import admin_keyboard
from app.bot.middlewares import MaintenanceMiddleware
from app.bot.states import AdminStates
from app.core.security import escape_html
from app.db.repositories.analytics_repo import AnalyticsRepository
from app.db.repositories.user_repo import UserRepository
from app.i18n.texts import Texts
from app.services.analytics_service import AnalyticsService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="admin")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    """Show admin dashboard overview."""
    analytics = AnalyticsService(session)
    stats = await analytics.get_admin_stats()

    text = (
        Texts.ADMIN_PANEL + "\n"
        + Texts.ADMIN_STATS.format(
            total_users=stats["total_users"],
            active_today=stats["active_today"],
            active_week=stats["active_week"],
            total_tasks=stats["total_tasks"],
            completed_tasks=stats["completed_tasks"],
            ai_requests=stats["ai_requests"],
        )
        + f"\n⚠️ Ошибок за 24ч: {stats['errors_24h']}\n"
        f"🔧 Режим обслуживания: {'ВКЛЮЧЕН ⚠️' if MaintenanceMiddleware.is_maintenance else 'Выключен'}\n"
    )

    await message.answer(text, reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """Refresh admin stats."""
    analytics = AnalyticsService(session)
    stats = await analytics.get_admin_stats()

    top_cmds = "\n".join(f"• {cmd}: {count}" for cmd, count in list(stats["top_commands"].items())[:6])

    text = (
        Texts.ADMIN_PANEL + "\n"
        + Texts.ADMIN_STATS.format(
            total_users=stats["total_users"],
            active_today=stats["active_today"],
            active_week=stats["active_week"],
            total_tasks=stats["total_tasks"],
            completed_tasks=stats["completed_tasks"],
            ai_requests=stats["ai_requests"],
        )
        + f"\n📊 <b>Популярные команды (7 дней):</b>\n{top_cmds or 'Нет данных'}\n"
    )

    await callback.message.edit_text(text, reply_markup=admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_maintenance")
async def cb_toggle_maintenance(callback: CallbackQuery, session: AsyncSession) -> None:
    """Toggle system maintenance mode."""
    MaintenanceMiddleware.is_maintenance = not MaintenanceMiddleware.is_maintenance
    status_str = "ВКЛЮЧЕН" if MaintenanceMiddleware.is_maintenance else "ВЫКЛЮЧЕН"

    audit = AnalyticsRepository(session)
    await audit.log_admin_action(
        admin_telegram_id=callback.from_user.id,
        action="toggle_maintenance",
        details=f"Maintenance mode set to {status_str}",
    )

    await callback.answer(f"Режим обслуживания: {status_str}!", show_alert=True)
    await cb_admin_stats(callback, session)


@router.callback_query(F.data == "admin_find_user")
async def cb_admin_find_user(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for telegram_id to look up."""
    await state.set_state(AdminStates.search_user)
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    await callback.message.edit_text("🔍 Введи Telegram ID пользователя для поиска:", reply_markup=builder.as_markup())
    await callback.answer()


@router.message(AdminStates.search_user)
async def process_user_search(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Lookup user by telegram_id."""
    raw = message.text.strip() if message.text else ""
    await state.clear()

    try:
        tg_id = int(raw)
    except ValueError:
        await message.answer("⚠️ Некорректный Telegram ID.", reply_markup=admin_keyboard())
        return

    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(tg_id)

    if not user:
        await message.answer(f"Пользователь с Telegram ID <code>{tg_id}</code> не найден.", reply_markup=admin_keyboard())
        return

    sub_tier = user.subscription.tier if user.subscription else "free"
    created = user.created_at.strftime("%d.%m.%Y")
    last_act = user.last_active_at.strftime("%d.%m.%Y %H:%M") if user.last_active_at else "никогда"

    text = (
        f"👤 <b>Пользователь #{user.id}</b>\n\n"
        f"• Telegram ID: <code>{user.telegram_id}</code>\n"
        f"• Username: @{user.username or 'нет'}\n"
        f"• Имя: {escape_html(user.first_name or '')}\n"
        f"• Роль: {user.role or 'не указана'}\n"
        f"• Таймзона: {user.timezone}\n"
        f"• Тариф: {sub_tier.upper()}\n"
        f"• Зарегистрирован: {created}\n"
        f"• Активность: {last_act}\n"
        f"• Заблокирован: {'Да' if user.is_blocked else 'Нет'}\n"
    )

    await message.answer(text, reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Start broadcast scenario."""
    await state.set_state(AdminStates.broadcast_message)
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    await callback.message.edit_text("📢 Введи сообщение для рассылки всем активным пользователям:", reply_markup=builder.as_markup())
    await callback.answer()


@router.message(AdminStates.broadcast_message)
async def process_broadcast(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Broadcast message to all active users."""
    text = message.text.strip() if message.text else ""
    await state.clear()

    if not text:
        await message.answer("Отменено: пустое сообщение.", reply_markup=admin_keyboard())
        return

    repo = UserRepository(session)
    users = await repo.get_all_active_users_with_settings()

    count = 0
    from app.services.notification_service import NotificationService
    notif = NotificationService(session)

    broadcast_payload = f"📢 <b>Системное уведомление:</b>\n\n{escape_html(text)}"
    for u in users:
        ok = await notif.send_message_safe(message.bot, u.telegram_id, broadcast_payload)
        if ok:
            count += 1

    await message.answer(f"✅ Рассылка завершена. Успешно доставлено: {count} из {len(users)}.", reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin_cancel")
async def cb_admin_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel admin action."""
    await state.clear()
    await cb_admin_stats(callback, callback.message.bot)  # type: ignore[arg-type]
