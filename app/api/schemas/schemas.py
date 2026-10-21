"""Pydantic v2 schemas for the Focus Bot API."""

from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime as dt_datetime
from datetime import time as dt_time

from pydantic import BaseModel, ConfigDict, Field

# ── Error schemas ───────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Single error detail."""
    code: str
    message: str


class ErrorWrapper(BaseModel):
    """Unified error envelope."""
    error: ErrorResponse


# ── Task schemas ────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    """Schema for creating a new task."""
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str = Field(default="medium", pattern=r"^(low|medium|high|urgent)$")
    due_date: dt_date | None = None
    due_time: dt_time | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = None


class TaskUpdate(BaseModel):
    """Schema for partially updating a task."""
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = Field(default=None, pattern=r"^(inbox|planned|in_progress|completed|cancelled)$")
    priority: str | None = Field(default=None, pattern=r"^(low|medium|high|urgent)$")
    due_date: dt_date | None = None
    due_time: dt_time | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)
    category: str | None = Field(default=None, max_length=100)
    is_important: bool | None = None
    comment: str | None = None


class TaskResponse(BaseModel):
    """Schema for task in API response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    status: str
    priority: str
    due_date: dt_date | None = None
    due_time: dt_time | None = None
    estimated_minutes: int | None = None
    category: str | None = None
    is_important: bool = False
    source: str = "manual"
    parent_task_id: int | None = None
    completed_at: dt_datetime | None = None
    comment: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: dt_datetime
    updated_at: dt_datetime


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""
    tasks: list[TaskResponse]
    total: int
    page: int
    pages: int


# ── Habit schemas ───────────────────────────────────────────────────────────

class HabitCreate(BaseModel):
    """Schema for creating a new habit."""
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    frequency: str = Field(default="daily", pattern=r"^(daily|weekdays|specific_days|times_per_week|custom)$")
    days_of_week: str | None = None
    times_per_week: int | None = Field(default=None, ge=1, le=7)
    reminder_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class HabitResponse(BaseModel):
    """Schema for habit in API response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    frequency: str
    days_of_week: str | None = None
    times_per_week: int | None = None
    reminder_time: str | None = None
    current_streak: int = 0
    best_streak: int = 0
    total_completions: int = 0
    start_date: dt_date
    is_active: bool = True
    is_paused: bool = False
    completed_today: bool = False
    created_at: dt_datetime
    updated_at: dt_datetime


class HabitCompleteRequest(BaseModel):
    """Schema for marking a habit complete."""
    date: dt_date | None = None


# ── Stats schema ────────────────────────────────────────────────────────────

class FocusStatsResponse(BaseModel):
    """Focus session statistics."""
    sessions_count: int = 0
    total_minutes: int = 0


class StatsResponse(BaseModel):
    """Overall user statistics."""
    tasks_total: int = 0
    tasks_active: int = 0
    tasks_completed: int = 0
    tasks_completed_today: int = 0
    tasks_overdue: int = 0
    habits_total: int = 0
    habits_completed_today: int = 0
    habits_week_completions: int = 0
    focus_minutes_today: int = 0
    focus_week: FocusStatsResponse = Field(default_factory=FocusStatsResponse)
    subscription_tier: str = "free"


# ── Today schema ────────────────────────────────────────────────────────────

class TodayResponse(BaseModel):
    """Today's overview plan."""
    date: dt_date
    tasks: list[TaskResponse] = Field(default_factory=list)
    overdue_tasks: list[TaskResponse] = Field(default_factory=list)
    habits: list[HabitResponse] = Field(default_factory=list)
    focus_minutes_today: int = 0
    completed_today: int = 0
    total_today: int = 0


# ── AI schemas ──────────────────────────────────────────────────────────────

class AIAnalyzeRequest(BaseModel):
    """Request for AI text analysis."""
    text: str = Field(..., min_length=1, max_length=5000)
    mode: str | None = Field(default=None, pattern=r"^(task|plan|general)$")


class AIAnalyzeResponse(BaseModel):
    """Response from AI analysis."""
    result: str


# ── Settings schemas ────────────────────────────────────────────────────────

class SettingsResponse(BaseModel):
    """User settings response."""
    model_config = ConfigDict(from_attributes=True)

    timezone: str
    language: str
    morning_digest_enabled: bool = True
    morning_digest_time: str = "08:00"
    evening_digest_enabled: bool = True
    evening_digest_time: str = "21:00"
    notifications_paused: bool = False
    working_hours_start: str = "09:00"
    working_hours_end: str = "18:00"


class SettingsUpdate(BaseModel):
    """Partial settings update."""
    timezone: str | None = None
    language: str | None = None
    morning_digest_enabled: bool | None = None
    morning_digest_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    evening_digest_enabled: bool | None = None
    evening_digest_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    notifications_paused: bool | None = None
    working_hours_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    working_hours_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


# ── User schema ─────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Current user info."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    language: str = "ru"
    timezone: str = "Europe/Moscow"
    role: str | None = None
    goal_30_days: str | None = None
    onboarding_completed: bool = False
    is_active: bool = True
    last_active_at: dt_datetime | None = None
    subscription_tier: str = "free"
    created_at: dt_datetime
    updated_at: dt_datetime


# ── Health schema ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    database: str = "unknown"
    redis: str = "unknown"
