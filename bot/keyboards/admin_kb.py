"""Клавиатуры сценария администратора (мультиязычные)."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot import i18n
from bot.database.models import Client, ClientStatus, Property, PropertyStatus

PREFIX = "adm"

# Поля объекта, доступные для редактирования: key -> i18n-ключ подписи
EDIT_FIELDS = {
    "price": "ef_price",
    "district": "ef_district",
    "address": "ef_address",
    "rooms": "ef_rooms",
    "area": "ef_area",
    "renovation": "ef_renovation",
    "description": "ef_description",
}

CLIENT_STATUS_ORDER = [
    ClientStatus.new,
    ClientStatus.contacted,
    ClientStatus.showing_set,
    ClientStatus.showing_done,
    ClientStatus.deal,
    ClientStatus.closed,
]


def edit_field_label(field: str, lang: str = "ru") -> str:
    return i18n.t(EDIT_FIELDS.get(field, field), lang)


# ---------------------------------------------------------------------------
# Меню
# ---------------------------------------------------------------------------
def main_menu(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.btn("adm_new", lang)), KeyboardButton(text=i18n.btn("adm_objects", lang))],
            [KeyboardButton(text=i18n.btn("adm_clients", lang)), KeyboardButton(text=i18n.btn("adm_meetings", lang))],
            [KeyboardButton(text=i18n.btn("adm_publications", lang)), KeyboardButton(text=i18n.btn("adm_stats", lang))],
            [KeyboardButton(text=i18n.btn("language", lang))],
        ],
        resize_keyboard=True,
    )


# ---------------------------------------------------------------------------
# Объекты
# ---------------------------------------------------------------------------
def object_filters_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.btn("adm_f_all", lang), callback_data=f"{PREFIX}:objs:all"),
                InlineKeyboardButton(text=i18n.btn("adm_f_active", lang), callback_data=f"{PREFIX}:objs:active"),
            ],
            [
                InlineKeyboardButton(text=i18n.btn("adm_f_pending", lang), callback_data=f"{PREFIX}:objs:pending"),
                InlineKeyboardButton(text=i18n.btn("adm_f_sold", lang), callback_data=f"{PREFIX}:objs:sold"),
            ],
        ]
    )


def moderation_kb(property_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки под уведомлением о новом объекте (модерация)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.btn("adm_approve", lang), callback_data=f"{PREFIX}:approve:{property_id}"),
                InlineKeyboardButton(text=i18n.btn("adm_edit", lang), callback_data=f"{PREFIX}:edit:{property_id}"),
                InlineKeyboardButton(text=i18n.btn("adm_hold", lang), callback_data=f"{PREFIX}:hold:{property_id}"),
            ]
        ]
    )


def object_actions_kb(prop: Property, lang: str = "ru") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if prop.status == PropertyStatus.pending:
        rows.append([
            InlineKeyboardButton(text=i18n.btn("adm_approve", lang), callback_data=f"{PREFIX}:approve:{prop.id}"),
            InlineKeyboardButton(text=i18n.btn("adm_hold", lang), callback_data=f"{PREFIX}:hold:{prop.id}"),
        ])
    if prop.status == PropertyStatus.active:
        rows.append([
            InlineKeyboardButton(text=i18n.btn("adm_bump", lang), callback_data=f"{PREFIX}:bump:{prop.id}"),
            InlineKeyboardButton(text=i18n.btn("adm_sold_btn", lang), callback_data=f"{PREFIX}:sold:{prop.id}"),
        ])
    rows.append([
        InlineKeyboardButton(text=i18n.btn("adm_edit", lang), callback_data=f"{PREFIX}:edit:{prop.id}"),
        InlineKeyboardButton(text=i18n.btn("adm_archive", lang), callback_data=f"{PREFIX}:arch:{prop.id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_fields_kb(property_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=i18n.t(msg_key, lang), callback_data=f"{PREFIX}:efield:{property_id}:{key}")]
        for key, msg_key in EDIT_FIELDS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Клиенты
# ---------------------------------------------------------------------------
def client_actions_kb(client: Client, lang: str = "ru") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for status in CLIENT_STATUS_ORDER:
        mark = "🔘 " if status == client.status else ""
        row.append(
            InlineKeyboardButton(
                text=f"{mark}{i18n.t(f'cst_{status.value}', lang)}",
                callback_data=f"{PREFIX}:cstatus:{client.id}:{status.value}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=i18n.btn("adm_matches", lang), callback_data=f"{PREFIX}:cmatch:{client.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Встречи
# ---------------------------------------------------------------------------
def meetings_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=i18n.btn("adm_new_meeting", lang), callback_data=f"{PREFIX}:meet_new")]]
    )


def meeting_actions_kb(meeting_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.btn("adm_m_done", lang), callback_data=f"{PREFIX}:mdone:{meeting_id}"),
                InlineKeyboardButton(text=i18n.btn("adm_m_cancel", lang), callback_data=f"{PREFIX}:mcancel:{meeting_id}"),
            ]
        ]
    )


def more_kb(callback_data: str, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=i18n.btn("adm_more", lang), callback_data=callback_data)]]
    )


def export_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.btn("adm_exp_props_xlsx", lang), callback_data=f"{PREFIX}:export:props:xlsx"),
                InlineKeyboardButton(text=i18n.btn("adm_exp_props_csv", lang), callback_data=f"{PREFIX}:export:props:csv"),
            ],
            [
                InlineKeyboardButton(text=i18n.btn("adm_exp_cli_xlsx", lang), callback_data=f"{PREFIX}:export:clients:xlsx"),
                InlineKeyboardButton(text=i18n.btn("adm_exp_cli_csv", lang), callback_data=f"{PREFIX}:export:clients:csv"),
            ],
        ]
    )


def pick_clients_kb(clients: list[Client]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{c.id} · {c.name or '—'}", callback_data=f"{PREFIX}:mclient:{c.id}")]
        for c in clients
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pick_properties_kb(props: list[Property]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{p.id} · {p.district or '—'}", callback_data=f"{PREFIX}:mprop:{p.id}")]
        for p in props
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Публикации
# ---------------------------------------------------------------------------
def bump_kb(property_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=i18n.btn("adm_bump", lang), callback_data=f"{PREFIX}:bump:{property_id}")]]
    )


def language_kb() -> InlineKeyboardMarkup:
    """Пикер языка для админа (callback alang:<code>)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"alang:{code}")]
            for code, label in i18n.LANGUAGES.items()
        ]
    )
