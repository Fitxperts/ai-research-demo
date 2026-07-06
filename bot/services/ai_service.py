"""ИИ-сервис РиелторБота.

Три функции:
- generate_description(property_data) -> str  — готовое объявление (MarkdownV2,
  строгий формат с премиум-эмодзи), для публикации в канал;
- parse_free_text(text) -> dict               — разбор свободного текста
  собственника («2к чиланзар 450 хозяин») в структуру;
- find_matches(client, properties) -> list    — умный подбор объектов под
  клиента (бюджет ±10%, район, комнаты).

Дополнительно generate_short_description() — короткое описание для карточек.
Совместимо с anthropic 0.28 (базовый messages.create, без thinking/output_config).
"""
from __future__ import annotations

import json
import logging
import re

from bot.config import (
    AGENCY_CONTACTS,
    BOT_PUBLISH_URL,
    CHANNEL_URL,
    PREMIUM_EMOJI,
    get_settings,
)

logger = logging.getLogger(__name__)

# Узбекские подписи
_KIND_UZ = {
    "apartment": "КВАРТИРА",
    "house": "ҲОВЛИ",
    "land": "ЕР УЧАСТКА",
    "commercial": "ТИЖОРАТ ОБЪЕКТ",
}
_KIND_RU = {
    "apartment": "квартиру",
    "house": "дом",
    "land": "участок",
    "commercial": "коммерческое помещение",
}
_DEAL_RU = {"rent": "аренду", "sale": "продажу"}

_MD_SPECIALS = r"_*[]()~`>#+-=|{}.!\\"


def escape_md(text: str) -> str:
    """Экранировать спецсимволы MarkdownV2."""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))


def _fmt_price(value) -> str:
    try:
        return f"{int(float(value)):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


class AIService:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.ai_model
        self._client = None
        try:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        except Exception:  # noqa: BLE001 - библиотека недоступна
            logger.warning("Anthropic SDK недоступен, используются офлайн-режимы")

    # ------------------------------------------------------------------
    # 1. Готовое объявление (строгий формат, MarkdownV2)
    # ------------------------------------------------------------------
    def generate_description(self, property_data: dict) -> str:
        d = property_data
        e = PREMIUM_EMOJI
        deal = d.get("deal_type") or d.get("type")
        kind_uz = _KIND_UZ.get(d.get("property_kind"), "КВАРТИРА")
        title_deal = "ИЖАРАГА БЕРИЛАДИ" if deal == "rent" else "СОТИЛАДИ"
        tag_deal = "\\#Ижара" if deal == "rent" else "\\#Сотув"
        rooms = d.get("rooms")

        lines: list[str] = []
        lines.append(f"![🏢](tg://emoji?id={e['building']}) *{kind_uz} {title_deal}*")

        tags = f"{tag_deal} \\#Фарғона"
        if rooms:
            tags += f" \\#{rooms}\\_хона"
        if d.get("urgent"):
            tags += f" ![🚨](tg://emoji?id={e['siren']}) \\#Срочно"
        lines.append(tags)
        lines.append("")

        address = escape_md(d.get("address") or "—")
        lines.append(f"![📍](tg://emoji?id={e['pin']}) *Манзил:* {address}\\.")
        lines.append("")

        if rooms:
            floor, floors = d.get("floor"), d.get("floors")
            fl = f" \\({floor}/{floors} қават\\)" if floor and floors else ""
            lines.append(f"![🚪](tg://emoji?id={e['door']}) *Хоналар сони:* {rooms} хона{fl}\\.")

        reno = escape_md(d.get("renovation") or "Аъло даражада, тоза ва шинам")
        lines.append(f"![🛠](tg://emoji?id={e['tools']}) *Ҳолати:* {reno}\\.")

        comforts = self._comforts(d)
        lines.append(f"![⚡️](tg://emoji?id={e['lightning']}) *Қулайликлари:* {comforts}\\.")
        lines.append("")

        price = escape_md(_fmt_price(d.get("price")))
        neg = " \\(келишилади\\)" if d.get("negotiable") else ""
        lines.append(f"![💰](tg://emoji?id={e['money']}) *Нархи:* {price} сўм{neg}\\.")
        lines.append("_\\*Риэлторлик хизмати алоҳида\\._")
        lines.append("")

        lines.append(f"![📞](tg://emoji?id={e['phone']}) *Мурожаат учун \\(босиб кўринг\\):*")
        contacts = "\n".join(
            f"☎️ {escape_md(phone)} \\| @{escape_md(username)}"
            for phone, username in AGENCY_CONTACTS
        )
        lines.append(f"||{contacts}||")
        lines.append("")

        lines.append("➖➖➖➖➖➖➖➖➖➖")
        lines.append(f"[🏘 «Фарғона Уйлари» каналига қўшилиш]({CHANNEL_URL})")
        lines.append(f"[📥 Бепул эълон жойлаш]({BOT_PUBLISH_URL})")
        return "\n".join(lines)

    @staticmethod
    def _comforts(d: dict) -> str:
        present = [
            name
            for name, key in (("Газ", "gas"), ("сув", "water"), ("свет", "electricity"), ("интернет", "internet"))
            if d.get(key)
        ]
        if not present:
            return "маълумот сўраб олинг"
        if len(present) >= 3:
            return ", ".join(present[:-1]) + f" ва {present[-1]} узлуксиз"
        return " ва ".join(present) + " бор"

    # ------------------------------------------------------------------
    # 2. Разбор свободного текста собственника
    # ------------------------------------------------------------------
    async def parse_free_text(self, text: str) -> dict:
        if self._client is not None:
            parsed = await self._parse_with_ai(text)
            if parsed:
                return parsed
        return self._parse_regex(text)

    async def _parse_with_ai(self, text: str) -> dict:
        prompt = (
            "Разбери объявление о недвижимости в JSON с полями: deal_type "
            "(rent/sale), property_kind (apartment/house/land/commercial), rooms "
            "(int), district (str), price (число), phone (str). Отсутствующее — null. "
            "Верни только JSON.\n\nТекст: " + text
        )
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = "".join(getattr(b, "text", "") for b in response.content)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {k: v for k, v in data.items() if v is not None}
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка разбора текста через ИИ")
        return {}

    _STOPWORDS = {
        "аренд", "ижара", "сдам", "сдается", "сдаётся", "продаж", "сотув",
        "продам", "сотилади", "хозяин", "срочно", "комн", "хона", "сум", "сўм",
        "дом", "квартира", "участок",
    }
    _KIND_WORDS = (
        ("apartment", ("квартир", "кв", "хона")),
        ("house", ("дом", "ҳовли", "уй")),
        ("land", ("участок", "ер")),
        ("commercial", ("коммерч", "тижорат", "офис")),
    )

    @classmethod
    def _parse_regex(cls, text: str) -> dict:
        result: dict = {}

        # Телефон — извлекаем и убираем из текста, чтобы не спутать с ценой
        phone = re.search(r"\+?\d[\d\s\-()]{7,}\d", text)
        work = text
        if phone:
            result["phone"] = phone.group().strip()
            work = text.replace(phone.group(), " ")
        low = work.lower()

        # Тип сделки
        if any(w in low for w in ("аренд", "ижара", "сдам", "сдаётся", "сдается")):
            result["deal_type"] = "rent"
        elif any(w in low for w in ("продаж", "сотув", "продам", "сотилади")):
            result["deal_type"] = "sale"

        # Вид объекта
        for kind, words in cls._KIND_WORDS:
            if any(w in low for w in words):
                result["property_kind"] = kind
                break

        # Комнаты: "2к", "3 комн", "2-х"
        rooms = re.search(r"(\d+)\s*[-хx]?\s*(?:к|комн|хона)", low)
        if rooms:
            result["rooms"] = int(rooms.group(1))

        # Цена: наибольшее «нетелефонное» число
        numbers = [int(n) for n in re.findall(r"\d+", low) if len(n) <= 9]
        if numbers:
            result["price"] = float(max(numbers))

        # Район: первое подходящее кириллическое слово (не стоп-слово)
        for token in re.findall(r"[а-яёўқғҳ]{4,}", low):
            if token not in cls._STOPWORDS:
                result["district"] = token.capitalize()
                break

        return result

    # ------------------------------------------------------------------
    # 3. Умный подбор объектов под клиента
    # ------------------------------------------------------------------
    def find_matches(self, client: dict, properties: list) -> list:
        deal_map = {"rent": "rent", "buy": "sale"}
        want_type = deal_map.get(self._get(client, "deal_type"))
        budget = self._get(client, "budget")
        district = (self._get(client, "district") or "").lower()
        rooms = self._get(client, "rooms")

        scored: list[tuple[int, object]] = []
        for prop in properties:
            if want_type and self._get(prop, "type") not in (want_type, None):
                continue
            price = self._get(prop, "price")
            if budget and price and float(price) > float(budget) * 1.1:
                continue  # бюджет +10%

            score = 0
            p_district = (self._get(prop, "district") or "").lower()
            if district and district in p_district:
                score += 2
            if rooms and self._get(prop, "rooms") == rooms:
                score += 2
            if budget and price and float(price) <= float(budget):
                score += 1
            scored.append((score, prop))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [prop for _, prop in scored]

    @staticmethod
    def _get(obj, key):
        if isinstance(obj, dict):
            return obj.get(key)
        value = getattr(obj, key, None)
        # enum -> value
        return getattr(value, "value", value)

    # ------------------------------------------------------------------
    # Короткое описание (для карточек в боте)
    # ------------------------------------------------------------------
    async def generate_short_description(self, data: dict) -> str:
        if self._client is None:
            return self._short_fallback(data)
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=300,
                system=(
                    "Ты риелтор. Составь короткое привлекательное описание объекта "
                    "на русском (2-3 предложения) по данным, без выдумок."
                ),
                messages=[{"role": "user", "content": json.dumps(data, ensure_ascii=False)}],
            )
            text = "".join(getattr(b, "text", "") for b in response.content).strip()
            return text or self._short_fallback(data)
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка генерации короткого описания")
            return self._short_fallback(data)

    @staticmethod
    def _short_fallback(data: dict) -> str:
        kind = _KIND_RU.get(data.get("property_kind", ""), "объект")
        deal = _DEAL_RU.get(data.get("deal_type", ""), "")
        bits = []
        if data.get("rooms"):
            bits.append(f"{data['rooms']}-комн.")
        if data.get("area"):
            bits.append(f"{data['area']:g} м²")
        if data.get("district"):
            bits.append(f"район {data['district']}")
        line = kind.capitalize()
        if bits:
            line += ", " + ", ".join(bits)
        if deal:
            line += f", на {deal}"
        return line + ". Подробности — у риелтора."


_service: AIService | None = None


def get_ai_service() -> AIService:
    global _service
    if _service is None:
        _service = AIService()
    return _service
