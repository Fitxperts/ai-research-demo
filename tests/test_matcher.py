"""Тесты подбора (клиент↔объект)."""
from bot.database import crud
from bot.database.models import (
    ClientDealType,
    PropertyKind,
    PropertyStatus,
    PropertyType,
)
from bot.services import matcher


async def test_find_for_client(session):
    c = await crud.create_client(session, telegram_id=1, deal_type=ClientDealType.rent,
                                 district="Центр", rooms=2, budget=2500000)
    await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.rent,
                               status=PropertyStatus.active, district="Центр", rooms=2, price=2000000)
    await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.sale,
                               status=PropertyStatus.active, district="Центр", rooms=2, price=100)
    res = await matcher.find_for_client(session, c)
    assert len(res) == 1  # только аренда


async def test_clients_for_property(session):
    await crud.create_client(session, telegram_id=101, deal_type=ClientDealType.buy,
                             district="Центр", rooms=2, budget=100)   # match
    await crud.create_client(session, telegram_id=102, deal_type=ClientDealType.buy,
                             district="Центр", rooms=2, budget=50)    # бюджет мимо
    await crud.create_client(session, telegram_id=103, deal_type=ClientDealType.rent,
                             district="Центр", rooms=2, budget=100)   # др. сделка
    await crud.create_client(session, telegram_id=104, deal_type=ClientDealType.buy,
                             district=None, rooms=None, budget=None)  # без критериев -> match
    p = await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.sale,
                                   status=PropertyStatus.active, district="Центр", rooms=2, price=90)
    clients = await matcher.clients_for_property(session, p)
    ids = sorted(c.telegram_id for c in clients)
    assert ids == [101, 104]
