"""Подбор объектов недвижимости под заявку клиента."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.database.models import Client, ClientDealType, Property, PropertyType

# Сопоставление типа сделки клиента и типа объекта
_DEAL_MAP = {
    ClientDealType.rent: PropertyType.rent,
    ClientDealType.buy: PropertyType.sale,
}


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
