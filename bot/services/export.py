"""Экспорт объектов и клиентов в CSV/XLSX для администратора."""
from __future__ import annotations

import csv
import io

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.database.models import Client, Property

_PROPERTY_HEADERS = [
    "id", "тип", "статус", "вид", "район", "адрес", "комнат", "площадь",
    "цена", "валюта", "телефон", "создан",
]
_CLIENT_HEADERS = [
    "id", "имя", "телефон", "сделка", "район", "комнат", "бюджет", "валюта",
    "статус", "создан",
]


def _val(x) -> str:
    if x is None:
        return ""
    return getattr(x, "value", x) if not hasattr(x, "isoformat") else x.strftime("%Y-%m-%d %H:%M")


def _property_row(p: Property) -> list:
    return [
        p.id, _val(p.type), _val(p.status), _val(p.property_kind), p.district or "",
        p.address or "", p.rooms or "", p.area or "", p.price or "", p.currency or "",
        p.owner_phone or "", _val(p.created_at),
    ]


def _client_row(c: Client) -> list:
    return [
        c.id, c.name or "", c.phone or "", _val(c.deal_type), c.district or "",
        c.rooms or "", c.budget or "", c.currency or "", _val(c.status), _val(c.created_at),
    ]


def _to_csv(headers: list[str], rows: list[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    # BOM, чтобы Excel корректно открыл кириллицу
    return buf.getvalue().encode("utf-8-sig")


def _to_xlsx(sheet: str, headers: list[str], rows: list[list]) -> bytes | None:
    try:
        from openpyxl import Workbook
    except Exception:  # noqa: BLE001 - openpyxl не установлен
        return None
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def export_properties(session: AsyncSession, fmt: str) -> tuple[bytes, str]:
    rows = [_property_row(p) for p in await crud.all_properties(session)]
    if fmt == "xlsx":
        data = _to_xlsx("Объекты", _PROPERTY_HEADERS, rows)
        if data is not None:
            return data, "properties.xlsx"
    return _to_csv(_PROPERTY_HEADERS, rows), "properties.csv"


async def export_clients(session: AsyncSession, fmt: str) -> tuple[bytes, str]:
    rows = [_client_row(c) for c in await crud.all_clients(session)]
    if fmt == "xlsx":
        data = _to_xlsx("Клиенты", _CLIENT_HEADERS, rows)
        if data is not None:
            return data, "clients.xlsx"
    return _to_csv(_CLIENT_HEADERS, rows), "clients.csv"
