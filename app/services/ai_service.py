"""AI Service with Provider abstraction, Mock Provider, Gemini Provider, and OpenAI Provider."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import ConfigurationError, get_settings
from app.services.ai_schemas import AITaskParseSchema
from app.utils.helpers import clean_telegram_html, parse_date_ru, parse_time, parse_time_input

logger = logging.getLogger(__name__)


class AIError(Exception):
    """Base exception for AI operations."""
    pass


class AIQuotaError(AIError):
    """Rate limit or quota exhausted."""
    pass


class AITimeoutError(AIError):
    """Request timeout."""
    pass


class AINetworkError(AIError):
    """Network connection failure."""
    pass


class AIProviderError(AIError):
    """General provider-level error."""
    pass


class BaseAIProvider(ABC):
    """Abstract interface for AI providers."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_format: str = "text",
    ) -> str:
        """Generate text or JSON completion from prompt and message."""
        pass


class MockAIProvider(BaseAIProvider):
    """Mock AI Provider that returns realistic, structured Russian responses.

    Works completely offline without external APIs or keys.
    """

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_format: str = "text",
    ) -> str:
        sys_lower = system_prompt.lower()

        if "парс" in sys_lower or "parse_task" in sys_lower:
            return self._mock_parse_task(user_message)
        if "мысл" in sys_lower or "analyze_thought" in sys_lower:
            return self._mock_analyze_thought(user_message)
        if "план" in sys_lower or "plan_day" in sys_lower:
            return self._mock_plan_day(user_message)
        if "декомпозиц" in sys_lower or "decompose" in sys_lower:
            return self._mock_decompose(user_message)
        if "коуч" in sys_lower or "coach" in sys_lower:
            return self._mock_coaching(user_message)
        if "обзор" in sys_lower or "недел" in sys_lower or "weekly_review" in sys_lower:
            return self._mock_weekly_review(user_message)

        # Default fallback response
        return (
            "🤖 <b>AI-анализ:</b>\n\n"
            f"Запрос обработан успешно. Получено {len(user_message)} символов.\n"
            "Все ключевые действия зафиксированы."
        )

    def _mock_parse_task(self, text: str) -> str:
        parsed_date = parse_date_ru(text)
        parsed_time_val = parse_time_input(text) or parse_time(text)

        # Priority detection
        priority = "medium"
        lower = text.lower()
        if "срочн" in lower or "важн" in lower or "критич" in lower or "высокий" in lower:
            priority = "high"
        elif "низк" in lower or "не к спеху" in lower or "когда-нибудь" in lower:
            priority = "low"

        # Estimated minutes detection
        estimated = 30
        if "2 часа" in lower or "2 ч" in lower or "120 мин" in lower:
            estimated = 120
        elif "1 час" in lower or "час" in lower or "60 мин" in lower:
            estimated = 60
        elif "15 мин" in lower:
            estimated = 15
        elif "45 мин" in lower:
            estimated = 45

        # Category
        category = "Личное"
        if any(w in lower for w in ["клиент", "проект", "презентаци", "отчет", "договор", "сайт", "код", "работа"]):
            category = "Работа"
        elif any(w in lower for w in ["билет", "купить", "магазин", "оплат"]):
            category = "Покупки"
        elif any(w in lower for w in ["врач", "спорт", "тренировк", "здоровь"]):
            category = "Здоровье"

        title = text.strip()

        data = {
            "title": title,
            "due_date": parsed_date.isoformat() if parsed_date else None,
            "due_time": parsed_time_val.strftime("%H:%M") if parsed_time_val else None,
            "priority": priority,
            "estimated_minutes": estimated,
            "category": category,
            "subtasks": [
                f"Собрать исходные данные для: {title[:40]}",
                "Выполнить основную часть",
                "Проверить результат и подвести итог",
            ],
        }
        return json.dumps(data, ensure_ascii=False)

    def _mock_analyze_thought(self, text: str) -> str:
        return (
            "🧠 <b>AI-разбор вашей мысли:</b>\n\n"
            "📌 <b>Выделенные задачи:</b>\n"
            f"1. <b>Основное направление:</b> {text[:60]}... (Приоритет: Высокий)\n"
            "2. <b>Подготовка и согласование:</b> уточнить ключевые требования\n"
            "3. <b>Контроль дедлайна:</b> зафиксировать срок выполнения\n\n"
            "❓ <b>Вопросы для уточнения:</b>\n"
            "• Есть ли жёсткий дедлайн?\n"
            "• Кто ещё участвует в этой задаче?\n\n"
            "💡 <b>Рекомендованный план:</b> разбить задачу на 2 фокус-сессии по 45 минут."
        )

    def _mock_plan_day(self, text: str) -> str:
        return (
            "📅 <b>Персональный план на день:</b>\n\n"
            "🎯 <b>Главный фокус:</b>\n"
            "Закрыть ключевой проект и сохранить баланс энергии.\n\n"
            "⏰ <b>Расписание:</b>\n"
            "• <b>09:00 - 10:30</b> — 🎯 Фокус-сессия 1: главная задача\n"
            "• <b>10:30 - 10:45</b> — Короткий перерыв (разминка, вода)\n"
            "• <b>10:45 - 12:00</b> — 🎯 Фокус-сессия 2: коммуникации и правки\n"
            "• <b>12:00 - 13:00</b> — Обед и прогулка\n"
            "• <b>13:00 - 14:30</b> — Текущие дела и мелкие задачи\n"
            "• <b>18:00</b> — 🔄 Привычка: спорт / чтение\n\n"
            "📊 <b>Баланс:</b> Запланировано 4 ч работы, свободное окно: 2 ч."
        )

    def _mock_decompose(self, text: str) -> str:
        return (
            f"🌳 <b>Декомпозиция задачи «{text[:50]}»:</b>\n\n"
            "1. <b>Этап 1: Подготовка (30 мин)</b>\n"
            "   ├── Собрать необходимые материалы и ссылки\n"
            "   └── Определить критерии готовности\n\n"
            "2. <b>Этап 2: Реализация (1 ч 30 мин)</b>\n"
            "   ├── Выполнить черновой вариант / основу\n"
            "   └── Внести доработки и отполировать детали\n\n"
            "3. <b>Этап 3: Финализация (20 мин)</b>\n"
            "   └── Проверить чек-лист и отправить / сохранить"
        )

    def _mock_coaching(self, question: str) -> str:
        return (
            f"💡 <b>Коучинг продуктивности:</b>\n\n"
            f"По поводу вопроса: <i>«{question[:80]}»</i>\n\n"
            "1. <b>Почему это происходит:</b>\n"
            "Часто сопротивление связано с неопределенностью первого шага "
            "или завышенными ожиданиями к идеальному результату.\n\n"
            "2. <b>Что сделать прямо сейчас:</b>\n"
            "• Уменьши первый шаг до абсурдно простого (на 2 минуты).\n"
            "• Поставь таймер на 15 минут без обязательства доделать всё.\n"
            "• Убери телефон из зоны видимости.\n\n"
            "💪 <i>Сделай только один маленький шаг сегодня. Импульс появится в процессе!</i>"
        )

    def _mock_weekly_review(self, stats_text: str) -> str:
        return (
            "📊 <b>AI-обзор продуктивности за неделю:</b>\n\n"
            "🏆 <b>Главные достижения:</b>\n"
            "• Высокая стабильность в выполнении утренних задач.\n"
            "• Успешное удержание серии ключевых привычек.\n\n"
            "⚠️ <b>Узкие места:</b>\n"
            "• Накопление задач в статусе «Inbox» к концу недели.\n"
            "• Перенос вечерних задач на следующий день.\n\n"
            "🎯 <b>Рекомендации на следующую неделю:</b>\n"
            "1. Начинать день с одной 25-минутной фокус-сессии без уведомлений.\n"
            "2. Проводить вечерний клиринг входящих за 10 минут до завершения дня."
        )


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider using HTTP requests via httpx with model fallback."""

    FALLBACK_MODELS = ("gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest")

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-flash-lite-latest",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model.strip() if model else "gemini-flash-lite-latest"
        self.timeout = timeout
        self._masked_key = (self.api_key[:4] + "..." + self.api_key[-4:]) if len(self.api_key) > 8 else "***"

    def __repr__(self) -> str:
        return f"GeminiProvider(model={self.model!r}, api_key={self._masked_key!r})"

    async def _call_api(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        response_format: str,
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        generation_config: dict[str, Any] = {
            "temperature": 0.2 if response_format == "json" else 0.7,
            "maxOutputTokens": 2048,
        }
        if response_format == "json":
            generation_config["responseMimeType"] = "application/json"

        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message}],
                }
            ],
            "generationConfig": generation_config,
        }

        if system_prompt:
            payload["system_instruction"] = {
                "parts": [{"text": system_prompt}]
            }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise AIProviderError("Gemini API не вернул вариантов ответа.")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        if not parts:
            raise AIProviderError("Gemini API вернул пустой текст ответа.")

        text_res = parts[0].get("text", "")
        return text_res.strip()

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_format: str = "text",
    ) -> str:
        """Call Google Gemini v1beta generateContent endpoint with automatic model fallback."""
        models_to_try = [self.model]
        for fallback in self.FALLBACK_MODELS:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_error: Exception | None = None
        for model in models_to_try:
            try:
                result = await self._call_api(model, system_prompt, user_message, response_format)
                if model != self.model:
                    logger.info("Successfully used fallback Gemini model: %s (switched from %s)", model, self.model)
                    self.model = model  # Switch active model to working fallback for future calls
                return result
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                safe_err_text = exc.response.text[:200]
                logger.error("GeminiProvider HTTP error model=%s status=%d: %s", model, status, safe_err_text)
                if status == 403:
                    raise AIProviderError("Ошибка авторизации Gemini API: неверный ключ или доступ запрещен.") from exc
                if status == 429:
                    last_error = AIQuotaError("Превышен лимит запросов к Gemini API (429 Rate Limit). Попробуйте позже.")
                elif status == 404:
                    logger.warning("Gemini model '%s' not found or unsupported (404), trying fallback...", model)
                    last_error = AIProviderError(f"Модель Gemini '{model}' недоступна (404).")
                elif status >= 500:
                    logger.warning("Gemini model '%s' unavailable (%d), trying fallback...", model, status)
                    last_error = AIProviderError(f"Сервер Google Gemini временно недоступен ({status}).")
                else:
                    last_error = AIProviderError(f"Ошибка Gemini API (HTTP {status})")
            except httpx.TimeoutException:
                logger.warning("Gemini model '%s' timed out after %.1fs, trying fallback...", model, self.timeout)
                last_error = AITimeoutError("Время ожидания ответа от Gemini API истекло.")
            except httpx.RequestError as exc:
                logger.error("GeminiProvider network error model=%s: %s", model, type(exc).__name__)
                last_error = AINetworkError(f"Сетевая ошибка при обращении к Gemini API: {type(exc).__name__}")

        if last_error:
            raise last_error
        raise AIProviderError("Все доступные модели Gemini вернули ошибку.")


class OpenAIProvider(BaseAIProvider):
    """OpenAI-compatible AI Provider using HTTP requests via httpx."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_format: str = "text",
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.2 if response_format == "json" else 0.7,
            "max_tokens": 1500,
        }
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return str(data["choices"][0]["message"]["content"]).strip()
            except Exception as exc:
                logger.error("OpenAIProvider request failed: %s (%s)", type(exc).__name__, str(exc)[:200])
                raise


class AIService:
    """High-level AI Service coordinating providers, prompts, and task generation."""

    def __init__(self, provider: BaseAIProvider | None = None) -> None:
        settings = get_settings()
        if provider:
            self.provider = provider
        elif settings.AI_PROVIDER == "gemini":
            if settings.GEMINI_API_KEY:
                logger.info("AIService using GeminiProvider with model %s", settings.GEMINI_MODEL)
                self.provider = GeminiProvider(
                    api_key=settings.GEMINI_API_KEY,
                    model=settings.GEMINI_MODEL,
                )
            else:
                if settings.is_production:
                    raise ConfigurationError(
                        "AI_PROVIDER='gemini', но GEMINI_API_KEY не задан! "
                        "В production-режиме использование Mock AI запрещено."
                    )
                logger.warning(
                    "AI_PROVIDER='gemini', but GEMINI_API_KEY is not set! Falling back to MockAIProvider in %s mode.",
                    settings.APP_ENV,
                )
                self.provider = MockAIProvider()
        elif settings.AI_PROVIDER == "openai":
            if settings.AI_API_KEY:
                logger.info("AIService using OpenAIProvider with model %s", settings.AI_MODEL)
                self.provider = OpenAIProvider(
                    api_key=settings.AI_API_KEY,
                    base_url=settings.AI_API_BASE_URL,
                    model=settings.AI_MODEL,
                )
            else:
                if settings.is_production:
                    raise ConfigurationError(
                        "AI_PROVIDER='openai', но AI_API_KEY не задан! "
                        "В production-режиме использование Mock AI запрещено."
                    )
                logger.warning(
                    "AI_PROVIDER='openai', but AI_API_KEY is not set! Falling back to MockAIProvider in %s mode.",
                    settings.APP_ENV,
                )
                self.provider = MockAIProvider()
        else:
            self.provider = MockAIProvider()

    def _truncate_input(self, text: str) -> str:
        """Limit user input length to prevent token overflow and prompt injection bloat."""
        settings = get_settings()
        limit = getattr(settings, "AI_MAX_INPUT_CHARS", 2000)
        if len(text) > limit:
            logger.info("Truncating AI input text from %d to %d characters.", len(text), limit)
            return text[:limit]
        return text

    def _strip_markdown_json(self, raw: str) -> str:
        """Strip markdown fences (```json ... ```) from model output."""
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    async def parse_task_from_text(self, text: str) -> dict[str, Any]:
        """Extract structured task fields from natural language text with validation and retry."""
        safe_text = self._truncate_input(text)
        system_prompt = (
            "Ты — парсер задач AI-органайзера 'Фокус'. Извлеки из текста параметры задачи "
            "и верни строгий JSON следующего формата:\n"
            "{\n"
            '  "title": "название задачи",\n'
            '  "due_date": "YYYY-MM-DD" или null,\n'
            '  "due_time": "HH:MM" или null,\n'
            '  "priority": "low" | "medium" | "high" | "urgent",\n'
            '  "estimated_minutes": целое число или null,\n'
            '  "category": "Работа" | "Личное" | "Покупки" | "Здоровье" | "Общее" или null,\n'
            '  "subtasks": ["подзадача 1", "подзадача 2"]\n'
            "}"
        )

        # Attempt 1: primary completion request
        try:
            raw_response = await self.provider.complete(system_prompt, safe_text, response_format="json")
            cleaned = self._strip_markdown_json(raw_response)
            parsed_model = AITaskParseSchema.model_validate_json(cleaned)
            return parsed_model.model_dump()
        except Exception as first_err:
            logger.warning("First attempt to parse task JSON failed: %s. Attempting repair retry...", first_err)

            # Attempt 2: retry with explicit schema correction
            try:
                repair_prompt = (
                    "Предыдущий ответ содержал ошибку форматирования или схемы. "
                    "Верни ИСКЛЮЧИТЕЛЬНО валидный JSON без markdown-тегов по схеме: "
                    '{"title": str, "due_date": "YYYY-MM-DD"|null, "due_time": "HH:MM"|null, '
                    '"priority": "low"|"medium"|"high"|"urgent", "estimated_minutes": int|null, '
                    '"category": str|null, "subtasks": list[str]}.'
                )
                raw_retry = await self.provider.complete(repair_prompt, safe_text, response_format="json")
                cleaned_retry = self._strip_markdown_json(raw_retry)
                parsed_model = AITaskParseSchema.model_validate_json(cleaned_retry)
                return parsed_model.model_dump()
            except Exception as retry_err:
                logger.error("AI task parsing retry failed (%s). Falling back to rule-based parser.", retry_err)

        # Graceful rule-based fallback: guarantees the bot never crashes
        parsed_date = parse_date_ru(safe_text)
        parsed_time_val = parse_time_input(safe_text) or parse_time(safe_text)
        return {
            "title": safe_text.strip(),
            "due_date": parsed_date.isoformat() if parsed_date else None,
            "due_time": parsed_time_val.strftime("%H:%M") if parsed_time_val else None,
            "priority": "medium",
            "estimated_minutes": 30,
            "category": "Общее",
            "subtasks": [],
        }

    async def analyze_thought(self, text: str) -> str:
        """Analyze chaotic thoughts and structure into tasks and actions."""
        safe_text = self._truncate_input(text)
        system_prompt = (
            "Ты — коуч продуктивности и организатор 'Фокус'. "
            "Разбери мысли пользователя, выдели конкретные задачи с приоритетами, "
            "сформулируй 1-2 вопроса для уточнения и дай рекомендацию по фокус-сессиям. "
            "Используй форматирование Telegram HTML (<b>, <i>, <code>). Не используй теги списков <li> или markdown заголовки."
        )
        try:
            raw = await self.provider.complete(system_prompt, safe_text)
            return clean_telegram_html(raw)
        except AIError as exc:
            logger.warning("AI analyze_thought failed: %s", exc)
            return f"⚠️ Не удалось выполнить AI-разбор: {exc}"

    async def plan_day(self, text: str) -> str:
        """Create a realistic daily plan."""
        safe_text = self._truncate_input(text)
        system_prompt = (
            "Ты — AI-планировщик продуктивности 'Фокус'. "
            "Составь реалистичный и сбалансированный план дня на основе задач пользователя. "
            "Выдели главный фокус дня, расписание по слотам и баланс работы/отдыха. "
            "Используй форматирование Telegram HTML (<b>, <i>). Не используй теги списков <li> или markdown заголовки."
        )
        try:
            raw = await self.provider.complete(system_prompt, safe_text)
            return clean_telegram_html(raw)
        except AIError as exc:
            logger.warning("AI plan_day failed: %s", exc)
            return f"⚠️ Не удалось составить AI-план: {exc}"

    async def decompose_task(self, title: str, description: str | None = None) -> str:
        """Decompose a complex task into a subtask tree."""
        msg = self._truncate_input(f"Задача: {title}\nОписание: {description or 'нет'}")
        system_prompt = (
            "Ты — эксперт по декомпозиции задач 'Фокус'. "
            "Разбей большую задачу на 3-4 последовательных логических этапа с оценкой времени и чек-листом. "
            "Используй форматирование Telegram HTML (<b>, <i>). Не используй теги списков <li> или markdown заголовки."
        )
        try:
            raw = await self.provider.complete(system_prompt, msg)
            return clean_telegram_html(raw)
        except AIError as exc:
            logger.warning("AI decompose_task failed: %s", exc)
            return f"⚠️ Не удалось выполнить декомпозицию: {exc}"

    async def coaching(self, question: str) -> str:
        """Provide short, actionable productivity coaching."""
        safe_question = self._truncate_input(question)
        system_prompt = (
            "Ты — персональный коуч продуктивности 'Фокус'. "
            "Дай краткий, ободряющий и практичный совет на вопрос пользователя. "
            "Объясни причину сопротивления/прокрастинации и назови 1 конкретный шаг на 2 минуты прямо сейчас. "
            "Используй форматирование Telegram HTML (<b>, <i>). Не используй теги списков <li> или markdown заголовки."
        )
        try:
            raw = await self.provider.complete(system_prompt, safe_question)
            return clean_telegram_html(raw)
        except AIError as exc:
            logger.warning("AI coaching failed: %s", exc)
            return f"⚠️ Не удалось получить совет: {exc}"

    async def weekly_review(self, stats_summary: str) -> str:
        """Generate weekly productivity review."""
        safe_stats = self._truncate_input(stats_summary)
        system_prompt = (
            "Ты — AI-аналитик продуктивности 'Фокус'. "
            "Проанализируй недельную статистику пользователя, выдели главные победы, "
            "узкие места и дай 2 конкретные рекомендации на следующую неделю. "
            "Используй форматирование Telegram HTML (<b>, <i>). Не используй теги списков <li> или markdown заголовки."
        )
        try:
            raw = await self.provider.complete(system_prompt, safe_stats)
            return clean_telegram_html(raw)
        except AIError as exc:
            logger.warning("AI weekly_review failed: %s", exc)
            return f"⚠️ Не удалось сформировать обзор недели: {exc}"
