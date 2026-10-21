"""Pydantic schemas for AI structured responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AITaskParseSchema(BaseModel):
    """Schema for structured task extracted from natural language text."""

    title: str = Field(description="Краткое и понятное название задачи")
    due_date: str | None = Field(default=None, description="Дата дедлайна в формате YYYY-MM-DD или null")
    due_time: str | None = Field(default=None, description="Время дедлайна в формате HH:MM или null")
    priority: Literal["low", "medium", "high", "urgent"] = Field(default="medium", description="Приоритет задачи")
    estimated_minutes: int | None = Field(default=30, description="Оценка времени в минутах (целое число)")
    category: str | None = Field(default="Общее", description="Категория задачи (Работа, Личное, Покупки и т.д.)")
    subtasks: list[str] = Field(default_factory=list, description="Список подзадач")


class AIDecomposeItemSchema(BaseModel):
    """Single stage/subtask in task decomposition."""

    title: str = Field(description="Название этапа или подзадачи")
    estimated_minutes: int | None = Field(default=None, description="Оценка времени на этап в минутах")
    subtasks: list[str] = Field(default_factory=list, description="Шаги выполнения этапа")


class AIDecomposeSchema(BaseModel):
    """Decomposition of a complex goal or task."""

    task: str = Field(description="Исходная задача")
    stages: list[AIDecomposeItemSchema] = Field(default_factory=list, description="Этапы выполнения")


class AIDayPlanItemSchema(BaseModel):
    """Single item in daily plan schedule."""

    time_slot: str = Field(description="Временной слот (например, '09:00 - 10:30')")
    activity: str = Field(description="Описание активности")
    is_focus: bool = Field(default=False, description="Является ли глубокой фокус-сессией")


class AIDayPlanSchema(BaseModel):
    """Structured daily plan."""

    main_focus: str = Field(description="Главный фокус дня")
    schedule: list[AIDayPlanItemSchema] = Field(default_factory=list, description="Расписание по слотам")
    balance_summary: str | None = Field(default=None, description="Итоговый баланс времени и отдыха")
