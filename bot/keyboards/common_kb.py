"""Общие клавиатуры: выбор роли и меню ролей."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def role_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Ищу жильё", callback_data="role:client")],
            [InlineKeyboardButton(text="🏠 Хочу сдать/продать", callback_data="role:owner")],
        ]
    )


def client_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔎 Подобрать жильё")],
            [KeyboardButton(text="↩️ Сменить роль")],
        ],
        resize_keyboard=True,
    )


def owner_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Разместить объект"), KeyboardButton(text="📋 Мои объекты")],
            [KeyboardButton(text="↩️ Сменить роль")],
        ],
        resize_keyboard=True,
    )
