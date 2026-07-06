"""ИИ-ассистент на базе Anthropic Claude: генерация описаний объектов.

Совместимо с anthropic 0.28: используется базовый вызов messages.create без
параметров thinking/output_config. При недоступности ИИ возвращается
шаблонное описание, чтобы сценарий не прерывался.
"""
from __future__ import annotations

import logging

from bot.config import get_settings

logger = logging.getLogger(__name__)

_KIND_LABELS = {
    "apartment": "квартиру",
    "house": "дом",
    "land": "участок",
    "commercial": "коммерческое помещение",
}
_DEAL_LABELS = {"rent": "аренду", "sale": "продажу"}


class AIService:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.ai_model
        self._client = None
        try:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        except Exception:  # noqa: BLE001 - библиотека может быть недоступна
            logger.warning("Anthropic SDK недоступен, используются шаблонные описания")

    async def generate_description(self, data: dict) -> str:
        """Сгенерировать привлекательное описание объекта на русском."""
        prompt = self._build_prompt(data)
        if self._client is None:
            return self._fallback(data)
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=400,
                system=(
                    "Ты — риелтор. Составь короткое привлекательное описание объекта "
                    "недвижимости на русском языке (2-4 предложения), без выдуманных фактов. "
                    "Пиши по данным, что дал пользователь."
                ),
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(getattr(b, "text", "") for b in response.content).strip()
            return text or self._fallback(data)
        except Exception:  # noqa: BLE001 - сеть/лимиты/ключ
            logger.exception("Ошибка генерации описания через Anthropic")
            return self._fallback(data)

    @staticmethod
    def _build_prompt(data: dict) -> str:
        parts = []
        for key, label in (
            ("property_kind", "Тип"),
            ("deal_type", "Сделка"),
            ("district", "Район"),
            ("address", "Адрес"),
            ("rooms", "Комнат"),
            ("area", "Площадь, м²"),
            ("floor", "Этаж"),
            ("floors", "Этажность"),
            ("renovation", "Ремонт"),
            ("price", "Цена"),
        ):
            value = data.get(key)
            if value not in (None, ""):
                parts.append(f"{label}: {value}")
        extras = [
            name
            for name, present in (
                ("мебель", data.get("furniture")),
                ("техника", data.get("appliances")),
                ("газ", data.get("gas")),
                ("вода", data.get("water")),
                ("электричество", data.get("electricity")),
                ("интернет", data.get("internet")),
            )
            if present
        ]
        if extras:
            parts.append("Есть: " + ", ".join(extras))
        return "\n".join(parts)

    @staticmethod
    def _fallback(data: dict) -> str:
        kind = _KIND_LABELS.get(data.get("property_kind", ""), "объект")
        deal = _DEAL_LABELS.get(data.get("deal_type", ""), "")
        district = data.get("district")
        rooms = data.get("rooms")
        area = data.get("area")
        bits = [f"Сдаётся/продаётся {kind}".replace("Сдаётся/продаётся", "Предлагаем")]
        detail = []
        if rooms:
            detail.append(f"{rooms}-комн.")
        if area:
            detail.append(f"{area:g} м²")
        if district:
            detail.append(f"район {district}")
        line = f"{kind.capitalize()}"
        if detail:
            line += ", " + ", ".join(detail)
        if deal:
            line += f", на {deal}"
        return line + ". Подробности — у риелтора."


_service: AIService | None = None


def get_ai_service() -> AIService:
    global _service
    if _service is None:
        _service = AIService()
    return _service
