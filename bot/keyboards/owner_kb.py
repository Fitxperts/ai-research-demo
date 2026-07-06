"""Инлайн-клавиатуры сценария собственника."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PREFIX = "ow"

RENOVATION = {
    "rough": "Черновая",
    "cosmetic": "Косметический",
    "euro": "Евроремонт",
    "designer": "Дизайнерский",
}


def deal_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔑 Аренда", callback_data=f"{PREFIX}:deal:rent"),
                InlineKeyboardButton(text="🏷 Продажа", callback_data=f"{PREFIX}:deal:sale"),
            ]
        ]
    )


def kind_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏢 Квартира", callback_data=f"{PREFIX}:kind:apartment"),
                InlineKeyboardButton(text="🏡 Дом", callback_data=f"{PREFIX}:kind:house"),
            ],
            [
                InlineKeyboardButton(text="🌳 Участок", callback_data=f"{PREFIX}:kind:land"),
                InlineKeyboardButton(text="🏬 Коммерция", callback_data=f"{PREFIX}:kind:commercial"),
            ],
        ]
    )


def yesno_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"{PREFIX}:bool:yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"{PREFIX}:bool:no"),
            ]
        ]
    )


def renovation_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"{PREFIX}:reno:{key}")]
            for key, label in RENOVATION.items()
        ]
    )


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data=f"{PREFIX}:skip")]]
    )


def photos_done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Готово / без фото", callback_data=f"{PREFIX}:pdone")]]
    )


def video_skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Без видео", callback_data=f"{PREFIX}:novideo")]]
    )


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"{PREFIX}:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"{PREFIX}:cancel"),
            ]
        ]
    )


def dup_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, добавить", callback_data=f"{PREFIX}:dupyes"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"{PREFIX}:dupno"),
            ]
        ]
    )
