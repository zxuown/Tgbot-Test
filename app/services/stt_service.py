"""Speech-to-Text (STT) service with Mock and OpenAI Whisper providers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BaseSTTProvider(ABC):
    """Abstract interface for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(self, file_path: str) -> str:
        """Transcribe audio file to text."""
        pass


class MockSTTProvider(BaseSTTProvider):
    """Mock STT Provider for local offline development.

    Returns realistic Russian task requests.
    """

    async def transcribe(self, file_path: str) -> str:
        # Check if file exists (if provided)
        p = Path(file_path)
        if not p.exists() and file_path != "mock.ogg":
            logger.warning("MockSTTProvider: file %s does not exist on disk, returning sample text", file_path)

        # Plausible voice transcription for demo scenario
        return "Подготовить презентацию для клиента к пятнице, выделить 2 часа"


class OpenAISTTProvider(BaseSTTProvider):
    """OpenAI Whisper STT Provider using Whisper-1 endpoint."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def transcribe(self, file_path: str) -> str:
        url = f"{self.base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                with open(path, "rb") as f:
                    files = {"file": (path.name, f, "audio/ogg")}
                    data = {"model": "whisper-1", "language": "ru"}
                    response = await client.post(url, headers=headers, files=files, data=data)
                    response.raise_for_status()
                    result = response.json()
                    return str(result.get("text", "")).strip()
            except Exception as exc:
                logger.error("OpenAISTTProvider transcription error: %s", type(exc).__name__)
                raise


class STTService:
    """High-level STT Service."""

    def __init__(self, provider: BaseSTTProvider | None = None) -> None:
        settings = get_settings()
        if provider:
            self.provider = provider
        elif settings.STT_PROVIDER == "openai" and settings.STT_API_KEY:
            self.provider = OpenAISTTProvider(
                api_key=settings.STT_API_KEY,
                base_url=settings.STT_API_BASE_URL or "https://api.openai.com/v1",
            )
        else:
            self.provider = MockSTTProvider()

    async def transcribe(self, file_path: str) -> str:
        """Transcribe audio file to text."""
        return await self.provider.transcribe(file_path)
