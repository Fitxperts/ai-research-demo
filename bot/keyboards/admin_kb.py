"""Инлайн-клавиатуры сценария администратора (модерация объектов)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PREFIX = "adm"


def moderation_kb(property_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"{PREFIX}:approve:{property_id}"),
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"{PREFIX}:edit:{property_id}"),
                InlineKeyboardButton(text="⏸ Отложить", callback_data=f"{PREFIX}:hold:{property_id}"),
            ]
        ]
    )
