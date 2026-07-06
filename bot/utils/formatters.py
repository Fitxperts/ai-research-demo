"""Форматирование доменных объектов для вывода в Telegram (HTML)."""
from __future__ import annotations

from html import escape

from bot.database.models import DealType, Listing, PropertyType

_PROPERTY_LABELS = {
    PropertyType.apartment: "Квартира",
    PropertyType.house: "Дом",
    PropertyType.room: "Комната",
    PropertyType.commercial: "Коммерческая",
}

_DEAL_LABELS = {
    DealType.sale: "Продажа",
    DealType.rent: "Аренда",
}


def property_label(value: PropertyType) -> str:
    return _PROPERTY_LABELS.get(value, value.value)


def deal_label(value: DealType) -> str:
    return _DEAL_LABELS.get(value, value.value)


def format_price(value: float) -> str:
    return f"{int(value):,}".replace(",", " ") + " ₽"


def format_listing(listing: Listing, *, with_status: bool = False) -> str:
    lines = [f"<b>{escape(listing.title)}</b>"]
    lines.append(
        f"{deal_label(listing.deal_type)} · {property_label(listing.property_type)}"
    )
    lines.append(f"💰 <b>{format_price(float(listing.price))}</b>")

    details: list[str] = []
    if listing.rooms:
        details.append(f"🛏 {listing.rooms}-комн.")
    if listing.area:
        details.append(f"📐 {float(listing.area):g} м²")
    if details:
        lines.append(" · ".join(details))

    if listing.district:
        lines.append(f"📍 {escape(listing.district)}")
    if listing.address:
        lines.append(f"🏠 {escape(listing.address)}")
    if listing.description:
        lines.append("")
        lines.append(escape(listing.description))

    if with_status:
        lines.append("")
        lines.append(f"Статус: <i>{listing.status.value}</i>")
        if listing.reject_reason:
            lines.append(f"Причина отклонения: {escape(listing.reject_reason)}")

    return "\n".join(lines)
