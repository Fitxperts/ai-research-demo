"""Подбор объявлений под заявки клиентов и уведомление о новинках."""
from __future__ import annotations

import logging

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.database.models import ClientRequest, Listing, User
from bot.utils.formatters import format_listing

logger = logging.getLogger(__name__)


async def find_matches(session: AsyncSession, request: ClientRequest, *, limit: int = 10) -> list[Listing]:
    """Найти опубликованные объявления, удовлетворяющие заявке клиента."""
    return await crud.search_listings(
        session,
        deal_type=request.deal_type,
        property_type=request.property_type,
        district=request.district,
        budget_min=float(request.budget_min) if request.budget_min is not None else None,
        budget_max=float(request.budget_max) if request.budget_max is not None else None,
        rooms=request.rooms,
        limit=limit,
    )


async def notify_matching_clients(bot: Bot, session: AsyncSession, listing: Listing) -> None:
    """При публикации нового объявления оповестить клиентов с подходящими заявками."""
    active_requests = await session.scalars(
        select(ClientRequest).where(ClientRequest.is_active.is_(True))
    )
    for request in active_requests:
        if not _matches(request, listing):
            continue
        client = await session.get(User, request.client_id)
        if client is None or client.is_blocked:
            continue
        try:
            await bot.send_message(
                client.telegram_id,
                "🔔 Появился объект по вашему запросу:\n\n" + format_listing(listing),
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001 - клиент мог заблокировать бота
            logger.debug("Не удалось уведомить клиента %s", client.telegram_id)


def _matches(request: ClientRequest, listing: Listing) -> bool:
    if request.deal_type != listing.deal_type:
        return False
    if request.property_type and request.property_type != listing.property_type:
        return False
    if request.district and request.district.lower() not in (listing.district or "").lower():
        return False
    price = float(listing.price)
    if request.budget_min is not None and price < float(request.budget_min):
        return False
    if request.budget_max is not None and price > float(request.budget_max):
        return False
    if request.rooms is not None and listing.rooms != request.rooms:
        return False
    return True
