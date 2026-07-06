"""Инлайн-клавиатуры сценария клиента."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PREFIX = "cl"

# Районы Ферганы
FERGANA_DISTRICTS = [
    "Центр",
    "Ёрмозор",
    "Киргули",
    "Селмаш",
    "Водник",
    "Дамкуль",
    "Юбилейный",
    "Ташлак",
]

# Состав проживающих: ключ -> подпись
RESIDENTS = {
    "one": "Один",
    "couple": "Пара",
    "family": "Семья с детьми",
    "students": "Студенты",
}

# Слоты по времени суток
TIME_SLOTS = {
    "morning": ["09:00", "10:00", "11:00"],
    "day": ["12:00", "13:00", "14:00", "15:00"],
    "evening": ["16:00", "17:00", "18:00"],
}
PERIOD_LABELS = {"morning": "Утро", "day": "День", "evening": "Вечер"}


def deal_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔑 Аренда", callback_data=f"{PREFIX}:deal:rent"),
                InlineKeyboardButton(text="🏷 Покупка", callback_data=f"{PREFIX}:deal:buy"),
            ]
        ]
    )


def districts_kb() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(FERGANA_DISTRICTS), 2):
        row = [
            InlineKeyboardButton(text=name, callback_data=f"{PREFIX}:dist:{idx}")
            for idx, name in enumerate(FERGANA_DISTRICTS[i : i + 2], start=i)
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✍️ Другой район", callback_data=f"{PREFIX}:dist:other")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rooms_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data=f"{PREFIX}:rooms:1"),
                InlineKeyboardButton(text="2", callback_data=f"{PREFIX}:rooms:2"),
                InlineKeyboardButton(text="3", callback_data=f"{PREFIX}:rooms:3"),
                InlineKeyboardButton(text="4+", callback_data=f"{PREFIX}:rooms:4"),
            ]
        ]
    )


def residents_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"{PREFIX}:res:{key}")]
            for key, label in RESIDENTS.items()
        ]
    )


def skip_date_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data=f"{PREFIX}:skipdate")]]
    )


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data=f"{PREFIX}:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"{PREFIX}:cancel"),
            ]
        ]
    )


def period_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=label, callback_data=f"{PREFIX}:period:{key}")
                for key, label in PERIOD_LABELS.items()
            ]
        ]
    )


def slots_kb(period: str) -> InlineKeyboardMarkup:
    slots = TIME_SLOTS.get(period, [])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=slot, callback_data=f"{PREFIX}:slot:{slot}") for slot in slots]
        ]
    )


def get_district(idx: str) -> str | None:
    if idx == "other" or not idx.isdigit():
        return None
    i = int(idx)
    return FERGANA_DISTRICTS[i] if 0 <= i < len(FERGANA_DISTRICTS) else None
