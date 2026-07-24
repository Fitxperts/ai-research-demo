"""Инлайн-клавиатуры сценария собственника (мультиязычные).

Размещение идёт «одним сообщением» + дозапрос недостающего, поэтому здесь
только нужные клавиатуры: тип сделки, выбор массива, «Готово» под медиа,
подтверждение и разрешение дубля.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import i18n

PREFIX = "ow"

# Районы/массивы Ферганы для выбора (адрес-ориентир сохраняется отдельно)
FERGANA_MASSIVES = [
    "ЭкоСити Аэропорт",
    "Миндонобод",
    "Киргули",
    "Фрунзе",
    "Ахунбабаев",
    "Калининский",
    "Текстиль",
    "Военный городок",
    "Маталка",
]


def deal_type_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t("owner_deal_rent", lang), callback_data=f"{PREFIX}:deal:rent"),
                InlineKeyboardButton(text=i18n.t("owner_deal_sale", lang), callback_data=f"{PREFIX}:deal:sale"),
            ]
        ]
    )


def district_kb(lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(FERGANA_MASSIVES), 2):
        rows.append([
            InlineKeyboardButton(text=name, callback_data=f"{PREFIX}:mass:{idx}")
            for idx, name in enumerate(FERGANA_MASSIVES[i : i + 2], start=i)
        ])
    rows.append([
        InlineKeyboardButton(text=i18n.btn("massif_other", lang), callback_data=f"{PREFIX}:mass:other"),
        InlineKeyboardButton(text=i18n.btn("massif_skip", lang), callback_data=f"{PREFIX}:mass:skip"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_massif(idx: str) -> str | None:
    if not idx.isdigit():
        return None
    i = int(idx)
    return FERGANA_MASSIVES[i] if 0 <= i < len(FERGANA_MASSIVES) else None


def photos_done_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=i18n.btn("done", lang), callback_data=f"{PREFIX}:pdone")]]
    )


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.btn("confirm_send", lang), callback_data=f"{PREFIX}:confirm"),
                InlineKeyboardButton(text=i18n.btn("cancel", lang), callback_data=f"{PREFIX}:cancel"),
            ]
        ]
    )


def dup_confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ " + i18n.btn("yes", lang), callback_data=f"{PREFIX}:dupyes"),
                InlineKeyboardButton(text="❌ " + i18n.btn("no", lang), callback_data=f"{PREFIX}:dupno"),
            ]
        ]
    )
