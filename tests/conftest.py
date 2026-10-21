"""Pytest fixtures with in-memory SQLite database and test clients."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models.base import Base
from app.db.models.habit import Habit, HabitFrequency
from app.db.models.subscription import Subscription, SubscriptionTier
from app.db.models.task import Task, TaskPriority, TaskStatus
from app.db.models.user import User, UserSettings

# In-memory SQLite async engine for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create test engine and tables once for test session."""
    test_engine = create_async_engine(TEST_DB_URL, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session per test."""
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a standard test user with settings and free subscription."""
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Тест",
        last_name="Пользователь",
        display_name="Тест",
        language="ru",
        timezone="Europe/Moscow",
        onboarding_completed=True,
        is_active=True,
        last_active_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.flush()

    settings = UserSettings(user_id=user.id)
    db_session.add(settings)

    sub = Subscription(user_id=user.id, tier=SubscriptionTier.FREE.value)
    db_session.add(sub)

    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_user: User) -> Task:
    """Create a test task."""
    task = Task(
        user_id=test_user.id,
        title="Тестовая задача",
        description="Описание задачи",
        status=TaskStatus.INBOX.value,
        priority=TaskPriority.MEDIUM.value,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.flush()
    return task


@pytest_asyncio.fixture
async def test_habit(db_session: AsyncSession, test_user: User) -> Habit:
    """Create a test habit."""
    habit = Habit(
        user_id=test_user.id,
        title="Тестовая привычка",
        frequency=HabitFrequency.DAILY.value,
        start_date=datetime.now(UTC).date(),
    )
    db_session.add(habit)
    await db_session.flush()
    return habit
