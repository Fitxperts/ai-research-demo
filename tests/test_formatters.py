"""Тесты форматирования карточек."""
from bot.database.models import (
    Client,
    ClientDealType,
    ClientStatus,
    Property,
    PropertyKind,
    PropertyType,
)
from bot.utils.formatters import (
    format_client_short,
    format_money,
    format_property_brief,
    format_property_card,
)


def test_format_money():
    assert format_money(2000000, "сум") == "2 000 000 сум"
    assert format_money(None, "сум") == "—"


def test_format_property_card():
    p = Property(id="APT_1001", type=PropertyType.sale, property_kind=PropertyKind.apartment,
                 district="Центр", address="ул. X 1", rooms=3, area=75.5, floor=4, floors=9,
                 price=45000000, currency="сум", negotiable=True, gas=True, water=True)
    card = format_property_card(p)
    assert "Квартира" in card and "Продажа" in card
    assert "45 000 000 сум (торг)" in card
    assert "3-комн." in card


def test_format_property_brief():
    p = Property(id="APT_1012", type=PropertyType.rent, property_kind=PropertyKind.apartment,
                 district="Чиланзар", rooms=2, area=65, price=450, currency="$")
    assert format_property_brief(p) == "APT_1012 (Чиланзар, 2к, 65м², 450 $)"


def test_format_client_short_escapes_html():
    c = Client(id="CLT_001", telegram_id=1, name="<b>Хакер</b>", phone="+998",
               deal_type=ClientDealType.rent, district="Центр", budget=100, currency="сум",
               status=ClientStatus.new)
    out = format_client_short(c)
    assert "&lt;b&gt;" in out  # HTML экранирован
