"""Общие клавиатуры: выбор роли, главное меню."""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.database.models import DealType, PropertyType


def role_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Я ищу недвижимость", callback_data="role:client")],
            [InlineKeyboardButton(text="🏠 Я собственник", callback_data="role:owner")],
        ]
    )


def client_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔎 Подобрать недвижимость")],
            [KeyboardButton(text="🤖 Спросить ассистента")],
            [KeyboardButton(text="↩️ Сменить роль")],
        ],
        resize_keyboard=True,
    )


def owner_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Разместить объявление")],
            [KeyboardButton(text="📋 Мои объявления")],
            [KeyboardButton(text="↩️ Сменить роль")],
        ],
        resize_keyboard=True,
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🕵️ Модерация")],
            [KeyboardButton(text="📊 Статистика")],
        ],
        resize_keyboard=True,
    )


def deal_type_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Продажа", callback_data=f"{prefix}:deal:{DealType.sale.value}")],
            [InlineKeyboardButton(text="Аренда", callback_data=f"{prefix}:deal:{DealType.rent.value}")],
        ]
    )


def property_type_keyboard(prefix: str, *, with_any: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Квартира", callback_data=f"{prefix}:prop:{PropertyType.apartment.value}")],
        [InlineKeyboardButton(text="Дом", callback_data=f"{prefix}:prop:{PropertyType.house.value}")],
        [InlineKeyboardButton(text="Комната", callback_data=f"{prefix}:prop:{PropertyType.room.value}")],
        [InlineKeyboardButton(text="Коммерческая", callback_data=f"{prefix}:prop:{PropertyType.commercial.value}")],
    ]
    if with_any:
        rows.append([InlineKeyboardButton(text="Не важно", callback_data=f"{prefix}:prop:any")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data=f"{prefix}:skip")]]
    )


def confirm_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{prefix}:confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"{prefix}:cancel")],
        ]
    )
