"""Добавляет колонку bot_users.language (uz | ru | en).

Идемпотентно: базовая ревизия 0001 создаёт таблицы через
``Base.metadata.create_all`` по текущим моделям, поэтому на СВЕЖЕЙ БД колонка
уже присутствует, а на СУЩЕСТВУЮЩЕЙ (обновление) — нет. Проверяем наличие
колонки и добавляем только при отсутствии.

Revision ID: 0002_add_language
Revises: 0001_initial
Create Date: 2026-07-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_language"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("bot_users", "language"):
        op.add_column("bot_users", sa.Column("language", sa.String(length=2), nullable=True))


def downgrade() -> None:
    if _has_column("bot_users", "language"):
        op.drop_column("bot_users", "language")
