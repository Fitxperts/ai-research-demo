"""Инлайн-клавиатуры сценария собственника (мультиязычные)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import i18n

PREFIX = "ow"

# key -> i18n-ключ подписи
RENOVATION = {
    "rough": "reno_rough",
    "cosmetic": "reno_cosmetic",
    "euro": "reno_euro",
    "designer": "reno_designer",
}


def deal_type_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t("owner_deal_rent", lang), callback_data=f"{PREFIX}:deal:rent"),
                InlineKeyboardButton(text=i18n.t("owner_deal_sale", lang), callback_data=f"{PREFIX}:deal:sale"),
            ]
        ]
    )


def kind_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.btn("kind_apartment", lang), callback_data=f"{PREFIX}:kind:apartment"),
                InlineKeyboardButton(text=i18n.btn("kind_house", lang), callback_data=f"{PREFIX}:kind:house"),
            ],
            [
                InlineKeyboardButton(text=i18n.btn("kind_land", lang), callback_data=f"{PREFIX}:kind:land"),
                InlineKeyboardButton(text=i18n.btn("kind_commercial", lang), callback_data=f"{PREFIX}:kind:commercial"),
            ],
        ]
    )


def yesno_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ " + i18n.btn("yes", lang), callback_data=f"{PREFIX}:bool:yes"),
                InlineKeyboardButton(text="❌ " + i18n.btn("no", lang), callback_data=f"{PREFIX}:bool:no"),
            ]
        ]
    )


def renovation_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(msg_key, lang), callback_data=f"{PREFIX}:reno:{key}")]
            for key, msg_key in RENOVATION.items()
        ]
    )


def skip_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=i18n.btn("skip", lang), callback_data=f"{PREFIX}:skip")]]
    )


def photos_done_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=i18n.btn("done", lang), callback_data=f"{PREFIX}:pdone")]]
    )


def video_skip_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=i18n.btn("skip", lang), callback_data=f"{PREFIX}:novideo")]]
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
