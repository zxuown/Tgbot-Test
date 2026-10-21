.PHONY: install dev bot api test lint format migrate migrate-create seed docker-up docker-down docker-logs

PYTHON ?= .venv/Scripts/python
PIP ?= .venv/Scripts/pip

install:
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]

dev:
	$(PYTHON) -m uvicorn app.api.app:app --reload --host 0.0.0.0 --port 8000

bot:
	$(PYTHON) -m app.main

api:
	$(PYTHON) -m uvicorn app.api.app:app --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check app tests

format:
	$(PYTHON) -m ruff format app tests

migrate:
	$(PYTHON) -m alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	$(PYTHON) -m alembic revision --autogenerate -m "$$msg"

seed:
	$(PYTHON) -m app.db.seed

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f
