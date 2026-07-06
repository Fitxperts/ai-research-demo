"""Публикация объявлений в канал и их поднятие."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database import crud
from bot.database.models import Listing
from bot.utils.formatters import format_listing

logger = logging.getLogger(__name__)


async def publish_listing(bot: Bot, session: AsyncSession, listing: Listing) -> None:
    """Опубликовать объявление в канал и сохранить id сообщения."""
    channel_id = get_settings().channel_id
    caption = format_listing(listing)
    photos = listing.photos

    if photos:
        message = await bot.send_photo(
            channel_id, photo=photos[0], caption=caption, parse_mode="HTML"
        )
    else:
        message = await bot.send_message(channel_id, caption, parse_mode="HTML")

    listing.channel_message_id = message.message_id
    await session.commit()
    logger.info("Объявление %s опубликовано (msg=%s)", listing.id, message.message_id)


async def bump_listing(bot: Bot, session: AsyncSession, listing: Listing) -> None:
    """Поднять объявление: повторно опубликовать и обновить bumped_at."""
    channel_id = get_settings().channel_id

    # Удаляем предыдущее сообщение, если оно было.
    if listing.channel_message_id:
        try:
            await bot.delete_message(channel_id, listing.channel_message_id)
        except Exception:  # noqa: BLE001 - сообщение могли удалить вручную
            logger.debug("Не удалось удалить старое сообщение %s", listing.channel_message_id)

    await publish_listing(bot, session, listing)
    await crud.touch_bump(session, listing.id)
    logger.info("Объявление %s поднято", listing.id)


def build_media_group(listing: Listing) -> list[InputMediaPhoto]:
    """Собрать медиагруппу из фотографий объявления (для предпросмотра)."""
    caption = format_listing(listing)
    media: list[InputMediaPhoto] = []
    for index, file_id in enumerate(listing.photos):
        media.append(
            InputMediaPhoto(
                media=file_id,
                caption=caption if index == 0 else None,
                parse_mode="HTML" if index == 0 else None,
            )
        )
    return media
