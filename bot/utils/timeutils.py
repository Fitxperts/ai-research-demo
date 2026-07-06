"""Работа со временем в часовом поясе приложения.

Все внутренние сравнения и хранение времени ведём как «наивное локальное»
время зоны приложения (Asia/Tashkent). Это гарантирует, что напоминания,
автоподнятие и отображение времени согласованы независимо от часового пояса
сервера (в контейнере обычно UTC), и не зависят от нюансов timestamptz.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from bot.config import TIMEZONE

_TZ = ZoneInfo(TIMEZONE)


def now() -> dt.datetime:
    """Текущее локальное время зоны приложения (наивное)."""
    return dt.datetime.now(_TZ).replace(tzinfo=None)
