"""Функции доступа к данным (CRUD) для моделей РиелторБота."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    BotUser,
    Client,
    ClientStatus,
    Meeting,
    MeetingStatus,
    Property,
    PropertyKind,
    PropertyStatus,
    PropertyType,
    UserRole,
)

# Префикс идентификатора объекта по типу недвижимости (APT_1001, HSE_1001, ...)
_KIND_PREFIX = {
    PropertyKind.apartment: "APT",
    PropertyKind.house: "HSE",
    PropertyKind.land: "LND",
    PropertyKind.commercial: "COM",
}


# ---------------------------------------------------------------------------
# Пользователи бота
# ---------------------------------------------------------------------------
async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    *,
    username: str | None = None,
    full_name: str | None = None,
    is_admin: bool = False,
) -> BotUser:
    user = await session.get(BotUser, telegram_id)
    if user is None:
        user = BotUser(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=UserRole.admin if is_admin else UserRole.client,
        )
        session.add(user)
        await session.commit()
        return user

    changed = False
    if username and user.username != username:
        user.username, changed = username, True
    if full_name and user.full_name != full_name:
        user.full_name, changed = full_name, True
    if is_admin and user.role != UserRole.admin:
        user.role, changed = UserRole.admin, True
    if changed:
        await session.commit()
    return user


async def set_user_role(session: AsyncSession, telegram_id: int, role: UserRole) -> None:
    user = await session.get(BotUser, telegram_id)
    if user:
        user.role = role
        await session.commit()


# ---------------------------------------------------------------------------
# Генерация строковых идентификаторов (APT_1001, CLT_001, MTG_001)
# ---------------------------------------------------------------------------
async def _next_id(session: AsyncSession, model, prefix: str, *, start: int = 1, pad: int = 3) -> str:
    ids = await session.scalars(select(model.id).where(model.id.like(f"{prefix}_%")))
    max_n = start - 1
    for rid in ids:
        suffix = rid.rsplit("_", 1)[-1]
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f"{prefix}_{max_n + 1:0{pad}d}"


# ---------------------------------------------------------------------------
# Клиенты
# ---------------------------------------------------------------------------
async def create_client(session: AsyncSession, **fields) -> Client:
    client_id = await _next_id(session, Client, "CLT", start=1, pad=3)
    client = Client(id=client_id, **fields)
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def has_client(session: AsyncSession, telegram_id: int) -> bool:
    count = await session.scalar(
        select(func.count()).select_from(Client).where(Client.telegram_id == telegram_id)
    )
    return bool(count)


# ---------------------------------------------------------------------------
# Объекты недвижимости
# ---------------------------------------------------------------------------
async def create_property(session: AsyncSession, *, property_kind: PropertyKind, **fields) -> Property:
    prefix = _KIND_PREFIX.get(property_kind, "APT")
    prop_id = await _next_id(session, Property, prefix, start=1001, pad=4)
    prop = Property(id=prop_id, property_kind=property_kind, **fields)
    session.add(prop)
    await session.commit()
    await session.refresh(prop)
    return prop


async def get_property(session: AsyncSession, property_id: str) -> Property | None:
    return await session.get(Property, property_id)


async def find_duplicate(
    session: AsyncSession, *, phone: str | None, address: str | None
) -> Property | None:
    """Найти дубль по телефону собственника и адресу."""
    if not phone or not address:
        return None
    return await session.scalar(
        select(Property)
        .where(Property.owner_phone == phone, Property.address.ilike(f"%{address}%"))
        .limit(1)
    )


async def set_property_status(
    session: AsyncSession, property_id: str, status: PropertyStatus
) -> Property | None:
    prop = await session.get(Property, property_id)
    if prop is None:
        return None
    prop.status = status
    await session.commit()
    await session.refresh(prop)
    return prop


async def search_properties(
    session: AsyncSession,
    *,
    prop_type: PropertyType | None = None,
    district: str | None = None,
    rooms: int | None = None,
    max_price: float | None = None,
    limit: int = 5,
) -> list[Property]:
    stmt = select(Property).where(Property.status == PropertyStatus.active)
    if prop_type is not None:
        stmt = stmt.where(Property.type == prop_type)
    if district:
        stmt = stmt.where(Property.district.ilike(f"%{district}%"))
    if rooms is not None:
        stmt = stmt.where(Property.rooms == rooms)
    if max_price is not None:
        stmt = stmt.where(Property.price <= max_price)
    stmt = stmt.order_by(Property.last_bump.desc().nullslast(), Property.created_at.desc()).limit(limit)
    result = await session.scalars(stmt)
    return list(result)


async def list_properties(
    session: AsyncSession,
    *,
    statuses: list[PropertyStatus] | None = None,
    limit: int = 15,
) -> list[Property]:
    stmt = select(Property)
    if statuses:
        stmt = stmt.where(Property.status.in_(statuses))
    stmt = stmt.order_by(Property.created_at.desc()).limit(limit)
    return list(await session.scalars(stmt))


async def properties_due_for_bump(session: AsyncSession, older_than: dt.datetime) -> list[Property]:
    stmt = select(Property).where(
        Property.status == PropertyStatus.active,
        (Property.last_bump.is_(None)) | (Property.last_bump < older_than),
    )
    return list(await session.scalars(stmt))


# ---------------------------------------------------------------------------
# Клиенты (CRM)
# ---------------------------------------------------------------------------
async def list_clients(session: AsyncSession, *, limit: int = 20) -> list[Client]:
    stmt = select(Client).order_by(Client.created_at.desc()).limit(limit)
    return list(await session.scalars(stmt))


async def get_client(session: AsyncSession, client_id: str) -> Client | None:
    return await session.get(Client, client_id)


async def set_client_status(
    session: AsyncSession, client_id: str, status: ClientStatus
) -> Client | None:
    client = await session.get(Client, client_id)
    if client is None:
        return None
    client.status = status
    await session.commit()
    await session.refresh(client)
    return client


# ---------------------------------------------------------------------------
# Встречи
# ---------------------------------------------------------------------------
async def create_meeting(
    session: AsyncSession, *, client_id: str, property_id: str, when: dt.datetime
) -> Meeting:
    meeting_id = await _next_id(session, Meeting, "MTG", start=1, pad=3)
    meeting = Meeting(id=meeting_id, client_id=client_id, property_id=property_id, datetime=when)
    session.add(meeting)
    await session.commit()
    await session.refresh(meeting)
    return meeting


async def upcoming_meetings(session: AsyncSession, *, limit: int = 20) -> list[Meeting]:
    today = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = (
        select(Meeting)
        .where(Meeting.datetime >= today, Meeting.status == MeetingStatus.planned)
        .order_by(Meeting.datetime)
        .limit(limit)
    )
    return list(await session.scalars(stmt))


async def meetings_needing_reminder(session: AsyncSession) -> list[Meeting]:
    """Запланированные будущие встречи (для напоминаний)."""
    now = dt.datetime.now()
    stmt = select(Meeting).where(
        Meeting.status == MeetingStatus.planned, Meeting.datetime >= now
    )
    return list(await session.scalars(stmt))


# ---------------------------------------------------------------------------
# Статистика
# ---------------------------------------------------------------------------
async def count_properties_by_status(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(
        select(Property.status, func.count()).group_by(Property.status)
    )
    return {status.value: count for status, count in rows}


async def count_clients_by_status(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(
        select(Client.status, func.count()).group_by(Client.status)
    )
    return {status.value: count for status, count in rows}
