"""Валидаторы пользовательского ввода."""
from __future__ import annotations

import re

_PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{7,17}\d$")


def parse_price(text: str) -> float | None:
    """Разобрать цену из свободного ввода ('1 500 000', '1.5 млн' не поддерживается)."""
    cleaned = text.replace(" ", "").replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value > 0 else None


def parse_int(text: str) -> int | None:
    text = text.strip()
    if not text.isdigit():
        return None
    return int(text)


def parse_budget_range(text: str) -> tuple[float | None, float | None] | None:
    """Разобрать бюджет вида '1000000-2000000', 'до 2000000' или '1500000'."""
    text = text.lower().replace(" ", "").replace(",", ".")
    if text.startswith("до"):
        value = _to_float(text[2:])
        return (None, value) if value else None
    if text.startswith("от"):
        value = _to_float(text[2:])
        return (value, None) if value else None
    if "-" in text:
        left, _, right = text.partition("-")
        lo, hi = _to_float(left), _to_float(right)
        if lo is None and hi is None:
            return None
        return (lo, hi)
    single = _to_float(text)
    return (None, single) if single else None


def is_valid_phone(text: str) -> bool:
    return bool(_PHONE_RE.match(text.strip()))


def _to_float(text: str) -> float | None:
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None
