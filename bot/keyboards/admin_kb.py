"""Клавиатуры сценария администратора (модерация)."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PREFIX = "admin"


def moderation_keyboard(listing_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"{PREFIX}:approve:{listing_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"{PREFIX}:reject:{listing_id}"),
            ]
        ]
    )
