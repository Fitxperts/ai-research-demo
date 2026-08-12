"""Чистая логика авто-репоста из чужих каналов (без сети — легко тестируется).

- looks_like_listing(text) — дешёвый префильтр «это вообще объявление о недвижимости?»
  (чтобы не гонять ИИ на каждое случайное сообщение канала);
- content_key(text) — ключ дедупликации по нормализованному тексту (ловит один и
  тот же объект, перепощенный в разных каналах);
- to_property_fields(parsed) — маппинг разбора ИИ в аргументы create_property.
"""
from __future__ import annotations

import hashlib
import re

from bot.database.models import PropertyKind, PropertyStatus, PropertyType

# Ключевые слова недвижимости (RU / UZ-latin) — хотя бы одно должно встретиться.
_ESTATE_WORDS = (
    "ижара", "ижарага", "аренда", "аренду", "сдается", "сдаётся", "сдам",
    "сотув", "сотилади", "продажа", "продается", "продаётся", "продам",
    "квартира", "кв.", "хона", "хонали", "уй", "ховли", "дом", "участок", "ер",
    "комнат", "этаж", "массив", "мкр",
    "ijara", "ijaraga", "sotuv", "sotiladi", "soiladi", "sotladi", "sotib",
    "kvartira", "xona", "xonali", "hovli", "uy", "uchastka", "yer", "qavat",
)
# Признаки цены/денег — усиливают уверенность.
_MONEY_WORDS = ("сум", "сўм", "so'm", "som", "$", "у.е", "у.е.", "ye", "млн", "минг", "000")

_KINDS = {"apartment", "house", "land", "commercial"}


def looks_like_listing(text: str | None) -> bool:
    """Грубый префильтр: похоже ли сообщение на объявление о недвижимости."""
    if not text:
        return False
    low = text.lower()
    if len(low) < 10:
        return False
    has_estate = any(w in low for w in _ESTATE_WORDS)
    has_money = any(w in low for w in _MONEY_WORDS) or bool(re.search(r"\d{3,}", low))
    return has_estate and has_money


def content_key(text: str) -> str:
    """Ключ дедупликации: нормализуем текст (только буквы/цифры) и берём хэш."""
    normalized = re.sub(r"[^0-9a-zа-яёўқғҳ]+", "", (text or "").lower())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()  # noqa: S324 - не для криптографии


def to_property_fields(parsed: dict) -> dict | None:
    """Разбор ИИ → аргументы crud.create_property. None — если нет типа сделки."""
    deal = parsed.get("deal_type")
    if deal not in ("rent", "sale"):
        return None  # без типа сделки объект бесполезен

    kind = parsed.get("property_kind")
    if kind not in _KINDS:
        kind = "apartment"

    fields: dict = {
        "type": PropertyType(deal),
        "property_kind": PropertyKind(kind),
        "status": PropertyStatus.pending,
        "currency": "сум",
    }
    for key in ("district", "address", "rooms", "area", "floor", "floors", "price", "description"):
        value = parsed.get(key)
        if value is not None:
            fields[key] = value
    phone = parsed.get("phone")
    if phone:
        fields["owner_phone"] = phone
    return fields
