"""Форматирование доменных объектов для вывода в Telegram (HTML)."""
from __future__ import annotations

from html import escape

from bot.database.models import (
    Client,
    ClientDealType,
    ClientStatus,
    Meeting,
    MeetingStatus,
    Property,
    PropertyKind,
    PropertyStatus,
    PropertyType,
)

CLIENT_DEAL_LABELS = {ClientDealType.rent: "Аренда", ClientDealType.buy: "Покупка"}
CLIENT_STATUS_LABELS = {
    ClientStatus.new: "Новый",
    ClientStatus.contacted: "Связались",
    ClientStatus.showing_set: "Показ назначен",
    ClientStatus.showing_done: "Показ проведён",
    ClientStatus.deal: "Сделка",
    ClientStatus.closed: "Закрыт",
}
PROPERTY_STATUS_LABELS = {
    PropertyStatus.pending: "На проверке",
    PropertyStatus.active: "Активно",
    PropertyStatus.rented: "Сдано",
    PropertyStatus.sold: "Продано",
    PropertyStatus.archived: "Архив",
}
MEETING_STATUS_LABELS = {
    MeetingStatus.planned: "Запланирована",
    MeetingStatus.done: "Проведена",
    MeetingStatus.cancelled: "Отменена",
}
PROPERTY_TYPE_LABELS = {PropertyType.rent: "Аренда", PropertyType.sale: "Продажа"}
KIND_LABELS = {
    PropertyKind.apartment: "Квартира",
    PropertyKind.house: "Дом",
    PropertyKind.land: "Участок",
    PropertyKind.commercial: "Коммерческая",
}


def format_money(value: float | None, currency: str | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}".replace(",", " ") + f" {currency or ''}".rstrip()


def format_client_card(client: Client) -> str:
    deal = CLIENT_DEAL_LABELS.get(client.deal_type, client.deal_type.value)
    lines = [
        f"🆕 <b>Заявка {escape(client.id)}</b>",
        f"👤 {escape(client.name or '—')}",
        f"📞 {escape(client.phone or '—')}",
        "",
        f"Сделка: <b>{deal}</b>",
        f"Район: {escape(client.district or '—')}",
        f"Комнат: {client.rooms if client.rooms else '—'}",
        f"Бюджет: <b>{format_money(client.budget, client.currency)}</b>",
        f"Кто будет жить: {escape(client.residents or '—')}",
    ]
    if client.move_date:
        lines.append(f"Заселение: {client.move_date.strftime('%d.%m.%Y')}")
    return "\n".join(lines)


def format_property_card(prop: Property) -> str:
    kind = KIND_LABELS.get(prop.property_kind, prop.property_kind.value)
    deal = PROPERTY_TYPE_LABELS.get(prop.type, prop.type.value)
    lines = [f"🏠 <b>{kind} · {deal}</b> <code>{escape(prop.id)}</code>"]

    location = ", ".join(x for x in (prop.district, prop.address) if x)
    if location:
        lines.append(f"📍 {escape(location)}")

    facts: list[str] = []
    if prop.rooms:
        facts.append(f"🛏 {prop.rooms}-комн.")
    if prop.area:
        facts.append(f"📐 {prop.area:g} м²")
    if prop.floor and prop.floors:
        facts.append(f"🏢 {prop.floor}/{prop.floors} эт.")
    if facts:
        lines.append(" · ".join(facts))

    price = format_money(prop.price, prop.currency)
    if prop.negotiable:
        price += " (торг)"
    lines.append(f"💰 <b>{price}</b>")

    comms = _communications(prop)
    if comms:
        lines.append("✅ " + ", ".join(comms))

    if prop.description:
        lines.append("")
        lines.append(escape(prop.description))
    return "\n".join(lines)


def format_client_short(client: Client) -> str:
    deal = CLIENT_DEAL_LABELS.get(client.deal_type, client.deal_type.value)
    status = CLIENT_STATUS_LABELS.get(client.status, client.status.value)
    parts = [f"<b>{escape(client.id)}</b> · {escape(client.name or '—')}"]
    parts.append(f"{deal} · {escape(client.district or 'любой район')}")
    parts.append(f"Бюджет: {format_money(client.budget, client.currency)}")
    parts.append(f"📞 {escape(client.phone or '—')} · Статус: <b>{status}</b>")
    return "\n".join(parts)


def format_meeting(meeting: Meeting) -> str:
    when = meeting.datetime.strftime("%d.%m.%Y %H:%M") if meeting.datetime else "—"
    status = MEETING_STATUS_LABELS.get(meeting.status, meeting.status.value)
    return (
        f"📆 <b>{escape(meeting.id)}</b> — {when}\n"
        f"Клиент: {escape(meeting.client_id)} · Объект: {escape(meeting.property_id)}\n"
        f"Статус: {status}"
    )


def _communications(prop: Property) -> list[str]:
    mapping = [
        (prop.furniture, "мебель"),
        (prop.appliances, "техника"),
        (prop.gas, "газ"),
        (prop.water, "вода"),
        (prop.electricity, "свет"),
        (prop.internet, "интернет"),
    ]
    return [label for present, label in mapping if present]
