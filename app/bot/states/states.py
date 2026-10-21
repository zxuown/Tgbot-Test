"""FSM states for all bot conversational scenarios."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """User onboarding survey."""
    name = State()
    timezone = State()
    role = State()
    goal_30_days = State()
    morning_time = State()
    evening_time = State()


class TaskCreationStates(StatesGroup):
    """Step-by-step task creation."""
    title = State()
    description = State()
    priority = State()
    due_date = State()
    due_time = State()
    estimated = State()
    category = State()
    confirm = State()


class HabitCreationStates(StatesGroup):
    """Habit creation flow."""
    title = State()
    frequency = State()
    days_of_week = State()
    reminder_time = State()
    confirm = State()


class AIStates(StatesGroup):
    """AI conversation states."""
    mode_selected = State()
    waiting_input = State()
    confirm_result = State()
    confirm_parsed_task = State()


class FocusStates(StatesGroup):
    """Focus timer states."""
    select_task = State()
    select_duration = State()
    active = State()


class AdminStates(StatesGroup):
    """Admin operations."""
    broadcast_message = State()
    search_user = State()
