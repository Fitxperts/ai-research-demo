"""Общие клавиатуры: выбор языка, выбор роли и меню ролей."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot import i18n


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"lang:{code}")]
            for code, label in i18n.LANGUAGES.items()
        ]
    )


def role_choice_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.btn("role_client", lang), callback_data="role:client")],
            [InlineKeyboardButton(text=i18n.btn("role_owner", lang), callback_data="role:owner")],
        ]
    )


def client_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.btn("find_housing", lang))],
            [
                KeyboardButton(text=i18n.btn("language", lang)),
                KeyboardButton(text=i18n.btn("change_role", lang)),
            ],
        ],
        resize_keyboard=True,
    )


def owner_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=i18n.btn("add_object", lang)),
                KeyboardButton(text=i18n.btn("my_objects", lang)),
            ],
            [
                KeyboardButton(text=i18n.btn("language", lang)),
                KeyboardButton(text=i18n.btn("change_role", lang)),
            ],
        ],
        resize_keyboard=True,
    )
