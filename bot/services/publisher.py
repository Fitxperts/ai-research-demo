"""Публикация объектов в канал и управление постами.

Функции принимают property_id, берут объект из БД, формируют текст объявления
через AI-сервис (строгий формат, MarkdownV2) и работают с каналом.
"""
from __future__ import annotations

import datetime as dt
import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database import crud
from bot.database.models import Property, PropertyStatus, PropertyType
from bot.services.ai_service import get_ai_service

logger = logging.getLogger(__name__)


def _prop_to_dict(prop: Property) -> dict:
    return {
        "deal_type": prop.type.value if prop.type else None,
        "property_kind": prop.property_kind.value if prop.property_kind else None,
        "address": prop.address,
        "district": prop.district,
        "rooms": prop.rooms,
        "area": prop.area,
        "floor": prop.floor,
        "floors": prop.floors,
        "renovation": prop.renovation,
        "gas": prop.gas,
        "water": prop.water,
        "electricity": prop.electricity,
        "internet": prop.internet,
        "price": prop.price,
        "negotiable": prop.negotiable,
    }


async def _send_post(bot: Bot, channel_id: str, text: str, photos: list[str]) -> int:
    """Отправить пост (альбом/фото/текст) и вернуть id первого сообщения."""
    if len(photos) > 1:
        media = [
            InputMediaPhoto(
                media=fid,
                caption=text if i == 0 else None,
                parse_mode=ParseMode.MARKDOWN_V2 if i == 0 else None,
            )
            for i, fid in enumerate(photos)
        ]
        messages = await bot.send_media_group(channel_id, media)
        return messages[0].message_id
    if len(photos) == 1:
        message = await bot.send_photo(
            channel_id, photos[0], caption=text, parse_mode=ParseMode.MARKDOWN_V2
        )
        return message.message_id
    message = await bot.send_message(channel_id, text, parse_mode=ParseMode.MARKDOWN_V2)
    return message.message_id


async def _edit_post(bot: Bot, channel_id: str, message_id: int, text: str, has_photo: bool) -> None:
    try:
        if has_photo:
            await bot.edit_message_caption(
                chat_id=channel_id, message_id=message_id, caption=text,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        else:
            await bot.edit_message_text(
                text, chat_id=channel_id, message_id=message_id,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
    except Exception:  # noqa: BLE001 - пост могли удалить/изменить вручную
        logger.debug("Не удалось отредактировать пост %s", message_id)


async def publish_property(bot: Bot, session: AsyncSession, property_id: str) -> Property | None:
    """Опубликовать объект в канал (с фото), сохранить post_id, обновить last_bump."""
    prop = await crud.get_property(session, property_id)
    if prop is None:
        return None

    text = get_ai_service().generate_description(_prop_to_dict(prop))
    post_id = await _send_post(bot, get_settings().channel_id, text, prop.photo_list)

    prop.channel_post_id = post_id
    prop.status = PropertyStatus.active
    prop.last_bump = dt.datetime.now()
    await session.commit()
    logger.info("Объект %s опубликован (post=%s)", prop.id, post_id)
    return prop


async def mark_as_rented(bot: Bot, session: AsyncSession, property_id: str) -> Property | None:
    """Отметить объект сданным/проданным: пометить пост и сменить статус."""
    prop = await crud.get_property(session, property_id)
    if prop is None:
        return None

    if prop.type == PropertyType.sale:
        prop.status, label = PropertyStatus.sold, "ПРОДАНО"
    else:
        prop.status, label = PropertyStatus.rented, "СДАНО"

    if prop.channel_post_id:
        text = f"⛔ *{label}*\n\n" + get_ai_service().generate_description(_prop_to_dict(prop))
        await _edit_post(
            bot, get_settings().channel_id, prop.channel_post_id, text, bool(prop.photo_list)
        )

    await session.commit()
    logger.info("Объект %s отмечен как %s", prop.id, label)
    return prop


async def bump_property(bot: Bot, session: AsyncSession, property_id: str) -> Property | None:
    """Поднять объект: пометить старый пост архивным и опубликовать новый."""
    prop = await crud.get_property(session, property_id)
    if prop is None:
        return None

    channel_id = get_settings().channel_id
    text = get_ai_service().generate_description(_prop_to_dict(prop))

    # Помечаем старый пост как неактуальный (архив)
    if prop.channel_post_id:
        archived_text = "🗄 *Эълон янгиланди \\(пастга қаранг\\)*\n\n" + text
        await _edit_post(bot, channel_id, prop.channel_post_id, archived_text, bool(prop.photo_list))

    # Публикуем свежий пост
    post_id = await _send_post(bot, channel_id, text, prop.photo_list)
    prop.channel_post_id = post_id
    prop.last_bump = dt.datetime.now()
    await session.commit()
    logger.info("Объект %s поднят (новый post=%s)", prop.id, post_id)
    return prop
