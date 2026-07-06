"""Тесты публикации в канал и уведомлений."""
from bot.database import crud
from bot.database.models import (
    ClientDealType,
    PropertyKind,
    PropertyStatus,
    PropertyType,
)
from bot.services import publisher
from tests.conftest import FakeBot


async def test_publish_short_caption_album(session):
    bot = FakeBot()
    p = await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.rent,
                                   status=PropertyStatus.pending, district="Центр", rooms=2, price=1,
                                   currency="сум", photos="f1,f2,f3")
    prop = await publisher.publish_property(bot, session, p.id)
    assert prop.status == PropertyStatus.active
    assert prop.channel_post_id is not None
    assert ("album", "@test", 3) in bot.calls  # короткий текст -> альбом с подписью


async def test_publish_long_text_splits(session):
    bot = FakeBot()
    long_reno = "Евроремонт " + "очень длинное состояние " * 50
    p = await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.rent,
                                   status=PropertyStatus.pending, address="A", rooms=2, price=1,
                                   currency="сум", renovation=long_reno, photos="f1,f2")
    await publisher.publish_property(bot, session, p.id)
    kinds = [c[0] for c in bot.calls]
    assert "album" in kinds and "message" in kinds  # альбом без подписи + отдельный текст


async def test_album_over_ten_photos_chunked(session):
    bot = FakeBot()
    p = await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.rent,
                                   status=PropertyStatus.pending, rooms=2, price=1, currency="сум",
                                   photos=",".join(f"f{i}" for i in range(23)),
                                   renovation="x" * 1200)  # длинный текст -> альбомы без подписи
    await publisher.publish_property(bot, session, p.id)
    album_sizes = [c[2] for c in bot.calls if c[0] == "album"]
    assert album_sizes == [10, 10, 3]


async def test_mark_as_rented(session):
    bot = FakeBot()
    p = await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.sale,
                                   status=PropertyStatus.pending, rooms=2, price=1, currency="сум")
    await publisher.publish_property(bot, session, p.id)
    prop = await publisher.mark_as_rented(bot, session, p.id)
    assert prop.status == PropertyStatus.sold


async def test_publish_notifies_matching_client(session):
    bot = FakeBot()
    await crud.create_client(session, telegram_id=555, deal_type=ClientDealType.buy,
                             district="Центр", rooms=2, budget=100)
    p = await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.sale,
                                   status=PropertyStatus.pending, district="Центр", rooms=2, price=90, currency="сум")
    await publisher.publish_property(bot, session, p.id)
    notified = [chat for kind, chat, *_ in bot.calls if kind == "message" and chat == 555]
    assert 555 in notified
