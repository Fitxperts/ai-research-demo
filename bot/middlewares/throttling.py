"""Простая защита от флуда: ограничение частоты сообщений на пользователя.

Медиа (фото/видео, в т.ч. альбомы) не троттлятся — иначе терялись бы части
альбома, приходящие пачкой.
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 0.5) -> None:
        self._rate = rate
        self._last: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Не троттлим медиа — фото/видео альбома приходят пачкой
        if isinstance(event, Message) and (event.media_group_id or event.photo or event.video):
            return await handler(event, data)

        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            if now - self._last.get(user.id, 0.0) < self._rate:
                return None  # слишком часто — игнорируем
            self._last[user.id] = now

        return await handler(event, data)
