"""Форматирование доменных объектов для вывода в Telegram (HTML, мультиязычно).

Все функции принимают ``lang`` (по умолчанию ``ru``) и берут подписи из
каталога ``bot.i18n``. Данные (адреса, имена, суммы) не переводятся.
"""
from __future__ import annotations

from html import escape

from bot import i18n
from bot.database.models import (
    Client,
    Meeting,
    Property,
    PropertyStatus,
)

# Русские подписи статусов объекта (для обратной совместимости/экспорта)
PROPERTY_STATUS_LABELS = {
    PropertyStatus.pending: "На проверке",
    PropertyStatus.active: "Активно",
    PropertyStatus.rented: "Сдано",
    PropertyStatus.sold: "Продано",
    PropertyStatus.archived: "Архив",
}


def property_status_label(status: PropertyStatus, lang: str = "ru") -> str:
    return i18n.t(f"pst_{status.value}", lang)


def format_money(value: float | None, currency: str | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}".replace(",", " ") + f" {currency or ''}".rstrip()


def format_client_card(client: Client, lang: str = "ru") -> str:
    deal = i18n.t(f"cd_{client.deal_type.value}", lang)
    lines = [
        i18n.t("cc_request", lang, id=escape(client.id)),
        f"👤 {escape(client.name or '—')}",
        f"📞 {escape(client.phone or '—')}",
        "",
        f"{i18n.t('cc_deal', lang)}: <b>{deal}</b>",
        f"{i18n.t('cc_district', lang)}: {escape(client.district or '—')}",
        f"{i18n.t('cc_rooms', lang)}: {client.rooms if client.rooms else '—'}",
        f"{i18n.t('cc_budget', lang)}: <b>{format_money(client.budget, client.currency)}</b>",
        f"{i18n.t('cc_residents', lang)}: {escape(client.residents or '—')}",
    ]
    if client.move_date:
        lines.append(f"{i18n.t('cc_movein', lang)}: {client.move_date.strftime('%d.%m.%Y')}")
    return "\n".join(lines)


def format_property_card(prop: Property, lang: str = "ru") -> str:
    kind = i18n.t(f"kw_{prop.property_kind.value}", lang)
    deal = i18n.t(f"pt_{prop.type.value}", lang)
    lines = [f"🏠 <b>{kind} · {deal}</b> <code>{escape(prop.id)}</code>"]

    location = ", ".join(x for x in (prop.district, prop.address) if x)
    if location:
        lines.append(f"📍 {escape(location)}")

    facts: list[str] = []
    if prop.rooms:
        facts.append(f"🛏 {prop.rooms}{i18n.t('card_rooms_suffix', lang)}")
    if prop.area:
        facts.append(f"📐 {prop.area:g} {i18n.t('card_area_unit', lang)}")
    if prop.floor and prop.floors:
        facts.append(f"🏢 {prop.floor}/{prop.floors} {i18n.t('card_floor_suffix', lang)}")
    if facts:
        lines.append(" · ".join(facts))

    price = format_money(prop.price, prop.currency)
    if prop.negotiable:
        price += f" ({i18n.t('card_neg', lang)})"
    lines.append(f"💰 <b>{price}</b>")

    comms = _communications(prop, lang)
    if comms:
        lines.append("✅ " + ", ".join(comms))

    if prop.description:
        lines.append("")
        lines.append(escape(prop.description))
    return "\n".join(lines)


def format_property_brief(prop: Property) -> str:
    """Краткая строка объекта: APT_1012 (Центр, 2к, 65м², 450 сум)."""
    details: list[str] = []
    if prop.district:
        details.append(prop.district)
    if prop.rooms:
        details.append(f"{prop.rooms}к")
    if prop.area:
        details.append(f"{prop.area:g}м²")
    if prop.price:
        details.append(format_money(prop.price, prop.currency))
    inner = ", ".join(details)
    return f"{escape(prop.id)} ({escape(inner)})" if inner else escape(prop.id)


def format_client_short(client: Client, lang: str = "ru") -> str:
    deal = i18n.t(f"cd_{client.deal_type.value}", lang)
    status = i18n.t(f"cst_{client.status.value}", lang)
    district = client.district or i18n.t("cc_any_district", lang)
    parts = [
        f"<b>{escape(client.id)}</b> · {escape(client.name or '—')}",
        f"{deal} · {escape(district)}",
        f"{i18n.t('cc_budget', lang)}: {format_money(client.budget, client.currency)}",
        f"📞 {escape(client.phone or '—')} · {i18n.t('cc_status', lang)}: <b>{status}</b>",
    ]
    return "\n".join(parts)


def format_meeting(meeting: Meeting, lang: str = "ru") -> str:
    when = meeting.datetime.strftime("%d.%m.%Y %H:%M") if meeting.datetime else "—"
    status = i18n.t(f"mst_{meeting.status.value}", lang)
    return (
        f"📆 <b>{escape(meeting.id)}</b> — {when}\n"
        f"{i18n.t('mc_client', lang)}: {escape(meeting.client_id)} · "
        f"{i18n.t('mc_object', lang)}: {escape(meeting.property_id)}\n"
        f"{i18n.t('mc_status', lang)}: {status}"
    )


def _communications(prop: Property, lang: str = "ru") -> list[str]:
    mapping = [
        (prop.furniture, "comm_furniture"),
        (prop.appliances, "comm_appliances"),
        (prop.gas, "comm_gas"),
        (prop.water, "comm_water"),
        (prop.electricity, "comm_electricity"),
        (prop.internet, "comm_internet"),
    ]
    return [i18n.t(key, lang) for present, key in mapping if present]
