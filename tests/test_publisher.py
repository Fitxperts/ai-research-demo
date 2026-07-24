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


async def test_publish_attaches_lead_button(session):
    bot = FakeBot()
    p = await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.rent,
                                   status=PropertyStatus.pending, district="Центр", price=1, currency="сум",
                                   photos="f1,f2,f3")
    prop = await publisher.publish_property(bot, session, p.id)
    # среди отправленных сообщений есть кнопка-заявка с deep-link на объект
    urls = [
        btn.url
        for kb in bot.markups if kb is not None
        for row in kb.inline_keyboard for btn in row if btn.url
    ]
    assert any(f"start=lead_{prop.id}" in u for u in urls), urls


async def test_lead_creates_client(session):
    from types import SimpleNamespace

    from bot.database.models import ClientDealType
    from bot.handlers import lead

    bot = FakeBot()
    p = await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.sale,
                                   status=PropertyStatus.active, district="Киргули", price=500, currency="сум")

    class FakeState:
        def __init__(self, data):
            self._d = dict(data)
        async def get_data(self):
            return self._d
        async def clear(self):
            self._d = {}

    msg = SimpleNamespace(
        from_user=SimpleNamespace(id=777, full_name="Али", username="ali"),
        answer=_noop_answer,
    )
    await lead._finish_lead(msg, FakeState({"lead_property_id": p.id}), session, bot, "ru", "+998901112233")

    clients = await crud.all_clients(session)
    assert len(clients) == 1
    assert clients[0].deal_type == ClientDealType.buy   # sale → buy
    assert clients[0].district == "Киргули" and clients[0].phone == "+998901112233"


async def _noop_answer(*a, **k):
    return None


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
