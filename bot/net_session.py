"""Сетевая сессия aiogram с форсированием IPv4 и жёстким таймаутом коннекта.

Зачем: на многих VPS отсутствует рабочий IPv6-маршрут до api.telegram.org
(OSError [Errno 101] Network is unreachable), а «повисший» TCP-коннект по
умолчанию съедает весь таймаут запроса (~90 сек), из-за чего бот подолгу
«молчит». Здесь мы:

1. форсируем IPv4 (family=AF_INET) — трафик не уходит в мёртвый IPv6;
2. задаём sock_connect=10 — сбойный маршрут отваливается за 10 сек, после
   чего aiogram переподключается (backoff ≤ 5 сек), а не висит минуту-полторы.

sock_read НЕ ограничиваем маленьким значением: long-poll getUpdates держит
соединение без данных до polling_timeout секунд — это нормально.
"""
from __future__ import annotations

import socket
from typing import cast

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType
from aiohttp import ClientError, ClientTimeout

# Максимум на установку TCP-соединения (сек). Дольше — считаем маршрут сбойным.
CONNECT_TIMEOUT = 10


class RobustSession(AiohttpSession):
    """AiohttpSession: только IPv4 + ограниченный таймаут установки соединения."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Трафик к Telegram — только по IPv4 (обход отсутствующего IPv6-маршрута).
        self._connector_init["family"] = socket.AF_INET

    async def make_request(
        self, bot: Bot, method: TelegramMethod[TelegramType], timeout: int | None = None
    ) -> TelegramType:
        session = await self.create_session()

        url = self.api.api_url(token=bot.token, method=method.__api_method__)
        form = self.build_form_data(bot=bot, method=method)

        total = self.timeout if timeout is None else timeout
        # total покрывает весь long-poll, sock_connect быстро рвёт сбойный коннект.
        client_timeout = ClientTimeout(total=total, sock_connect=CONNECT_TIMEOUT)

        try:
            async with session.post(url, data=form, timeout=client_timeout) as resp:
                raw_result = await resp.text()
        except TimeoutError as e:
            raise TelegramNetworkError(method=method, message="Request timeout error") from e
        except ClientError as e:
            raise TelegramNetworkError(method=method, message=f"{type(e).__name__}: {e}") from e

        response = self.check_response(
            bot=bot, method=method, status_code=resp.status, content=raw_result
        )
        return cast(TelegramType, response.result)
