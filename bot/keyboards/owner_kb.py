"""Клавиатуры сценария собственника."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.models import Listing, ListingStatus

PREFIX = "owner"


def photos_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Готово / без фото", callback_data=f"{PREFIX}:photos_done")]
        ]
    )


def listing_actions_keyboard(listing: Listing) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if listing.status in (ListingStatus.published,):
        rows.append(
            [InlineKeyboardButton(text="⬆️ Поднять", callback_data=f"{PREFIX}:bump:{listing.id}")]
        )
        rows.append(
            [InlineKeyboardButton(text="🗄 Снять с публикации", callback_data=f"{PREFIX}:archive:{listing.id}")]
        )
    if listing.status in (ListingStatus.draft, ListingStatus.rejected):
        rows.append(
            [InlineKeyboardButton(text="📤 Отправить на модерацию", callback_data=f"{PREFIX}:submit:{listing.id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
