"""SQLAlchemy-модели предметной области РиелторБота."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    client = "client"
    owner = "owner"
    admin = "admin"


class PropertyType(str, enum.Enum):
    apartment = "apartment"  # квартира
    house = "house"  # дом
    room = "room"  # комната
    commercial = "commercial"  # коммерческая


class DealType(str, enum.Enum):
    sale = "sale"  # продажа
    rent = "rent"  # аренда


class ListingStatus(str, enum.Enum):
    draft = "draft"  # черновик
    pending = "pending"  # на модерации
    published = "published"  # опубликовано
    rejected = "rejected"  # отклонено
    archived = "archived"  # снято/архив


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.client)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listings: Mapped[list["Listing"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    requests: Mapped[list["ClientRequest"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class Listing(Base):
    """Объявление о недвижимости, размещённое собственником."""

    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    property_type: Mapped[PropertyType] = mapped_column(Enum(PropertyType))
    deal_type: Mapped[DealType] = mapped_column(Enum(DealType))
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    rooms: Mapped[int | None] = mapped_column(Integer)
    area: Mapped[float | None] = mapped_column(Numeric(8, 2))
    district: Mapped[str | None] = mapped_column(String(128), index=True)
    address: Mapped[str | None] = mapped_column(String(255))
    photo_file_ids: Mapped[str | None] = mapped_column(Text)  # список file_id через запятую

    status: Mapped[ListingStatus] = mapped_column(Enum(ListingStatus), default=ListingStatus.draft, index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(255))
    channel_message_id: Mapped[int | None] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bumped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_bump: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped["User"] = relationship(back_populates="listings")

    @property
    def photos(self) -> list[str]:
        if not self.photo_file_ids:
            return []
        return [p for p in self.photo_file_ids.split(",") if p]

    def set_photos(self, file_ids: list[str]) -> None:
        self.photo_file_ids = ",".join(file_ids)


class ClientRequest(Base):
    """Заявка на подбор недвижимости от клиента."""

    __tablename__ = "client_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    deal_type: Mapped[DealType] = mapped_column(Enum(DealType))
    property_type: Mapped[PropertyType | None] = mapped_column(Enum(PropertyType))
    district: Mapped[str | None] = mapped_column(String(128))
    budget_min: Mapped[float | None] = mapped_column(Numeric(12, 2))
    budget_max: Mapped[float | None] = mapped_column(Numeric(12, 2))
    rooms: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["User"] = relationship(back_populates="requests")
