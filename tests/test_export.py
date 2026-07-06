"""Тесты экспорта в CSV/XLSX и структурного логирования."""
import json
import logging

from bot.database import crud
from bot.database.models import ClientDealType, PropertyKind, PropertyStatus, PropertyType
from bot.logging_setup import JsonFormatter
from bot.services import export


async def test_export_properties_csv(session):
    await crud.create_property(session, property_kind=PropertyKind.apartment, type=PropertyType.sale,
                               status=PropertyStatus.active, district="Центр", rooms=2, price=100, currency="сум")
    data, name = await export.export_properties(session, "csv")
    assert name == "properties.csv"
    text = data.decode("utf-8-sig")
    assert "APT_1001" in text and "Центр" in text
    assert text.splitlines()[0].startswith("id,")


async def test_export_clients_xlsx(session):
    await crud.create_client(session, telegram_id=1, name="Иван", deal_type=ClientDealType.rent, currency="сум")
    data, name = await export.export_clients(session, "xlsx")
    # openpyxl установлен -> xlsx; иначе fallback на csv
    assert name in ("clients.xlsx", "clients.csv")
    assert len(data) > 0


def test_json_formatter():
    rec = logging.LogRecord("t", logging.INFO, __file__, 1, "привет", None, None)
    out = json.loads(JsonFormatter().format(rec))
    assert out["level"] == "INFO" and out["message"] == "привет"
