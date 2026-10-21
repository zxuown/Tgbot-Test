"""Unit tests for Telegram bot handler logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers.menu import cmd_cancel
from app.bot.handlers.start import cmd_start
from app.bot.states import TaskCreationStates
from app.db.models.user import User


@pytest.fixture
def mock_message():
    """Create a mock Telegram message."""
    msg = MagicMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 12345
    msg.from_user.username = "testuser"
    msg.from_user.first_name = "Test"
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def fsm_context():
    """Create an in-memory FSMContext."""
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=12345, user_id=12345)
    return FSMContext(storage=storage, key=key)


@pytest.mark.asyncio
async def test_cmd_cancel_in_fsm_state(mock_message, fsm_context: FSMContext):
    # Set state
    await fsm_context.set_state(TaskCreationStates.title)
    assert await fsm_context.get_state() == TaskCreationStates.title.state

    # Run cancel
    await cmd_cancel(mock_message, fsm_context)

    # State must be cleared
    assert await fsm_context.get_state() is None
    assert mock_message.answer.called
    args, _ = mock_message.answer.call_args
    assert "отменено" in args[0].lower()


@pytest.mark.asyncio
async def test_cmd_cancel_without_active_state(mock_message, fsm_context: FSMContext):
    await fsm_context.clear()
    await cmd_cancel(mock_message, fsm_context)

    assert mock_message.answer.called
    args, _ = mock_message.answer.call_args
    assert "нет активного действия" in args[0].lower()


@pytest.mark.asyncio
async def test_cmd_start_new_user(mock_message, fsm_context: FSMContext, test_user: User):
    test_user.onboarding_completed = False

    await cmd_start(mock_message, test_user, fsm_context)

    # Must prompt for name and set state to OnboardingStates.name
    state = await fsm_context.get_state()
    assert state == "OnboardingStates:name"
    assert mock_message.answer.call_count >= 2


@pytest.mark.asyncio
async def test_user_middleware_with_telegram_update(db_session):
    """Test that UserMiddleware correctly extracts user from Update object and populates data['user']."""
    from datetime import datetime

    from aiogram.types import Chat, Update
    from aiogram.types import Message as TgMessage
    from aiogram.types import User as TgUser

    from app.bot.middlewares.db import UserMiddleware

    tg_user = TgUser(id=778899, is_bot=False, first_name="MiddlewareTest", username="midtest")
    tg_message = TgMessage(
        message_id=999,
        date=datetime.now(),
        chat=Chat(id=778899, type="private"),
        from_user=tg_user,
        text="/start",
    )
    update = Update(update_id=1001, message=tg_message)

    middleware = UserMiddleware()
    data = {
        "session": db_session,
        "event_from_user": tg_user,
    }

    async def dummy_handler(event, handler_data):
        return handler_data.get("user")

    user_result = await middleware(dummy_handler, update, data)

    assert user_result is not None
    assert user_result.telegram_id == 778899
    assert user_result.first_name == "MiddlewareTest"
    assert "user" in data


@pytest.mark.asyncio
async def test_user_middleware_fallback_extraction_without_event_from_user(db_session):
    """Test that UserMiddleware falls back to extracting user from update.event if event_from_user is absent."""
    from datetime import datetime

    from aiogram.types import Chat, Update
    from aiogram.types import Message as TgMessage
    from aiogram.types import User as TgUser

    from app.bot.middlewares.db import UserMiddleware

    tg_user = TgUser(id=445566, is_bot=False, first_name="FallbackTest")
    tg_message = TgMessage(
        message_id=998,
        date=datetime.now(),
        chat=Chat(id=445566, type="private"),
        from_user=tg_user,
        text="/menu",
    )
    update = Update(update_id=1002, message=tg_message)

    middleware = UserMiddleware()
    # No event_from_user in data:
    data = {
        "session": db_session,
    }

    async def dummy_handler(event, handler_data):
        return handler_data.get("user")

    user_result = await middleware(dummy_handler, update, data)

    assert user_result is not None
    assert user_result.telegram_id == 445566
    assert data["user"].telegram_id == 445566


@pytest.mark.asyncio
async def test_task_creation_time_error_then_success(mock_message, fsm_context: FSMContext):
    """Test entering 30:00 produces informative error, keeps state, then 14:00 advances to estimated."""
    from app.bot.handlers.tasks import process_task_due_time

    await fsm_context.set_state(TaskCreationStates.due_time)

    # 1. Enter invalid hour 30:00
    mock_message.text = "30:00"
    await process_task_due_time(mock_message, fsm_context)

    # Must stay on due_time
    assert await fsm_context.get_state() == TaskCreationStates.due_time.state
    assert mock_message.answer.called
    err_text = mock_message.answer.call_args[0][0]
    assert "00:00 до 23:59" in err_text

    # 2. Enter valid time 14:00
    mock_message.text = "14:00"
    await process_task_due_time(mock_message, fsm_context)

    # Must advance to estimated
    assert await fsm_context.get_state() == TaskCreationStates.estimated.state
    data = await fsm_context.get_data()
    assert data.get("due_time") == "14:00"


@pytest.mark.asyncio
async def test_task_creation_minute_error(mock_message, fsm_context: FSMContext):
    """Test entering 14:70 produces minute range error and stays on due_time."""
    from app.bot.handlers.tasks import process_task_due_time

    await fsm_context.set_state(TaskCreationStates.due_time)

    mock_message.text = "14:70"
    await process_task_due_time(mock_message, fsm_context)

    assert await fsm_context.get_state() == TaskCreationStates.due_time.state
    err_text = mock_message.answer.call_args[0][0]
    assert "Минуты должны быть от 00 до 59" in err_text


@pytest.mark.asyncio
async def test_task_creation_bare_hour(mock_message, fsm_context: FSMContext):
    """Test entering '14' is accepted as 14:00."""
    from app.bot.handlers.tasks import process_task_due_time

    await fsm_context.set_state(TaskCreationStates.due_time)

    mock_message.text = "14"
    await process_task_due_time(mock_message, fsm_context)

    assert await fsm_context.get_state() == TaskCreationStates.estimated.state
    data = await fsm_context.get_data()
    assert data.get("due_time") == "14:00"


@pytest.mark.asyncio
async def test_task_creation_cancel_button_during_time(fsm_context: FSMContext):
    """Test pressing 'Cancel' inline button during time input clears state."""
    from app.bot.handlers.menu import cb_step_cancel

    await fsm_context.set_state(TaskCreationStates.due_time)

    mock_cb = MagicMock()
    mock_cb.message = MagicMock()
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await cb_step_cancel(mock_cb, fsm_context)

    assert await fsm_context.get_state() is None
    assert mock_cb.message.edit_text.called


@pytest.mark.asyncio
async def test_task_creation_cancel_command_during_time(mock_message, fsm_context: FSMContext):
    """Test /cancel command during time input clears state."""
    await fsm_context.set_state(TaskCreationStates.due_time)

    await cmd_cancel(mock_message, fsm_context)

    assert await fsm_context.get_state() is None


@pytest.mark.asyncio
async def test_menu_button_during_active_fsm(mock_message, test_user, db_session, fsm_context: FSMContext):
    """Test pressing main menu 'Tasks' button clears FSM and opens tasks list."""
    from app.bot.handlers.menu import menu_nav_tasks

    await fsm_context.set_state(TaskCreationStates.due_time)

    await menu_nav_tasks(mock_message, test_user, db_session, fsm_context)

    # State must be cleared!
    assert await fsm_context.get_state() is None
    assert mock_message.answer.called


@pytest.mark.asyncio
async def test_task_creation_full_scenario(mock_message, test_user, db_session, fsm_context: FSMContext):
    """Test full task creation flow from title to category and verify FSM cleanup."""
    from app.bot.handlers.tasks import (
        process_task_category,
        process_task_desc,
        process_task_due_date,
        process_task_due_time,
        process_task_estimated,
        process_task_priority,
    )
    from app.db.repositories.task_repo import TaskRepository

    await fsm_context.clear()
    await fsm_context.set_state(TaskCreationStates.title)
    await fsm_context.update_data(title="Запустить проект")

    # Description
    await fsm_context.set_state(TaskCreationStates.description)
    mock_message.text = "Важное описание"
    await process_task_desc(mock_message, fsm_context)
    assert await fsm_context.get_state() == TaskCreationStates.priority.state

    # Priority callback
    mock_cb = MagicMock()
    mock_cb.data = "priority_high"
    mock_cb.message = MagicMock()
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()
    await process_task_priority(mock_cb, fsm_context)
    assert await fsm_context.get_state() == TaskCreationStates.due_date.state

    # Due date
    mock_message.text = "25.10.2026"
    await process_task_due_date(mock_message, fsm_context)
    assert await fsm_context.get_state() == TaskCreationStates.due_time.state

    # Due time (first error, then valid)
    mock_message.text = "30:00"
    await process_task_due_time(mock_message, fsm_context)
    assert await fsm_context.get_state() == TaskCreationStates.due_time.state

    mock_message.text = "14:00"
    await process_task_due_time(mock_message, fsm_context)
    assert await fsm_context.get_state() == TaskCreationStates.estimated.state

    # Estimated
    mock_message.text = "45"
    await process_task_estimated(mock_message, fsm_context)
    assert await fsm_context.get_state() == TaskCreationStates.category.state

    # Category -> Creates task
    mock_message.text = "Разработка"
    await process_task_category(mock_message, test_user, db_session, fsm_context)

    # State must be completely cleared after creation
    assert await fsm_context.get_state() is None

    # Check task exists in DB
    task_repo = TaskRepository(db_session)
    tasks = await task_repo.get_user_tasks(test_user.id)
    created_task = next((t for t in tasks if t.title == "Запустить проект"), None)
    assert created_task is not None
    assert created_task.category == "Разработка"
    assert created_task.priority == "high"
    assert str(created_task.due_time) == "14:00:00"
    assert created_task.estimated_minutes == 45
