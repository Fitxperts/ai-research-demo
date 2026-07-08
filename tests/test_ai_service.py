"""Тесты ИИ-сервиса (офлайн-режимы: без реального Anthropic)."""
import pytest

from bot.services.ai_service import escape_md, get_ai_service


def test_escape_md():
    assert escape_md("а.б(в)") == r"а\.б\(в\)"


def test_generate_description_no_broken_emoji():
    svc = get_ai_service()
    text = svc.generate_description(
        {"deal_type": "rent", "property_kind": "apartment", "address": "Тест",
         "rooms": 2, "price": 2000000, "negotiable": True}
    )
    # с плейсхолдерами ID кастомных эмодзи не должно быть tg://emoji
    assert "tg://emoji" not in text
    assert "🏢" in text
    assert "\\#Ижара" in text
    assert "2 000 000 сўм" in text
    assert "\\." in text  # экранированные точки MarkdownV2


@pytest.mark.parametrize(
    "text,expect",
    [
        ("2к чиланзар 450 хозяин", {"rooms": 2, "district": "Чиланзар", "price": 450.0}),
        ("продам 3 комн дом киргули 90000000", {"deal_type": "sale", "property_kind": "house", "rooms": 3}),
        ("сдаётся 1к центр 200000 +998901112233", {"deal_type": "rent", "phone": "+998901112233"}),
        # узбекская латиница
        ("2x margʻilon 450000 sotuv egasi", {"deal_type": "sale", "rooms": 2, "district": "Margʻilon"}),
        ("3 xonali kvartira ijaraga fargʻona 2500000",
         {"deal_type": "rent", "property_kind": "apartment", "rooms": 3, "district": "Fargʻona"}),
        ("hovli sotiladi qirguli 90000000", {"deal_type": "sale", "property_kind": "house", "district": "Qirguli"}),
    ],
)
def test_parse_free_text(text, expect):
    parsed = get_ai_service()._parse_regex(text)
    for k, v in expect.items():
        assert parsed.get(k) == v


def test_parse_free_text_phone_not_price():
    parsed = get_ai_service()._parse_regex("2к 450000 +998901112233")
    assert parsed["price"] == 450000.0  # телефон не спутан с ценой


def test_find_matches_budget_and_filters():
    svc = get_ai_service()
    client = {"deal_type": "rent", "budget": 2500000, "district": "центр", "rooms": 2}
    props = [
        {"type": "rent", "district": "Центр", "rooms": 2, "price": 2400000, "id": "A1"},
        {"type": "rent", "district": "Центр", "rooms": 2, "price": 5000000, "id": "A2"},  # > +10%
        {"type": "sale", "district": "Центр", "rooms": 2, "price": 100, "id": "A3"},       # др. сделка
    ]
    ids = [p["id"] for p in svc.find_matches(client, props)]
    assert ids == ["A1"]
