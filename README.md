# 🎯 Фокус — Персональный AI-органайзер и коуч продуктивности

Production-ready Telegram-бот «Фокус» для фрилансеров, небольших команд, студентов и предпринимателей. Помогает превращать хаотичные сообщения, голосовые заметки и идеи в структурированные задачи, планировать день, отслеживать привычки, проводить вечерний анализ продуктивности и получать персональные рекомендации от AI.

---

## 🛠 Технологический стек

- **Python 3.12+**
- **aiogram 3.x** — асинхронный фреймворк для Telegram Bot API (поддержка Polling и Webhook)
- **FastAPI** — backend для REST API и Telegram Mini App
- **SQLAlchemy 2.x (async)** + **asyncpg** / **aiosqlite** — ORM для работы с PostgreSQL и SQLite
- **Alembic** — автоматические миграции базы данных перед стартом
- **Redis (aioredis)** + **MemoryStorage** (автоматический fallback для FSM)
- **APScheduler** — фоновые периодические уведомления (утренний и вечерний дайджесты, таймеры фокуса)
- **Google Gemini API** (`gemini-flash-lite-latest`, автоматический model fallback) + **Mock AI Provider**
- **httpx** — асинхронные HTTP-запросы
- **Pydantic Settings v2** — типизированная валидация конфигурации с разделением dev/prod
- **pytest** + **pytest-asyncio** — автоматизированное тестирование (75 тестов)
- **Ruff** — линтинг и форматирование кода
- **Docker** & **Docker Compose** — мультистейдж production-образ и локальный стек

---

## 🚀 Быстрый старт (Локально)

### 1. Активация окружения

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 2. Настройка переменных окружения

Скопируйте пример конфигурации:
```powershell
Copy-Item .env.example .env
```

Откройте `.env` и укажите:
1. `BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather).
2. Выберите AI-провайдер:
   - **Mock-режим** (по умолчанию, не требует ключей и интернета):
     ```env
     AI_PROVIDER=mock
     ```
   - **Реальный Google Gemini API**:
     ```env
     AI_PROVIDER=gemini
     GEMINI_API_KEY=ваш_ключ_от_Google_AI_Studio
     GEMINI_MODEL=gemini-flash-lite-latest
     ```

### 3. Запуск Telegram-бота

```powershell
.venv\Scripts\python -m app.main
```

### 4. Запуск FastAPI & Mini App (при необходимости отдельного процесса)

```powershell
.venv\Scripts\uvicorn app.api.app:create_app --factory --reload --port 8000
```
- Документация Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Mini App: [http://127.0.0.1:8000/app/](http://127.0.0.1:8000/app/)
- Healthcheck: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## ☁️ Развертывание в облаке (Production Deployment)

Проект полностью подготовлен для развертывания на облачных платформах (**Render**, **Railway**, **Fly.io**, **VPS/Docker**).

### Режимы работы (`BOT_MODE`)

| Значение `BOT_MODE` | Описание | Для каких платформ |
|---------------------|----------|-------------------|
| `polling` *(default)* | Бот опрашивает Telegram через Polling. Если задан `$PORT`, одновременно запускается FastAPI для прохождения облачного Healthcheck (`GET /health`). | **Render Web Service**, **Railway Web Service**, локально |
| `webhook` | Входящие апдейты Telegram обрабатываются через FastAPI endpoint `POST {WEBHOOK_PATH}`. Требуется публичный HTTPS URL в `WEBHOOK_URL`. | **Render Web Service**, **Railway**, собственный VPS с доменом |
| `worker` | Чистый фоновый worker (только polling + APScheduler, без HTTP-сервера). | **Render Background Worker**, **Railway Worker** |
| `api` | Запуск только REST API и MiniApp через Uvicorn (без Telegram-бота). | Выделенный API сервис в микросервисной архитектуре |

---

### Вариант 1. Развертывание на Render (Render Blueprint)

Проект включает готовый файл конфигурации [`render.yaml`](render.yaml).

1. Создайте репозиторий на GitHub и отправьте в него код проекта.
2. Войдите в панель [Render.com](https://render.com) и перейдите в **Blueprints** → **New Blueprint Instance**.
3. Подключите ваш репозиторий. Render автоматически обнаружит `render.yaml` и создаст:
   - Базу данных **PostgreSQL** (`focus-db`).
   - Web-сервис **focus-bot-app** на базе универсального `Dockerfile`.
4. В настройках сервиса задайте секретные переменные:
   - `BOT_TOKEN`: ваш токен от BotFather.
   - `GEMINI_API_KEY`: ваш ключ Google AI Studio.
5. Нажмите **Apply**. Render выполнит:
   - Сборку мультистейдж Dockerfile.
   - Автоматический прогон миграций `alembic upgrade head`.
   - Запуск приложения со встроенным Healthcheck на `/health`.

---

### Вариант 2. Развертывание на Railway

Проект включает готовый файл конфигурации [`railway.toml`](railway.toml).

1. Создайте проект в [Railway.app](https://railway.app).
2. Добавьте плагины **PostgreSQL** и **Redis** (New → Database → PostgreSQL / Redis).
3. Добавьте сервис из вашего GitHub-репозитория.
4. В разделе **Variables** задайте:
   ```env
   APP_ENV=production
   BOT_MODE=polling
   AUTO_MIGRATE=true
   BOT_TOKEN=8665814809:...
   AI_PROVIDER=gemini
   GEMINI_API_KEY=AIzaSy...
   SECRET_KEY=сгенерируйте_случайный_ключ_32_символа
   ```
   *(Переменные `DATABASE_URL` и `PORT` Railway подставит автоматически).*
5. Railway автоматически соберет Docker-образ, запустит миграции и поднимет сервис с проверкой здоровья `/health`.

---

### Вариант 3. Запуск через Docker Compose (Local / VPS)

Для изолированного запуска приложения со всеми зависимостями (PostgreSQL 16, Redis 7, API и Bot worker):

```bash
# 1. Запустить все сервисы в фоне
docker compose up --build -d

# 2. Просмотреть логи
docker compose logs -f

# 3. Остановить контейнеры
docker compose down
```

---

## 🔒 Безопасность и Production-контроль

- **Строгая валидация конфигурации:** в режиме `APP_ENV=production` бот не запустится с небезопасным `SECRET_KEY`, локальным SQLite или отсутствующим `GEMINI_API_KEY`.
- **Никаких секретов в коде и репозитории:** все токены передаются исключительно через переменные окружения, `.env` добавлен в `.gitignore`.
- **Автоматический Model Fallback:** если указанная Gemini-модель временно перегружена (503) или недоступна, бот автоматически переключается на рабочие резервные модели (`gemini-flash-lite-latest`, `gemini-3.5-flash-lite`), не обрывая диалог.
- **Graceful Shutdown:** контейнер перехватывает сигналы `SIGTERM` и `SIGINT`, корректно завершает работу APScheduler, закрывает сессии бота и пул соединений PostgreSQL.
- **Непривилегированный пользователь:** внутри контейнера приложение выполняется от пользователя `appuser` (non-root, UID 1000).

---

## 🧪 Запуск тестов и линтера

```powershell
# Запуск полного набора unit & integration тестов (75 тестов)
.venv\Scripts\pytest

# Проверка линтером Ruff
.venv\Scripts\ruff check app tests
```

---

## 📋 Таблица переменных окружения

| Переменная | Обязательна в Prod | По умолчанию | Описание |
|---|:---:|:---:|---|
| `BOT_TOKEN` | **Да** | — | Токен Telegram-бота от @BotFather |
| `DATABASE_URL` | **Да** | — | URL подключения к PostgreSQL (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | **Да** | — | Ключ для подписи сессий (минимум 16 символов) |
| `APP_ENV` | Нет | `development` | Окружение: `development` или `production` |
| `BOT_MODE` | Нет | `polling` | Режим: `polling`, `webhook`, `worker`, `api` |
| `AUTO_MIGRATE` | Нет | `true` | Автозапуск `alembic upgrade head` перед стартом |
| `REDIS_URL` | Нет | `redis://localhost:6379/0` | URL Redis для FSM (fallback на MemoryStorage) |
| `AI_PROVIDER` | Нет | `mock` | `mock`, `gemini`, `openai` |
| `GEMINI_API_KEY` | Если AI=gemini | — | API-ключ Google AI Studio |
| `GEMINI_MODEL` | Нет | `gemini-flash-lite-latest` | Модель Gemini |
| `WEBHOOK_URL` | Если MODE=webhook | — | Публичный HTTPS URL (для webhook-режима) |
| `WEBHOOK_SECRET` | Нет | `changeme` | Секретный заголовок валидации вебхука |
| `LOG_LEVEL` | Нет | `INFO` | Уровень логов: DEBUG, INFO, WARNING, ERROR |
| `LOG_FORMAT` | Нет | `auto` | `auto` (json в prod, console в dev), `json`, `console` |
| `PORT` | Нет | `8000` | HTTP-порт для веб-сервера / healthcheck |
