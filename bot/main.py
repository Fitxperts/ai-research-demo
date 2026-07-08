"""Точка входа РиелторБота: инициализация бота, диспетчера и запуск polling."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, ErrorEvent

from bot.config import get_settings
from bot.handlers import register_routers
from bot.logging_setup import init_sentry, setup_logging
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.i18n import LanguageMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.net_session import RobustSession
from bot.services.scheduler import setup_scheduler

_COMMANDS = [
    BotCommand(command="start", description="Начать / меню"),
    BotCommand(command="add", description="Разместить объект"),
    BotCommand(command="cancel", description="Отменить действие"),
    BotCommand(command="help", description="Помощь"),
]

setup_logging()
logger = logging.getLogger(__name__)


def _register_error_handler(dp: Dispatcher, bot: Bot, settings) -> None:
    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        # Сетевые таймауты/сбои связи — временные, aiogram переподключится сам.
        # Логируем как предупреждение, но админов не спамим.
        if isinstance(event.exception, TelegramNetworkError):
            logger.warning("Сетевой сбой Telegram (временный): %s", event.exception)
            return True
        logger.exception("Необработанная ошибка в хендлере", exc_info=event.exception)
        text = f"⚠️ Ошибка бота: {type(event.exception).__name__}: {event.exception}"[:1000]
        for admin_id in settings.admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except Exception:  # noqa: BLE001
                pass
        return True  # ошибка обработана


async def main() -> None:
    settings = get_settings()

    init_sentry()

    # Схема БД применяется миграциями Alembic (alembic upgrade head) до старта бота.

    # Устойчивая к «плавающей» сети сессия: только IPv4 (обход мёртвого IPv6
    # до api.telegram.org) + таймаут установки коннекта 10 сек, чтобы сбойный
    # маршрут отваливался быстро, а не держал бота в «молчании».
    bot = Bot(
        token=settings.bot_token,
        session=RobustSession(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FSM-хранилище состояний в Redis
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)

    # Прокидываем сессию БД во все хендлеры
    dp.update.middleware(DbSessionMiddleware())

    # Определение языка пользователя (после сессии — читает bot_users)
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    # Антифлуд на сообщения и колбэки
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    # Роутеры: клиент, собственник, админ
    register_routers(dp)

    # Глобальный обработчик ошибок
    _register_error_handler(dp, bot, settings)

    # Планировщик фоновых задач
    scheduler = setup_scheduler(bot)
    scheduler.start()

    logger.info("РиелторБот запущен")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_my_commands(_COMMANDS)
        # polling_timeout поменьше → быстрее восстановление после сетевого блипа
        await dp.start_polling(bot, polling_timeout=20)
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
