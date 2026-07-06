"""Тесты валидаторов ввода."""
import datetime as dt

from bot.utils.validators import (
    is_valid_phone,
    parse_budget_range,
    parse_date,
    parse_int,
    parse_price,
)


def test_parse_price():
    assert parse_price("3 000 000") == 3000000.0
    assert parse_price("1500000") == 1500000.0
    assert parse_price("0") is None
    assert parse_price("abc") is None


def test_parse_int():
    assert parse_int("3") == 3
    assert parse_int(" 12 ") == 12
    assert parse_int("3.5") is None
    assert parse_int("x") is None


def test_parse_budget_range():
    assert parse_budget_range("1000000-2000000") == (1000000.0, 2000000.0)
    assert parse_budget_range("до 2000000") == (None, 2000000.0)
    assert parse_budget_range("от 1000000") == (1000000.0, None)
    assert parse_budget_range("1500000") == (None, 1500000.0)


def test_is_valid_phone():
    assert is_valid_phone("+998901234567")
    assert is_valid_phone("998901234567")
    assert not is_valid_phone("123")
    assert not is_valid_phone("phone")


def test_parse_date():
    assert parse_date("05.03.2026") == dt.date(2026, 3, 5)
    assert parse_date("5.3.26") == dt.date(2026, 3, 5)
    assert parse_date("нет") is None
