"""Task handlers: list, pagination, step-by-step & natural language creation, actions."""

from __future__ import annotations

import math
from datetime import date
from typing import TYPE_CHECKING, Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    TaskCallback,
    ai_parsed_task_keyboard,
    main_menu_keyboard,
    skip_keyboard,
    task_actions_keyboard,
    task_filter_keyboard,
    task_list_keyboard,
    task_priority_keyboard,
)
from app.bot.states import TaskCreationStates
from app.core.logging import get_logger
from app.core.security import escape_html
from app.db.models.task import TaskPriority, TaskStatus
from app.i18n.texts import Texts
from app.services.ai_service import AIService
from app.services.task_service import TaskService
from app.utils.helpers import (
    format_date_ru,
    format_minutes,
    parse_date_ru,
    parse_time,
    parse_time_input,
    priority_emoji,
    status_emoji,
    validate_time_input,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models.user import User

router = Router(name="tasks")


# ── Listing & Pagination ───────────────────────────────────────────────────

@router.message(Command("tasks"))
@router.message(F.text == Texts.BTN_TASKS)
async def cmd_tasks(message: Message, user: User, session: AsyncSession) -> None:
    """Show list of active tasks."""
    await _show_task_list(message, user, session, filter_type="all", page=1)


@router.callback_query(TaskCallback.filter(F.action == "page"))
async def cb_task_page(
    callback: CallbackQuery,
    callback_data: TaskCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Handle pagination and filter switching."""
    await _show_task_list(
        callback.message,
        user,
        session,
        filter_type=callback_data.filter_type,
        page=callback_data.page,
        is_edit=True,
    )
    await callback.answer()


@router.callback_query(TaskCallback.filter(F.action == "filter"))
async def cb_task_filter_menu(callback: CallbackQuery) -> None:
    """Show filter selection menu."""
    await callback.message.edit_text("🔍 Выбери фильтр для задач:", reply_markup=task_filter_keyboard())
    await callback.answer()


async def _show_task_list(
    message: Message,
    user: User,
    session: AsyncSession,
    filter_type: str = "all",
    page: int = 1,
    is_edit: bool = False,
) -> None:
    """Render paginated task list with filter."""
    service = TaskService(session)
    per_page = 5
    offset = (page - 1) * per_page

    kwargs: dict[str, Any] = {"limit": per_page, "offset": offset}
    filter_label = ""

    if filter_type == "today":
        kwargs["due_date"] = date.today()
        filter_label = " (на сегодня)"
    elif filter_type == "overdue":
        kwargs["overdue"] = True
        filter_label = " (просроченные)"
    elif filter_type == "high":
        kwargs["priority"] = TaskPriority.HIGH.value
        filter_label = " (высокий приоритет)"
    elif filter_type == "completed":
        kwargs["status"] = TaskStatus.COMPLETED.value
        filter_label = " (выполненные)"

    tasks = await service.list_tasks(user_id=user.id, **kwargs)

    # Count total for pagination
    repo = service.task_repo
    count_kwargs = {k: v for k, v in kwargs.items() if k not in ("limit", "offset")}
    total = await repo.count_user_tasks(user_id=user.id, **count_kwargs)
    pages = max(1, math.ceil(total / per_page))

    text = Texts.TASK_LIST_HEADER.format(filter_label=filter_label)
    if not tasks:
        text += f"\n{Texts.TASK_LIST_EMPTY}"
    else:
        text += f"Всего задач: {total}\n"

    kb = task_list_keyboard(tasks, page=page, total_pages=pages, filter_type=filter_type)

    if is_edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


# ── Task Detail & Actions ──────────────────────────────────────────────────

@router.callback_query(TaskCallback.filter(F.action == "view"))
async def cb_task_view(
    callback: CallbackQuery,
    callback_data: TaskCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Show details of a single task."""
    service = TaskService(session)
    task = await service.get_task(callback_data.task_id, user.id)
    if not task:
        await callback.answer(Texts.TASK_NOT_FOUND, show_alert=True)
        return

    desc = f"📄 <i>{escape_html(task.description)}</i>\n\n" if task.description else ""
    due_d = f"📅 Срок: {format_date_ru(task.due_date)}\n" if task.due_date else ""
    due_t = f"⏰ Время: {task.due_time.strftime('%H:%M')}\n" if task.due_time else ""
    est = f"⏱ Оценка: {format_minutes(task.estimated_minutes)}\n" if task.estimated_minutes else ""
    cat = f"🏷 Категория: {escape_html(task.category)}\n" if task.category else ""
    imp = "⭐ <b>Важная задача</b>\n" if task.is_important else ""
    tags = f"🔖 Теги: {', '.join(t.tag for t in task.tags)}\n" if task.tags else ""
    status_label = f"{status_emoji(task.status)} {task.status}"
    priority_label = f"{priority_emoji(task.priority)} {task.priority}"

    text = Texts.TASK_DETAIL.format(
        title=escape_html(task.title),
        description=desc,
        status=status_label,
        priority=priority_label,
        due_date=due_d,
        due_time=due_t,
        estimated=est,
        category=cat,
        tags=tags,
        created_at=task.created_at.strftime("%d.%m.%Y %H:%M"),
    )
    if imp:
        text = imp + text

    kb = task_actions_keyboard(task, filter_type=callback_data.filter_type, page=callback_data.page)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(TaskCallback.filter(F.action == "complete"))
async def cb_task_complete(
    callback: CallbackQuery,
    callback_data: TaskCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Mark task as complete."""
    service = TaskService(session)
    task = await service.complete_task(callback_data.task_id, user.id)
    if task:
        await callback.answer(Texts.TASK_COMPLETED.format(title=task.title[:30]), show_alert=True)
        await _show_task_list(callback.message, user, session, filter_type=callback_data.filter_type, page=callback_data.page, is_edit=True)
    else:
        await callback.answer(Texts.TASK_NOT_FOUND, show_alert=True)


@router.callback_query(TaskCallback.filter(F.action == "delete"))
async def cb_task_delete(
    callback: CallbackQuery,
    callback_data: TaskCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Delete task."""
    service = TaskService(session)
    deleted = await service.delete_task(callback_data.task_id, user.id)
    if deleted:
        await callback.answer(Texts.TASK_DELETED)
        await _show_task_list(callback.message, user, session, filter_type=callback_data.filter_type, page=callback_data.page, is_edit=True)
    else:
        await callback.answer(Texts.TASK_NOT_FOUND, show_alert=True)


@router.callback_query(TaskCallback.filter(F.action == "toggle_imp"))
async def cb_task_toggle_imp(
    callback: CallbackQuery,
    callback_data: TaskCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Toggle task importance flag."""
    service = TaskService(session)
    task = await service.get_task(callback_data.task_id, user.id)
    if task:
        new_val = not task.is_important
        await service.update_task(task.id, user.id, is_important=new_val)
        star = "добавлена в важные ⭐" if new_val else "убрана из важных"
        await callback.answer(f"Задача {star}")
        # Refresh detail
        await cb_task_view(callback, callback_data, user, session)
    else:
        await callback.answer(Texts.TASK_NOT_FOUND, show_alert=True)


# ── Step-by-Step Task Creation (Mode 1) ────────────────────────────────────

@router.message(Command("add_task"))
@router.callback_query(F.data == "act_create_task")
async def cmd_add_task(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Start task creation FSM."""
    await state.clear()
    await state.set_state(TaskCreationStates.title)
    text = (
        "➕ <b>Создание задачи:</b>\n\n"
        "Введи название задачи\n"
        "<i>(или просто напиши текст вроде «Позвонить клиенту завтра в 14:00», и я разберу его автоматически)</i>:"
    )
    if isinstance(event, CallbackQuery):
        await event.message.answer(text)
        await event.answer()
    else:
        await event.answer(text)


@router.message(TaskCreationStates.title)
async def process_task_title(message: Message, user: User, state: FSMContext) -> None:
    """Handle task title or natural language entry."""
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer(Texts.ERROR_INVALID_INPUT)
        return

    # Check if this text contains rich natural language attributes (date/time/priority)
    has_date = parse_date_ru(text) is not None
    has_time = parse_time(text) is not None
    has_meta = any(w in text.lower() for w in ["завтра", "к пятнице", "срочно", "высокий приоритет", "часа", "мин"])

    if has_date or has_time or has_meta:
        # Route to AI parser
        ai = AIService()
        parsed = await ai.parse_task_from_text(text)
        await state.update_data(parsed_task=parsed)

        p_date = f"📅 Дата: {parsed.get('due_date')}\n" if parsed.get("due_date") else ""
        p_time = f"⏰ Время: {parsed.get('due_time')}\n" if parsed.get("due_time") else ""
        p_dur = f"⏱ Длительность: {format_minutes(parsed.get('estimated_minutes'))}\n" if parsed.get("estimated_minutes") else ""
        p_cat = f"🏷 Категория: {parsed.get('category')}\n" if parsed.get("category") else ""
        p_prio = f"🔺 Приоритет: {priority_emoji(parsed.get('priority', 'medium'))} {parsed.get('priority', 'medium')}\n"

        confirm_msg = Texts.AI_TASK_PARSED.format(
            title=escape_html(parsed.get("title", text)),
            due_date=p_date,
            due_time=p_time,
            priority=p_prio,
            estimated=p_dur,
            category=p_cat,
        )
        await message.answer(confirm_msg, reply_markup=ai_parsed_task_keyboard())
        return

    # Regular step-by-step mode
    await state.update_data(title=text)
    await state.set_state(TaskCreationStates.description)
    await message.answer(Texts.TASK_ENTER_DESCRIPTION, reply_markup=skip_keyboard())


@router.callback_query(F.data == "ai_confirm_task")
async def cb_confirm_ai_task(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Confirm AI-parsed task."""
    data = await state.get_data()
    parsed = data.get("parsed_task")
    await state.clear()

    if not parsed:
        await callback.answer("Данные задачи устарели. Попробуй снова.", show_alert=True)
        return

    service = TaskService(session)
    due_d = date.fromisoformat(parsed["due_date"]) if parsed.get("due_date") else None
    due_t = parse_time(parsed["due_time"]) if parsed.get("due_time") else None

    task, err = await service.create_task(
        user_id=user.id,
        title=parsed.get("title", "Задача"),
        priority=parsed.get("priority", "medium"),
        due_date=due_d,
        due_time=due_t,
        estimated_minutes=parsed.get("estimated_minutes"),
        category=parsed.get("category"),
        source="ai",
    )

    if err:
        await callback.message.edit_text(f"⚠️ {err}")
    else:
        await callback.message.edit_text(
            Texts.TASK_CREATED.format(title=escape_html(task.title)),
            reply_markup=task_actions_keyboard(task),
        )
    await callback.answer()


@router.callback_query(F.data == "ai_cancel_task")
async def cb_cancel_ai_task(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel AI parsed task."""
    await state.clear()
    await callback.message.edit_text(Texts.CANCELLED)
    await callback.answer()


@router.message(TaskCreationStates.description)
async def process_task_desc(message: Message, state: FSMContext) -> None:
    """Step 2: Description."""
    desc = message.text.strip() if message.text else None
    await state.update_data(description=desc)
    await state.set_state(TaskCreationStates.priority)
    await message.answer(Texts.TASK_SELECT_PRIORITY, reply_markup=task_priority_keyboard())


@router.message(TaskCreationStates.priority)
async def process_task_priority_text_fallback(message: Message) -> None:
    """Prompt user to choose priority via inline buttons if they typed text."""
    await message.answer(
        "Выбери приоритет задачи с помощью кнопок ниже или нажми «Отмена»:",
        reply_markup=task_priority_keyboard(),
    )


@router.callback_query(F.data.startswith("priority_"))
async def process_task_priority(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Priority."""
    prio = callback.data.replace("priority_", "")
    await state.update_data(priority=prio)
    await state.set_state(TaskCreationStates.due_date)
    await callback.message.edit_text(Texts.TASK_ENTER_DUE_DATE, reply_markup=skip_keyboard(allow_back=False))
    await callback.answer()


@router.message(TaskCreationStates.due_date)
async def process_task_due_date(message: Message, state: FSMContext) -> None:
    """Step 4: Due date."""
    parsed = parse_date_ru(message.text) if message.text else None
    if not parsed:
        await message.answer(
            "Не удалось распознать дату. Напиши, например, «завтра», «в пятницу» или «25.10.2026» (или нажми «Пропустить»):",
            reply_markup=skip_keyboard(allow_back=False),
        )
        return

    await state.update_data(due_date=parsed.isoformat())
    await state.set_state(TaskCreationStates.due_time)
    await message.answer(Texts.TASK_ENTER_DUE_TIME, reply_markup=skip_keyboard(allow_back=True))


@router.message(TaskCreationStates.due_time)
async def process_task_due_time(message: Message, state: FSMContext) -> None:
    """Step 5: Due time."""
    parsed, err_code, err_msg = validate_time_input(message.text or "")
    if not parsed:
        prompt = err_msg or "Не удалось распознать время. Напиши, например, «14:00», «14.00» или «14»:"
        await message.answer(prompt, reply_markup=skip_keyboard(allow_back=True))
        return

    await state.update_data(due_time=parsed.strftime("%H:%M"))
    await state.set_state(TaskCreationStates.estimated)
    await message.answer(Texts.TASK_ENTER_ESTIMATED, reply_markup=skip_keyboard(allow_back=True))


@router.message(TaskCreationStates.estimated)
async def process_task_estimated(message: Message, state: FSMContext) -> None:
    """Step 6: Estimated minutes."""
    raw = message.text.strip() if message.text else ""
    if raw:
        try:
            val = int(raw)
            if val <= 0 or val > 1440:
                await message.answer(
                    "Укажи длительность числом минут от 1 до 1440 (например, 30 или 120) или нажми «Пропустить»:",
                    reply_markup=skip_keyboard(allow_back=True),
                )
                return
            await state.update_data(estimated_minutes=val)
        except ValueError:
            await message.answer(
                "Длительность должна быть числом минут (например, 45) или нажми «Пропустить»:",
                reply_markup=skip_keyboard(allow_back=True),
            )
            return

    await state.set_state(TaskCreationStates.category)
    await message.answer(Texts.TASK_ENTER_CATEGORY, reply_markup=skip_keyboard(allow_back=True))


@router.message(TaskCreationStates.category)
async def process_task_category(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Step 7: Category & final creation."""
    cat = message.text.strip() if message.text else "Общее"
    data = await state.get_data()

    try:
        service = TaskService(session)
        due_d = date.fromisoformat(data["due_date"]) if data.get("due_date") else None
        due_t = parse_time_input(data.get("due_time")) if data.get("due_time") else None

        task, err = await service.create_task(
            user_id=user.id,
            title=data.get("title", "Задача"),
            description=data.get("description"),
            priority=data.get("priority", "medium"),
            due_date=due_d,
            due_time=due_t,
            estimated_minutes=data.get("estimated_minutes"),
            category=cat,
        )

        if err:
            await message.answer(f"⚠️ {err}", reply_markup=main_menu_keyboard())
        else:
            await message.answer(
                Texts.TASK_CREATED.format(title=escape_html(task.title)),
                reply_markup=task_actions_keyboard(task),
            )
    except Exception as exc:
        logger.error("Error creating task: %s", exc)
        await message.answer("⚠️ Ошибка сохранения задачи. Попробуй позже.", reply_markup=main_menu_keyboard())
    finally:
        await state.clear()


# ── Step Skip Callbacks (Task Creation) ───────────────────────────────────

@router.callback_query(F.data == "step_skip", TaskCreationStates.description)
async def cb_task_skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip description."""
    await state.set_state(TaskCreationStates.priority)
    await callback.message.edit_text(Texts.TASK_SELECT_PRIORITY, reply_markup=task_priority_keyboard())
    await callback.answer()


@router.callback_query(F.data == "step_skip", TaskCreationStates.due_date)
async def cb_task_skip_due_date(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip due date."""
    await state.set_state(TaskCreationStates.due_time)
    await callback.message.edit_text(Texts.TASK_ENTER_DUE_TIME, reply_markup=skip_keyboard(allow_back=True))
    await callback.answer()


@router.callback_query(F.data == "step_skip", TaskCreationStates.due_time)
async def cb_task_skip_due_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip due time."""
    await state.set_state(TaskCreationStates.estimated)
    await callback.message.edit_text(Texts.TASK_ENTER_ESTIMATED, reply_markup=skip_keyboard(allow_back=True))
    await callback.answer()


@router.callback_query(F.data == "step_skip", TaskCreationStates.estimated)
async def cb_task_skip_estimated(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip estimated duration."""
    await state.set_state(TaskCreationStates.category)
    await callback.message.edit_text(Texts.TASK_ENTER_CATEGORY, reply_markup=skip_keyboard(allow_back=True))
    await callback.answer()


@router.callback_query(F.data == "step_skip", TaskCreationStates.category)
async def cb_task_skip_category(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Skip category and complete task creation."""
    data = await state.get_data()

    try:
        service = TaskService(session)
        due_d = date.fromisoformat(data["due_date"]) if data.get("due_date") else None
        due_t = parse_time_input(data.get("due_time")) if data.get("due_time") else None

        task, err = await service.create_task(
            user_id=user.id,
            title=data.get("title", "Задача"),
            description=data.get("description"),
            priority=data.get("priority", "medium"),
            due_date=due_d,
            due_time=due_t,
            estimated_minutes=data.get("estimated_minutes"),
            category="Общее",
        )

        if err:
            await callback.message.edit_text(f"⚠️ {err}")
        else:
            await callback.message.edit_text(
                Texts.TASK_CREATED.format(title=escape_html(task.title)),
                reply_markup=task_actions_keyboard(task),
            )
    except Exception as exc:
        logger.error("Error creating task on skip category: %s", exc)
        await callback.message.edit_text("⚠️ Ошибка сохранения задачи.")
    finally:
        await state.clear()
        await callback.answer()


# ── Step Back Callbacks (Task Creation) ───────────────────────────────────

@router.callback_query(F.data == "step_back", TaskCreationStates.due_time)
async def cb_task_back_to_date(callback: CallbackQuery, state: FSMContext) -> None:
    """Back from due time to due date."""
    await state.set_state(TaskCreationStates.due_date)
    await callback.message.edit_text(Texts.TASK_ENTER_DUE_DATE, reply_markup=skip_keyboard(allow_back=False))
    await callback.answer()


@router.callback_query(F.data == "step_back", TaskCreationStates.estimated)
async def cb_task_back_to_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Back from estimated to due time."""
    await state.set_state(TaskCreationStates.due_time)
    await callback.message.edit_text(Texts.TASK_ENTER_DUE_TIME, reply_markup=skip_keyboard(allow_back=True))
    await callback.answer()


@router.callback_query(F.data == "step_back", TaskCreationStates.category)
async def cb_task_back_to_estimated(callback: CallbackQuery, state: FSMContext) -> None:
    """Back from category to estimated."""
    await state.set_state(TaskCreationStates.estimated)
    await callback.message.edit_text(Texts.TASK_ENTER_ESTIMATED, reply_markup=skip_keyboard(allow_back=True))
    await callback.answer()
