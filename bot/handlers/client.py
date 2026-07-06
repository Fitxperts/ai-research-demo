"""Хендлеры клиента (заявки на подбор недвижимости).

Заглушка Шага 3: базовая команда /start. Полный сценарий подбора будет
добавлен на последующих шагах.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="client")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Здравствуйте! Это РиелторБот.\n"
        "Скоро здесь появится подбор недвижимости."
    )
