"""Регистрация всех роутеров хендлеров."""
from aiogram import Dispatcher

from bot.handlers import admin, client, common, owner


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(owner.router)
    dp.include_router(client.router)
