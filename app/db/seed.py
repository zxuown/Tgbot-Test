"""Database seed script for demo and test data."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, date, datetime, time, timedelta

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.db.models.base import Base
from app.db.models.habit import Habit, HabitCompletion, HabitFrequency
from app.db.models.subscription import Subscription, SubscriptionTier
from app.db.models.task import Task, TaskPriority, TaskStatus
from app.db.models.user import User, UserSettings
from app.db.session import get_db_session, get_engine


async def seed() -> None:
    """Create sample data in database."""
    print("🌱 Seeding database...")

    # Ensure tables exist (helpful for SQLite or fresh DB)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_db_session() as session:
        # Check if demo user already exists
        user_repo = __import__("app.db.repositories.user_repo", fromlist=["UserRepository"]).UserRepository(session)
        existing = await user_repo.get_by_telegram_id(999999999)

        if existing:
            print("ℹ️ Demo user already exists, skipping seed.")
            return

        # 1. Create User
        user = User(
            telegram_id=999999999,
            username="demouser",
            first_name="Алексей",
            last_name="Фокусов",
            display_name="Алексей",
            language="ru",
            timezone="Europe/Moscow",
            role="Фрилансер",
            goal_30_days="Запустить MVP и найти 3 новых клиентов",
            onboarding_completed=True,
            is_active=True,
            last_active_at=datetime.now(UTC),
        )
        session.add(user)
        await session.flush()

        # 2. User Settings
        settings = UserSettings(
            user_id=user.id,
            morning_digest_enabled=True,
            morning_digest_time="08:30",
            evening_digest_enabled=True,
            evening_digest_time="21:00",
            working_hours_start="09:00",
            working_hours_end="18:00",
        )
        session.add(settings)

        # 3. Subscription
        sub = Subscription(
            user_id=user.id,
            tier=SubscriptionTier.PRO.value,
            started_at=datetime.now(UTC),
            ai_requests_this_month=2,
        )
        session.add(sub)

        # 4. Tasks
        today = date.today()
        tasks_data = [
            {
                "title": "Подготовить коммерческое предложение",
                "description": "Собрать смету и презентацию для нового клиента",
                "status": TaskStatus.PLANNED.value,
                "priority": TaskPriority.HIGH.value,
                "due_date": today,
                "due_time": time(14, 0),
                "estimated_minutes": 90,
                "category": "Работа",
                "is_important": True,
            },
            {
                "title": "Созвон с дизайнером по макетам",
                "description": "Обсудить главный экран Mini App",
                "status": TaskStatus.PLANNED.value,
                "priority": TaskPriority.MEDIUM.value,
                "due_date": today,
                "due_time": time(16, 30),
                "estimated_minutes": 45,
                "category": "Встречи",
                "is_important": False,
            },
            {
                "title": "Проверить отчёт по рекламе",
                "description": None,
                "status": TaskStatus.INBOX.value,
                "priority": TaskPriority.LOW.value,
                "due_date": today + timedelta(days=1),
                "estimated_minutes": 30,
                "category": "Маркетинг",
                "is_important": False,
            },
            {
                "title": "Оплатить хостинг и домен",
                "description": "Продлить VPS сервер на год",
                "status": TaskStatus.COMPLETED.value,
                "priority": TaskPriority.URGENT.value,
                "due_date": today,
                "completed_at": datetime.now(UTC) - timedelta(hours=2),
                "category": "Финансы",
                "is_important": True,
            },
        ]

        for td in tasks_data:
            t = Task(user_id=user.id, **td)
            session.add(t)

        # 5. Habits
        habit1 = Habit(
            user_id=user.id,
            title="Читать профессиональную литературу 20 мин",
            description="Книги по дизайну и архитектуре",
            frequency=HabitFrequency.DAILY.value,
            reminder_time="20:00",
            current_streak=5,
            best_streak=12,
            total_completions=25,
            start_date=today - timedelta(days=30),
        )
        session.add(habit1)
        await session.flush()

        # Add recent completions for habit1
        for i in range(1, 6):
            c = HabitCompletion(
                habit_id=habit1.id,
                completed_date=today - timedelta(days=i),
                skipped=False,
            )
            session.add(c)

        habit2 = Habit(
            user_id=user.id,
            title="Тренировка в зале",
            description="Силовая тренировка 45 мин",
            frequency=HabitFrequency.SPECIFIC_DAYS.value,
            days_of_week="1,3,5",
            reminder_time="18:30",
            current_streak=3,
            best_streak=8,
            total_completions=18,
            start_date=today - timedelta(days=40),
        )
        session.add(habit2)

        print("✅ Demo data seeded successfully! Demo user telegram_id: 999999999")


if __name__ == "__main__":
    asyncio.run(seed())
