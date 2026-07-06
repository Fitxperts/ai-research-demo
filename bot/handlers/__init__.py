"""Регистрация всех роутеров хендлеров."""
from aiogram import Dispatcher

from bot.handlers import admin, client, owner


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(client.router)
    dp.include_router(owner.router)
    dp.include_router(admin.router)
