"""Регистрация всех роутеров хендлеров.

Порядок важен: админский роутер идёт первым (он ограничен фильтром IsAdmin,
поэтому не мешает обычным пользователям), затем собственник и клиент.
"""
from aiogram import Dispatcher

from bot.handlers import admin, client, owner


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(admin.router)
    dp.include_router(owner.router)
    dp.include_router(client.router)
