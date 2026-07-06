"""Начальная схема РиелторБота (properties, clients, meetings, bot_users).

Базовая ревизия: создаёт все таблицы по текущим моделям. Дальнейшие изменения
схемы делайте отдельными ревизиями (``alembic revision --autogenerate -m "..."``).

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-06
"""
from typing import Sequence, Union

from alembic import op

from bot.database.models import Base

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())
