"""Функции доступа к данным (CRUD) для моделей предметной области."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    ClientRequest,
    DealType,
    Listing,
    ListingStatus,
    PropertyType,
    User,
    UserRole,
)


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------
async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    *,
    username: str | None = None,
    full_name: str | None = None,
) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    elif username or full_name:
        user.username = username or user.username
        user.full_name = full_name or user.full_name
        await session.commit()
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def set_user_role(session: AsyncSession, telegram_id: int, role: UserRole) -> None:
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(role=role)
    )
    await session.commit()


async def set_user_phone(session: AsyncSession, telegram_id: int, phone: str) -> None:
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(phone=phone)
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Объявления
# ---------------------------------------------------------------------------
async def create_listing(session: AsyncSession, owner_id: int, **fields) -> Listing:
    listing = Listing(owner_id=owner_id, **fields)
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing


async def get_listing(session: AsyncSession, listing_id: int) -> Listing | None:
    return await session.get(Listing, listing_id)


async def list_owner_listings(session: AsyncSession, owner_id: int) -> list[Listing]:
    result = await session.scalars(
        select(Listing).where(Listing.owner_id == owner_id).order_by(Listing.created_at.desc())
    )
    return list(result)


async def list_by_status(session: AsyncSession, status: ListingStatus) -> list[Listing]:
    result = await session.scalars(
        select(Listing).where(Listing.status == status).order_by(Listing.created_at)
    )
    return list(result)


async def set_listing_status(
    session: AsyncSession,
    listing_id: int,
    status: ListingStatus,
    *,
    reject_reason: str | None = None,
) -> Listing | None:
    listing = await session.get(Listing, listing_id)
    if listing is None:
        return None
    listing.status = status
    if reject_reason is not None:
        listing.reject_reason = reject_reason
    if status == ListingStatus.published and listing.published_at is None:
        now = datetime.now(timezone.utc)
        listing.published_at = now
        listing.bumped_at = now
    await session.commit()
    await session.refresh(listing)
    return listing


async def touch_bump(session: AsyncSession, listing_id: int) -> None:
    await session.execute(
        update(Listing)
        .where(Listing.id == listing_id)
        .values(bumped_at=datetime.now(timezone.utc))
    )
    await session.commit()


async def listings_due_for_bump(session: AsyncSession, older_than: datetime) -> list[Listing]:
    """Опубликованные объявления с автоподнятием, которые давно не поднимали."""
    result = await session.scalars(
        select(Listing).where(
            Listing.status == ListingStatus.published,
            Listing.auto_bump.is_(True),
            Listing.bumped_at < older_than,
        )
    )
    return list(result)


# ---------------------------------------------------------------------------
# Заявки клиентов и подбор
# ---------------------------------------------------------------------------
async def create_request(session: AsyncSession, client_id: int, **fields) -> ClientRequest:
    request = ClientRequest(client_id=client_id, **fields)
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


async def search_listings(
    session: AsyncSession,
    *,
    deal_type: DealType | None = None,
    property_type: PropertyType | None = None,
    district: str | None = None,
    budget_min: float | None = None,
    budget_max: float | None = None,
    rooms: int | None = None,
    limit: int = 10,
) -> list[Listing]:
    stmt = select(Listing).where(Listing.status == ListingStatus.published)
    if deal_type is not None:
        stmt = stmt.where(Listing.deal_type == deal_type)
    if property_type is not None:
        stmt = stmt.where(Listing.property_type == property_type)
    if district:
        stmt = stmt.where(Listing.district.ilike(f"%{district}%"))
    if budget_min is not None:
        stmt = stmt.where(Listing.price >= budget_min)
    if budget_max is not None:
        stmt = stmt.where(Listing.price <= budget_max)
    if rooms is not None:
        stmt = stmt.where(Listing.rooms == rooms)
    stmt = stmt.order_by(Listing.bumped_at.desc().nullslast()).limit(limit)
    result = await session.scalars(stmt)
    return list(result)


# ---------------------------------------------------------------------------
# Статистика (для админа)
# ---------------------------------------------------------------------------
async def counts_by_status(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(
        select(Listing.status, func.count()).group_by(Listing.status)
    )
    return {status.value: count for status, count in rows}


async def total_users(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(User)) or 0
