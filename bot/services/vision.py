"""Распознавание объявлений со скриншотов (Google Gemini Vision).

Риелторы часто получают объявления партнёров картинкой (скрин из чата/канала).
Vision извлекает из изображения ТЕКСТ объявления, который дальше разбирается тем
же parse_listing, что и обычный текст. Без ключа функция просто выключена
(is_enabled() == False) — бот работает как раньше.
"""
from __future__ import annotations

import base64
import logging

from bot.config import get_settings

logger = logging.getLogger(__name__)

_PROMPT = (
    "На изображении — объявление о недвижимости (скриншот из чата, канала или "
    "фото листовки). Извлеки ВЕСЬ относящийся к объявлению текст: тип сделки "
    "(аренда/продажа), цену, комнаты, район/массив, адрес или ориентир, площадь, "
    "этаж, телефон, описание. Верни просто связный текст объявления как есть, "
    "без своих комментариев. Если на картинке нет объявления о недвижимости — "
    "верни пустую строку."
)


class VisionService:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.vision_model
        # Ключ Gemini; если не задан, но основной LLM уже Gemini — переиспользуем его.
        key = settings.gemini_api_key
        base = settings.gemini_base_url
        if not key and "generativelanguage.googleapis.com" in settings.llm_base_url:
            key, base = settings.llm_api_key, settings.llm_base_url
        self._client = None
        if key:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=key, base_url=base)
                logger.info("Vision: Gemini, модель %s", self._model)
            except Exception:  # noqa: BLE001
                logger.warning("Vision SDK недоступен — распознавание скринов выключено")

    def is_enabled(self) -> bool:
        return self._client is not None

    async def extract_listing_text(self, image_bytes: bytes, mime: str = "image/jpeg") -> str | None:
        """Вернуть текст объявления с картинки или None (выключено/ошибка/пусто)."""
        if self._client is None:
            return None
        data_uri = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=800,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _PROMPT},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
            )
            text = (resp.choices[0].message.content or "").strip()
            return text or None
        except Exception:  # noqa: BLE001 - сеть/лимиты/битый ответ
            logger.exception("Ошибка Vision-распознавания")
            return None


_service: VisionService | None = None


def get_vision_service() -> VisionService:
    global _service
    if _service is None:
        _service = VisionService()
    return _service
