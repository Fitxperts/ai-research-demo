"""ИИ-ассистент на базе Anthropic Claude.

Помогает клиенту сформулировать запрос на подбор недвижимости и отвечает
на вопросы. Также умеет извлекать структурированные критерии поиска из
свободного текста для последующего вызова :func:`crud.search_listings`.
"""
from __future__ import annotations

import json
import logging

from anthropic import APIError, AsyncAnthropic

from bot.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — вежливый ассистент риелтора в Telegram-боте. Помогаешь клиентам "
    "подобрать недвижимость: уточняешь тип сделки (продажа/аренда), тип объекта, "
    "район, бюджет и количество комнат. Отвечай кратко, по-русски, дружелюбно. "
    "Не выдумывай конкретные объявления — их подбирает система по критериям."
)

# JSON-схема критериев, которые ИИ извлекает из свободного текста запроса.
_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "deal_type": {"type": ["string", "null"], "enum": ["sale", "rent", None]},
        "property_type": {
            "type": ["string", "null"],
            "enum": ["apartment", "house", "room", "commercial", None],
        },
        "district": {"type": ["string", "null"]},
        "budget_min": {"type": ["number", "null"]},
        "budget_max": {"type": ["number", "null"]},
        "rooms": {"type": ["integer", "null"]},
    },
    "required": [
        "deal_type",
        "property_type",
        "district",
        "budget_min",
        "budget_max",
        "rooms",
    ],
    "additionalProperties": False,
}


class AIService:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.ai_model

    async def chat(self, message: str, history: list[dict] | None = None) -> str:
        """Ответить на реплику клиента в свободном диалоге."""
        messages = list(history or [])
        messages.append({"role": "user", "content": message})
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                thinking={"type": "adaptive"},
                messages=messages,
            ) as stream:
                response = await stream.get_final_message()
        except APIError:
            logger.exception("Ошибка обращения к Anthropic API")
            return "Извините, ассистент сейчас недоступен. Попробуйте позже."

        return "".join(block.text for block in response.content if block.type == "text").strip()

    async def extract_criteria(self, text: str) -> dict:
        """Извлечь структурированные критерии поиска из свободного текста."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=512,
                system=(
                    "Извлеки критерии поиска недвижимости из сообщения пользователя. "
                    "Если параметр не указан — верни null."
                ),
                messages=[{"role": "user", "content": text}],
                output_config={"format": {"type": "json_schema", "schema": _EXTRACT_SCHEMA}},
            )
        except APIError:
            logger.exception("Ошибка извлечения критериев через Anthropic API")
            return {}

        raw = next((b.text for b in response.content if b.type == "text"), "{}")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("ИИ вернул некорректный JSON: %s", raw)
            return {}
        return {k: v for k, v in data.items() if v is not None}


_service: AIService | None = None


def get_ai_service() -> AIService:
    global _service
    if _service is None:
        _service = AIService()
    return _service
