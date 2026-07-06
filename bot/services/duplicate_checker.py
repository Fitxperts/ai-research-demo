"""Проверка объектов на дубли.

Критерии (любой из):
- совпадение телефона собственника;
- совпадение адреса;
- совпадение район + комнаты + площадь (±5%) + цена (±5%).
"""
from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Property

_TOL = 0.05  # допуск ±5%


async def check_duplicates(session: AsyncSession, data: dict, *, exclude_id: str | None = None) -> list[Property]:
    phone = data.get("owner_phone") or data.get("phone")
    address = data.get("address")
    district = data.get("district")
    rooms = data.get("rooms")
    area = data.get("area")
    price = data.get("price")

    conditions = []

    if phone:
        conditions.append(Property.owner_phone == phone)
    if address:
        conditions.append(Property.address.ilike(f"%{address}%"))

    # Комбинированный критерий: район + комнаты + площадь ±5% + цена ±5%
    if district and rooms and area and price:
        conditions.append(
            and_(
                Property.district.ilike(f"%{district}%"),
                Property.rooms == rooms,
                Property.area.between(area * (1 - _TOL), area * (1 + _TOL)),
                Property.price.between(price * (1 - _TOL), price * (1 + _TOL)),
            )
        )

    if not conditions:
        return []

    stmt = select(Property).where(or_(*conditions))
    if exclude_id:
        stmt = stmt.where(Property.id != exclude_id)
    stmt = stmt.limit(5)
    return list(await session.scalars(stmt))
