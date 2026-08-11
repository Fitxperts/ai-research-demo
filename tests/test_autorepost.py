"""Тесты чистой логики авто-репоста: префильтр, дедуп-ключ, маппинг полей."""
from bot.database.models import PropertyKind, PropertyStatus, PropertyType
from bot.services import autorepost


def test_looks_like_listing_true():
    assert autorepost.looks_like_listing("Ижарага 2 хонали квартира Киргули 3 500 000 сум")
    assert autorepost.looks_like_listing("Sotiladi hovli, 5 sotix, 45000 $")


def test_looks_like_listing_false():
    assert not autorepost.looks_like_listing("Всем привет, как дела?")
    assert not autorepost.looks_like_listing("")
    assert not autorepost.looks_like_listing("реклама")  # нет цены/ключевых слов


def test_content_key_normalizes():
    # разные пробелы/регистр/эмодзи → один ключ (это один и тот же объект)
    a = autorepost.content_key("Ижара 2к  Киргули  450")
    b = autorepost.content_key("ижара 2к 🔥 киргули 450")
    assert a == b
    # другой текст → другой ключ
    assert a != autorepost.content_key("Сотув ховли 45000")


def test_to_property_fields_maps_enums():
    parsed = {"deal_type": "rent", "property_kind": "apartment", "rooms": 2,
              "district": "Киргули", "price": 3_500_000, "phone": "+998901112233"}
    fields = autorepost.to_property_fields(parsed)
    assert fields["type"] == PropertyType.rent
    assert fields["property_kind"] == PropertyKind.apartment
    assert fields["status"] == PropertyStatus.pending
    assert fields["currency"] == "сум"
    assert fields["owner_phone"] == "+998901112233"
    assert fields["rooms"] == 2 and fields["district"] == "Киргули"


def test_to_property_fields_defaults_kind_and_requires_deal():
    # неизвестный тип объекта → apartment
    f = autorepost.to_property_fields({"deal_type": "sale", "property_kind": "villa"})
    assert f["property_kind"] == PropertyKind.apartment
    assert f["type"] == PropertyType.sale
    # нет типа сделки → None (объект бесполезен)
    assert autorepost.to_property_fields({"rooms": 3}) is None
