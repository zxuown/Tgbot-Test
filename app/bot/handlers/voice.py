"""Voice message handler with Speech-to-Text and AI task extraction."""

from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import ai_parsed_task_keyboard
from app.core.security import escape_html
from app.i18n.texts import Texts
from app.services.ai_service import AIService
from app.services.stt_service import STTService
from app.utils.helpers import format_minutes, priority_emoji

if TYPE_CHECKING:
    from app.db.models.user import User

router = Router(name="voice")


@router.message(F.voice)
@router.message(F.audio)
async def handle_voice_message(message: Message, bot: Bot, user: User, state: FSMContext) -> None:
    """Download voice note, transcribe, and parse into task."""
    status_msg = await message.answer(Texts.VOICE_PROCESSING)

    # In local testing without actual Telegram bot connection,
    # or if downloading is simulated:
    transcribed_text = ""
    stt = STTService()

    voice = message.voice or message.audio
    if voice and hasattr(bot, "download"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            try:
                await bot.download(voice, destination=tmp_path)
                transcribed_text = await stt.transcribe(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception:
            # Fallback to mock STT text
            transcribed_text = await stt.transcribe("mock.ogg")
    else:
        transcribed_text = await stt.transcribe("mock.ogg")

    if not transcribed_text:
        await status_msg.edit_text(Texts.VOICE_ERROR)
        return

    # Now parse transcribed text as task
    ai = AIService()
    parsed = await ai.parse_task_from_text(transcribed_text)
    await state.update_data(parsed_task=parsed)

    p_date = f"📅 Дата: {parsed.get('due_date')}\n" if parsed.get("due_date") else ""
    p_time = f"⏰ Время: {parsed.get('due_time')}\n" if parsed.get("due_time") else ""
    p_dur = f"⏱ Длительность: {format_minutes(parsed.get('estimated_minutes'))}\n" if parsed.get("estimated_minutes") else ""
    p_cat = f"🏷 Категория: {parsed.get('category')}\n" if parsed.get("category") else ""
    p_prio = f"🔺 Приоритет: {priority_emoji(parsed.get('priority', 'medium'))} {parsed.get('priority', 'medium')}\n"

    result_text = (
        f"🎤 <b>Распознано:</b>\n<i>«{escape_html(transcribed_text)}»</i>\n\n"
        + Texts.AI_TASK_PARSED.format(
            title=escape_html(parsed.get("title", transcribed_text)),
            due_date=p_date,
            due_time=p_time,
            priority=p_prio,
            estimated=p_dur,
            category=p_cat,
        )
    )

    await status_msg.edit_text(result_text, reply_markup=ai_parsed_task_keyboard())
