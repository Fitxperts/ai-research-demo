"""Транскрипция голосовых сообщений (Groq Whisper).

Собственник может наговорить объявление голосом — в т.ч. на «ломаном» узбекском,
со сленгом и ошибками. Whisper-large-v3 хорошо тянет узбекский и смешанную
uz/ru речь; язык не фиксируем (автоопределение), чтобы принимать оба.
Без ключа функция выключена — бот работает как раньше.
"""
from __future__ import annotations

import logging

from bot.config import get_settings

logger = logging.getLogger(__name__)


class TranscribeService:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.whisper_model
        key = settings.groq_api_key
        # Если отдельный ключ Groq не задан, но основной LLM уже Groq — переиспользуем.
        base = settings.groq_base_url
        if not key and "api.groq.com" in settings.llm_base_url:
            key, base = settings.llm_api_key, settings.llm_base_url
        self._client = None
        if key:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=key, base_url=base)
                logger.info("Транскрипция: Groq Whisper, модель %s", self._model)
            except Exception:  # noqa: BLE001
                logger.warning("Whisper SDK недоступен — голосовой ввод выключен")

    def is_enabled(self) -> bool:
        return self._client is not None

    async def transcribe(self, audio_bytes: bytes, filename: str = "voice.ogg") -> str | None:
        """Расшифровать аудио в текст. None — если выключено/ошибка/пусто."""
        if self._client is None:
            return None
        try:
            resp = await self._client.audio.transcriptions.create(
                model=self._model,
                file=(filename, audio_bytes),
            )
            text = (getattr(resp, "text", "") or "").strip()
            return text or None
        except Exception:  # noqa: BLE001 - сеть/лимиты/формат
            logger.exception("Ошибка транскрипции голосового")
            return None


_service: TranscribeService | None = None


def get_transcribe_service() -> TranscribeService:
    global _service
    if _service is None:
        _service = TranscribeService()
    return _service
