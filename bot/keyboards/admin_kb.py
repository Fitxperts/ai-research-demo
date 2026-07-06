"""Клавиатуры сценария администратора."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.database.models import Client, ClientStatus, Property, PropertyStatus

PREFIX = "adm"

# Поля объекта, доступные для редактирования
EDIT_FIELDS = {
    "price": "Цена",
    "district": "Район",
    "address": "Адрес",
    "rooms": "Комнаты",
    "area": "Площадь",
    "renovation": "Ремонт",
    "description": "Описание",
}

CLIENT_STATUS_ORDER = [
    ClientStatus.new,
    ClientStatus.contacted,
    ClientStatus.showing_set,
    ClientStatus.showing_done,
    ClientStatus.deal,
    ClientStatus.closed,
]
_CLIENT_STATUS_LABELS = {
    ClientStatus.new: "Новый",
    ClientStatus.contacted: "Связались",
    ClientStatus.showing_set: "Показ назначен",
    ClientStatus.showing_done: "Показ проведён",
    ClientStatus.deal: "Сделка",
    ClientStatus.closed: "Закрыт",
}


# ---------------------------------------------------------------------------
# Меню
# ---------------------------------------------------------------------------
def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Новый объект"), KeyboardButton(text="📋 Объекты")],
            [KeyboardButton(text="👥 Клиенты"), KeyboardButton(text="📆 Встречи")],
            [KeyboardButton(text="📢 Публикации"), KeyboardButton(text="📊 Статистика")],
        ],
        resize_keyboard=True,
    )


# ---------------------------------------------------------------------------
# Объекты
# ---------------------------------------------------------------------------
def object_filters_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Все", callback_data=f"{PREFIX}:objs:all"),
                InlineKeyboardButton(text="Активные", callback_data=f"{PREFIX}:objs:active"),
            ],
            [
                InlineKeyboardButton(text="На проверке", callback_data=f"{PREFIX}:objs:pending"),
                InlineKeyboardButton(text="Сдано/Продано", callback_data=f"{PREFIX}:objs:sold"),
            ],
        ]
    )


def moderation_kb(property_id: str) -> InlineKeyboardMarkup:
    """Кнопки под уведомлением о новом объекте (модерация)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"{PREFIX}:approve:{property_id}"),
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"{PREFIX}:edit:{property_id}"),
                InlineKeyboardButton(text="⏸ Отложить", callback_data=f"{PREFIX}:hold:{property_id}"),
            ]
        ]
    )


def object_actions_kb(prop: Property) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if prop.status == PropertyStatus.pending:
        rows.append([
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"{PREFIX}:approve:{prop.id}"),
            InlineKeyboardButton(text="⏸ Отложить", callback_data=f"{PREFIX}:hold:{prop.id}"),
        ])
    if prop.status == PropertyStatus.active:
        rows.append([
            InlineKeyboardButton(text="📢 Поднять", callback_data=f"{PREFIX}:bump:{prop.id}"),
            InlineKeyboardButton(text="⛔ Сдано/Продано", callback_data=f"{PREFIX}:sold:{prop.id}"),
        ])
    rows.append([
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"{PREFIX}:edit:{prop.id}"),
        InlineKeyboardButton(text="🗄 Архив", callback_data=f"{PREFIX}:arch:{prop.id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_fields_kb(property_id: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{PREFIX}:efield:{property_id}:{key}")]
        for key, label in EDIT_FIELDS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Клиенты
# ---------------------------------------------------------------------------
def client_actions_kb(client: Client) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for status in CLIENT_STATUS_ORDER:
        mark = "🔘 " if status == client.status else ""
        row.append(
            InlineKeyboardButton(
                text=f"{mark}{_CLIENT_STATUS_LABELS[status]}",
                callback_data=f"{PREFIX}:cstatus:{client.id}:{status.value}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔎 Подходящие объекты", callback_data=f"{PREFIX}:cmatch:{client.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Встречи
# ---------------------------------------------------------------------------
def meetings_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="➕ Назначить встречу", callback_data=f"{PREFIX}:meet_new")]]
    )


def meeting_actions_kb(meeting_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Провёл", callback_data=f"{PREFIX}:mdone:{meeting_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"{PREFIX}:mcancel:{meeting_id}"),
            ]
        ]
    )


def more_kb(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬇️ Ещё", callback_data=callback_data)]]
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
def bump_kb(property_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📢 Поднять", callback_data=f"{PREFIX}:bump:{property_id}")]]
    )
