"""Работа со временем в часовом поясе приложения.

Все внутренние сравнения времени (напоминания, автоподнятие) должны
использовать одну и ту же зону, иначе логика напоминаний ломается на серверах
с UTC. Возвращаем timezone-aware datetime — так сравнения корректны и в
PostgreSQL (timestamptz).
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from bot.config import TIMEZONE

_TZ = ZoneInfo(TIMEZONE)


def now() -> dt.datetime:
    """Текущее время в зоне приложения (aware)."""
    return dt.datetime.now(_TZ)


def localize(value: dt.datetime) -> dt.datetime:
    """Пометить наивное локальное время зоной приложения."""
    return value.replace(tzinfo=_TZ) if value.tzinfo is None else value
