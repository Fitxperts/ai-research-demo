"""Планировщик фоновых задач (APScheduler).

Заглушка Шага 3: создаётся планировщик с нужным часовым поясом. Конкретные
задачи (автоподнятие объявлений, напоминания о встречах) добавляются на
последующих шагах.
"""
from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import TIMEZONE

logger = logging.getLogger(__name__)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    # Задачи будут зарегистрированы на следующих шагах:
    #   - автоподнятие объявлений (раз в BUMP_INTERVAL_DAYS)
    #   - напоминания о встречах (за 1 день / 2 часа / 30 минут)
    logger.info("Планировщик инициализирован (TZ=%s)", TIMEZONE)
    return scheduler
