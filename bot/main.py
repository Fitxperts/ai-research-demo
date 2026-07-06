"""Точка входа РиелторБота: инициализация бота, диспетчера и запуск polling."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from bot.config import get_settings
from bot.handlers import register_routers
from bot.middlewares.db import DbSessionMiddleware
from bot.services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FSM-хранилище состояний в Redis
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)

    # Прокидываем сессию БД во все хендлеры
    dp.update.middleware(DbSessionMiddleware())

    # Роутеры: клиент, собственник, админ
    register_routers(dp)

    # Планировщик фоновых задач
    scheduler = setup_scheduler(bot)
    scheduler.start()

    logger.info("РиелторБот запущен")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await storage.close()
        await bot.session.close()
        logger.info("РиелторБот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Завершение работы по сигналу")
