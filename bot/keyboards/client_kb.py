"""Клавиатуры сценария клиента."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PREFIX = "client"


def done_photos_stub() -> InlineKeyboardMarkup:  # noqa: D401 - совместимость импорта
    """Заглушка на будущее (клиенту фото не нужны)."""
    return InlineKeyboardMarkup(inline_keyboard=[])


def finish_search_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Искать", callback_data=f"{PREFIX}:confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"{PREFIX}:cancel")],
        ]
    )
