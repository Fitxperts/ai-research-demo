"""Отказоустойчивая сессия aiogram для нестабильной сети VPS.

Проблема: на VPS связь до api.telegram.org «плавает» (теряет пакеты). Из-за
этого:
- запросы уходят в мёртвый IPv6-маршрут (ENETUNREACH);
- «повисший» коннект держит запрос до таймаута;
- САМОЕ ГЛАВНОЕ: ответ бота (sendMessage/editMessage/answerCallbackQuery)
  при сетевом сбое терялся безвозвратно — aiogram не повторяет отправку, и
  пользователь не видел ответа («бот отвечает через раз»).

Решение (в одном месте — make_request, через которое идут ВСЕ вызовы API):
1. family=AF_INET — только IPv4 (обход сломанного IPv6);
2. sock_connect=CONNECT_TIMEOUT — сбойный коннект рвётся быстро;
3. короткий total на обычные вызовы — зависание не длится минуту;
4. АВТОПОВТОР на сетевых ошибках для всех методов, КРОМЕ getUpdates
   (его повторяет сам polling-цикл). Ответы больше не теряются.
"""
from __future__ import annotations

import asyncio
import logging
import socket
from typing import cast

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType
from aiohttp import ClientError, ClientTimeout

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10       # максимум на установку TCP-соединения (сек)
REQUEST_TIMEOUT = 30       # максимум на обычный вызов API (сек)
SEND_RETRIES = 4           # попыток отправки при сетевом сбое (кроме getUpdates)


class RobustSession(AiohttpSession):
    """IPv4 + жёсткие таймауты + автоповтор отправки при сетевых сбоях."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Только IPv4 (обход отсутствующего IPv6-маршрута до Telegram).
        self._connector_init["family"] = socket.AF_INET
        # Базовый таймаут обычных вызовов (getUpdates получает свой, больший).
        self.timeout = REQUEST_TIMEOUT

    async def _request_once(
        self, bot: Bot, method: TelegramMethod[TelegramType], client_timeout: ClientTimeout
    ) -> TelegramType:
        session = await self.create_session()
        url = self.api.api_url(token=bot.token, method=method.__api_method__)
        form = self.build_form_data(bot=bot, method=method)
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

    async def make_request(
        self, bot: Bot, method: TelegramMethod[TelegramType], timeout: int | None = None
    ) -> TelegramType:
        is_polling = method.__api_method__ == "getUpdates"
        total = self.timeout if timeout is None else timeout
        # sock_connect быстро рвёт сбойный коннект; sock_read покрывает long-poll.
        client_timeout = ClientTimeout(total=total, sock_connect=CONNECT_TIMEOUT, sock_read=total)

        # getUpdates повторяет сам polling-цикл aiogram — здесь не дублируем.
        attempts = 1 if is_polling else SEND_RETRIES
        last_exc: TelegramNetworkError | None = None
        for i in range(attempts):
            try:
                return await self._request_once(bot, method, client_timeout)
            except TelegramNetworkError as exc:
                last_exc = exc
                if i < attempts - 1:
                    delay = min(0.5 * 2**i, 3.0)
                    logger.warning(
                        "Сетевой сбой при %s (попытка %d/%d), повтор через %.1fс",
                        method.__api_method__, i + 1, attempts, delay,
                    )
                    await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc
