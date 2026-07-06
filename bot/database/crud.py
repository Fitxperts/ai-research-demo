"""Функции доступа к данным (CRUD) для моделей РиелторБота."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    BotUser,
    Client,
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
