"""Подбор объектов недвижимости под заявку клиента и наоборот."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.database.models import (
    Client,
    ClientDealType,
    ClientStatus,
    Property,
    PropertyType,
)

# Сопоставление типа сделки клиента и типа объекта
_DEAL_MAP = {
    ClientDealType.rent: PropertyType.rent,
    ClientDealType.buy: PropertyType.sale,
}
# Обратное сопоставление: тип объекта → тип сделки клиента
_REVERSE_DEAL_MAP = {
    PropertyType.rent: ClientDealType.rent,
    PropertyType.sale: ClientDealType.buy,
}
_TOL = 0.10  # допуск по бюджету +10%


async def find_for_client(session: AsyncSession, client: Client, *, limit: int = 5) -> list[Property]:
    """Найти активные объекты, подходящие под заявку клиента."""
    return await crud.search_properties(
        session,
        prop_type=_DEAL_MAP.get(client.deal_type),
        district=client.district,
        rooms=client.rooms,
        max_price=float(client.budget) if client.budget is not None else None,
        limit=limit,
    )


async def clients_for_property(session: AsyncSession, prop: Property, *, limit: int = 100) -> list[Client]:
    """Найти клиентов (не закрытых), чьи заявки подходят под объект."""
    want_deal = _REVERSE_DEAL_MAP.get(prop.type)
    if want_deal is None:
        return []

    stmt = select(Client).where(
        Client.deal_type == want_deal,
        Client.status != ClientStatus.closed,
    )
    candidates = list(await session.scalars(stmt))

    price = float(prop.price) if prop.price is not None else None
    result: list[Client] = []
    for client in candidates:
        # Бюджет: цена объекта не выше бюджета клиента +10%
        if price is not None and client.budget is not None and price > float(client.budget) * (1 + _TOL):
            continue
        # Район: если у клиента задан — объект должен ему соответствовать
        if client.district and prop.district and client.district.lower() not in prop.district.lower():
            continue
        # Комнаты: если заданы у клиента — должны совпадать
        if client.rooms is not None and prop.rooms is not None and client.rooms != prop.rooms:
            continue
        result.append(client)
        if len(result) >= limit:
            break
    return result
