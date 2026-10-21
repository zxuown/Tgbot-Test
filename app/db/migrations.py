"""Programmatic Alembic migrations runner."""

from __future__ import annotations

import concurrent.futures
import logging
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.core.config import get_settings

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _run_upgrade(ini_path: Path, alembic_dir: Path, database_url: str) -> None:
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")


def run_migrations() -> bool:
    """
    Run Alembic migrations programmatically up to 'head'.

    Uses a dedicated worker thread to avoid conflicts with running asyncio loops.
    """
    settings = get_settings()
    ini_path = BASE_DIR / "alembic.ini"
    alembic_dir = BASE_DIR / "alembic"

    if not ini_path.exists() or not alembic_dir.exists():
        logger.warning("Alembic configuration not found at %s. Skipping auto-migrations.", ini_path)
        return False

    try:
        logger.info("Checking and applying database migrations (alembic upgrade head)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_run_upgrade, ini_path, alembic_dir, settings.DATABASE_URL).result()
        logger.info("Database migrations successfully applied.")
        return True
    except Exception as exc:
        logger.error("Failed to run database migrations: %s", exc)
        if settings.is_production:
            raise
        return False
