"""Планировщик фоновых задач: автоподнятие объявлений."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import get_settings
from bot.database import crud
from bot.database.session import get_sessionmaker
from bot.services import publisher

logger = logging.getLogger(__name__)


async def _auto_bump_job(bot: Bot) -> None:
    """Поднять объявления, которые давно не поднимались."""
    interval = timedelta(hours=get_settings().bump_interval_hours)
    threshold = datetime.now(timezone.utc) - interval

    async with get_sessionmaker()() as session:
        due = await crud.listings_due_for_bump(session, threshold)
        for listing in due:
            try:
                await publisher.bump_listing(bot, session, listing)
            except Exception:  # noqa: BLE001 - не даём одному сбою остановить пачку
                logger.exception("Не удалось поднять объявление %s", listing.id)

    if due:
        logger.info("Автоподнятие: обработано %d объявлений", len(due))


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _auto_bump_job,
        trigger="interval",
        hours=1,  # проверяем ежечасно, поднимаем только «просроченные»
        args=[bot],
        id="auto_bump",
        replace_existing=True,
    )
    return scheduler
