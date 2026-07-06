"""Публикация объектов в канал, поднятие и отметка «сдано/продано»."""
from __future__ import annotations

import datetime as dt
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database.models import Property, PropertyStatus, PropertyType
from bot.utils.formatters import format_property_card

logger = logging.getLogger(__name__)


async def publish_property(bot: Bot, session: AsyncSession, prop: Property) -> None:
    """Опубликовать объект в канал, сохранить id поста и сделать активным."""
    channel_id = get_settings().channel_id
    caption = format_property_card(prop)
    photos = prop.photo_list

    if photos:
        message = await bot.send_photo(channel_id, photo=photos[0], caption=caption)
    else:
        message = await bot.send_message(channel_id, caption)

    prop.channel_post_id = message.message_id
    prop.status = PropertyStatus.active
    prop.last_bump = dt.datetime.now()
    await session.commit()
    logger.info("Объект %s опубликован (post=%s)", prop.id, message.message_id)


async def bump_property(bot: Bot, session: AsyncSession, prop: Property) -> None:
    """Переопубликовать объект (поднять) и обновить last_bump."""
    channel_id = get_settings().channel_id
    if prop.channel_post_id:
        try:
            await bot.delete_message(channel_id, prop.channel_post_id)
        except Exception:  # noqa: BLE001 - пост могли удалить вручную
            logger.debug("Старый пост %s не удалён", prop.channel_post_id)
    await publish_property(bot, session, prop)
    logger.info("Объект %s поднят", prop.id)


async def mark_sold(bot: Bot, session: AsyncSession, prop: Property) -> None:
    """Отметить объект сданным/проданным и отредактировать пост в канале."""
    channel_id = get_settings().channel_id
    if prop.type == PropertyType.sale:
        prop.status = PropertyStatus.sold
        label = "ПРОДАНО"
    else:
        prop.status = PropertyStatus.rented
        label = "СДАНО"

    if prop.channel_post_id:
        text = f"❌ <b>{label}</b>\n\n" + format_property_card(prop)
        try:
            if prop.photo_list:
                await bot.edit_message_caption(
                    chat_id=channel_id, message_id=prop.channel_post_id, caption=text
                )
            else:
                await bot.edit_message_text(
                    text, chat_id=channel_id, message_id=prop.channel_post_id
                )
        except Exception:  # noqa: BLE001
            logger.debug("Не удалось отредактировать пост %s", prop.channel_post_id)

    await session.commit()
    logger.info("Объект %s отмечен как %s", prop.id, label)
