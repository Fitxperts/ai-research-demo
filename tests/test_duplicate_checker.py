"""Тесты проверки дублей."""
from bot.database import crud
from bot.database.models import PropertyKind, PropertyStatus, PropertyType
from bot.services import duplicate_checker


async def _seed(session):
    return await crud.create_property(
        session, property_kind=PropertyKind.apartment, type=PropertyType.rent,
        status=PropertyStatus.active, owner_phone="+998901112233",
        address="Чиланзар 12", district="Чиланзар", rooms=2, area=65, price=450,
    )


async def test_duplicate_by_phone(session):
    await _seed(session)
    dups = await duplicate_checker.check_duplicates(session, {"owner_phone": "+998901112233", "address": "иное"})
    assert len(dups) == 1


async def test_duplicate_by_address(session):
    await _seed(session)
    dups = await duplicate_checker.check_duplicates(session, {"phone": "+000", "address": "Чиланзар 12"})
    assert len(dups) == 1


async def test_duplicate_by_combo(session):
    await _seed(session)
    dups = await duplicate_checker.check_duplicates(
        session, {"district": "Чиланзар", "rooms": 2, "area": 66, "price": 460}
    )
    assert len(dups) == 1


async def test_no_duplicate_price_out_of_range(session):
    await _seed(session)
    dups = await duplicate_checker.check_duplicates(
        session, {"district": "Чиланзар", "rooms": 2, "area": 66, "price": 600}
    )
    assert dups == []
