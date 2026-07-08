"""Хендлеры клиента: заявка на подбор недвижимости (FSM, мультиязычно)."""
from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot import i18n
from bot.config import get_settings
from bot.database import crud
from bot.database.models import ClientDealType
from bot.keyboards import client_kb
from bot.services import matcher
from bot.states.client_states import ClientForm
from bot.utils.formatters import format_client_card, format_property_card
from bot.utils.validators import is_valid_phone, parse_date, parse_int, parse_price

logger = logging.getLogger(__name__)
router = Router(name="client")


# ---------------------------------------------------------------------------
# Старт анкеты (вызывается из common-роутера по роли/меню)
# ---------------------------------------------------------------------------
async def begin_client_form(
    message: Message, state: FSMContext, lang: str, *, full_name: str | None = None
) -> None:
    await state.set_state(ClientForm.deal_type)
    await state.update_data(name=full_name or message.from_user.full_name, lang=lang)
    await message.answer(i18n.t("client_intro", lang), reply_markup=client_kb.deal_type_kb(lang))


# ---------------------------------------------------------------------------
# Шаг 1. Тип сделки
# ---------------------------------------------------------------------------
@router.callback_query(ClientForm.deal_type, F.data.startswith(f"{client_kb.PREFIX}:deal:"))
async def deal_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.update_data(deal_type=callback.data.split(":")[2])
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_district(callback.message, state, lang)
    await callback.answer()


@router.message(ClientForm.deal_type, F.text)
async def deal_txt(message: Message, state: FSMContext, lang: str) -> None:
    text = message.text.lower()
    if any(w in text for w in ("аренд", "снять", "сним", "ijara", "rent")):
        await state.update_data(deal_type=ClientDealType.rent.value)
    elif any(w in text for w in ("покуп", "куп", "sotib", "buy")):
        await state.update_data(deal_type=ClientDealType.buy.value)
    else:
        await message.answer(i18n.t("client_pick_deal", lang), reply_markup=client_kb.deal_type_kb(lang))
        return
    await _ask_district(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 2. Район
# ---------------------------------------------------------------------------
async def _ask_district(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ClientForm.district)
    await message.answer(i18n.t("ask_district", lang), reply_markup=client_kb.districts_kb(lang))


@router.callback_query(ClientForm.district, F.data.startswith(f"{client_kb.PREFIX}:dist:"))
async def district_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    district = client_kb.get_district(callback.data.split(":")[2])
    if district is None:
        await callback.message.answer(i18n.t("district_write", lang))
        await callback.answer()
        return
    await state.update_data(district=district)
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_budget(callback.message, state, lang)
    await callback.answer()


@router.message(ClientForm.district, F.text)
async def district_txt(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(district=message.text.strip()[:128])
    await _ask_budget(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 3. Бюджет
# ---------------------------------------------------------------------------
async def _ask_budget(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ClientForm.budget)
    await message.answer(i18n.t("ask_budget", lang))


@router.message(ClientForm.budget, F.text)
async def budget_txt(message: Message, state: FSMContext, lang: str) -> None:
    budget = parse_price(message.text)
    if budget is None:
        await message.answer(i18n.t("budget_bad", lang))
        return
    await state.update_data(budget=budget)
    await _ask_rooms(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 4. Количество комнат
# ---------------------------------------------------------------------------
async def _ask_rooms(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ClientForm.rooms)
    await message.answer(i18n.t("ask_rooms", lang), reply_markup=client_kb.rooms_kb())


@router.callback_query(ClientForm.rooms, F.data.startswith(f"{client_kb.PREFIX}:rooms:"))
async def rooms_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.update_data(rooms=int(callback.data.split(":")[2]))
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_residents(callback.message, state, lang)
    await callback.answer()


@router.message(ClientForm.rooms, F.text)
async def rooms_txt(message: Message, state: FSMContext, lang: str) -> None:
    rooms = parse_int(message.text)
    if rooms is None:
        await message.answer(i18n.t("rooms_bad", lang), reply_markup=client_kb.rooms_kb())
        return
    await state.update_data(rooms=rooms)
    await _ask_residents(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 5. Состав проживающих
# ---------------------------------------------------------------------------
async def _ask_residents(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ClientForm.residents)
    await message.answer(i18n.t("ask_residents", lang), reply_markup=client_kb.residents_kb(lang))


@router.callback_query(ClientForm.residents, F.data.startswith(f"{client_kb.PREFIX}:res:"))
async def residents_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    key = callback.data.split(":")[2]
    msg_key = client_kb.RESIDENTS.get(key)
    await state.update_data(residents=i18n.t(msg_key, lang) if msg_key else key)
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_move_date(callback.message, state, lang)
    await callback.answer()


@router.message(ClientForm.residents, F.text)
async def residents_txt(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(residents=message.text.strip()[:128])
    await _ask_move_date(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 6. Дата заселения
# ---------------------------------------------------------------------------
async def _ask_move_date(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ClientForm.move_date)
    await message.answer(i18n.t("ask_move_date", lang), reply_markup=client_kb.skip_date_kb(lang))


@router.callback_query(ClientForm.move_date, F.data == f"{client_kb.PREFIX}:skipdate")
async def skip_date_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.update_data(move_date=None)
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_phone(callback.message, state, lang)
    await callback.answer()


@router.message(ClientForm.move_date, F.text)
async def move_date_txt(message: Message, state: FSMContext, lang: str) -> None:
    parsed = parse_date(message.text)
    if parsed is None:
        await message.answer(i18n.t("date_bad", lang), reply_markup=client_kb.skip_date_kb(lang))
        return
    await state.update_data(move_date=parsed.isoformat())
    await _ask_phone(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 7. Телефон
# ---------------------------------------------------------------------------
async def _ask_phone(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ClientForm.phone)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=i18n.btn("send_phone", lang), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(i18n.t("ask_phone", lang), reply_markup=kb)


@router.message(ClientForm.phone, F.contact)
async def phone_contact(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(phone=message.contact.phone_number)
    await _show_confirm(message, state, lang)


@router.message(ClientForm.phone, F.text)
async def phone_txt(message: Message, state: FSMContext, lang: str) -> None:
    if not is_valid_phone(message.text):
        await message.answer(i18n.t("phone_bad", lang))
        return
    await state.update_data(phone=message.text.strip())
    await _show_confirm(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 8. Подтверждение
# ---------------------------------------------------------------------------
async def _show_confirm(message: Message, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    preview = _preview_card(data, lang)
    await state.set_state(ClientForm.confirm)
    await message.answer(i18n.t("confirm_title", lang), reply_markup=ReplyKeyboardRemove())
    await message.answer(preview, reply_markup=client_kb.confirm_kb(lang))


@router.callback_query(ClientForm.confirm, F.data == f"{client_kb.PREFIX}:cancel")
async def confirm_cancel(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(i18n.t("request_cancelled", lang))
    await callback.answer()


@router.callback_query(ClientForm.confirm, F.data == f"{client_kb.PREFIX}:confirm")
async def confirm_save(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, lang: str
) -> None:
    data = await state.get_data()
    move_date = data.get("move_date")

    client = await crud.create_client(
        session,
        telegram_id=callback.from_user.id,
        name=data.get("name"),
        phone=data.get("phone"),
        deal_type=ClientDealType(data["deal_type"]),
        district=data.get("district"),
        rooms=data.get("rooms"),
        budget=data.get("budget"),
        currency="сум",
        residents=data.get("residents"),
        move_date=parse_date_iso(move_date),
    )
    await state.clear()

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(i18n.t("request_accepted", lang))
    await callback.answer()

    # Уведомление администратору (на русском — панель оператора)
    await _notify_admins(bot, format_client_card(client))

    # Подходящие объекты
    matches = await matcher.find_for_client(session, client)
    if matches:
        await callback.message.answer(i18n.t("matches_found", lang))
        for prop in matches:
            await callback.message.answer(format_property_card(prop, lang))
    else:
        await callback.message.answer(i18n.t("no_matches", lang))

    # Выбор времени для звонка
    await callback.message.answer(i18n.t("ask_call_time", lang), reply_markup=client_kb.period_kb(lang))


# ---------------------------------------------------------------------------
# Выбор времени звонка (после анкеты, без состояния)
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith(f"{client_kb.PREFIX}:period:"))
async def pick_period(callback: CallbackQuery, lang: str) -> None:
    period = callback.data.split(":")[2]
    period_label = i18n.t(client_kb.PERIODS.get(period, "period_day"), lang)
    await callback.message.edit_text(
        i18n.t("pick_time", lang, period=period_label),
        reply_markup=client_kb.slots_kb(period),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{client_kb.PREFIX}:slot:"))
async def pick_slot(callback: CallbackQuery, bot: Bot, lang: str) -> None:
    slot = callback.data.split(":", 2)[2]
    await callback.message.edit_text(i18n.t("call_scheduled", lang, slot=slot))
    await callback.answer()

    who = escape(callback.from_user.full_name or "")
    username = f" (@{escape(callback.from_user.username)})" if callback.from_user.username else ""
    await _notify_admins(bot, f"📞 Клиент {who}{username} просит звонок в <b>{slot}</b>.")


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def _preview_card(data: dict, lang: str) -> str:
    def esc(value) -> str:
        return escape(str(value)) if value not in (None, "") else "—"

    deal_key = "deal_rent_word" if data.get("deal_type") == "rent" else "deal_buy_word"
    deal = i18n.t(deal_key, lang)
    budget = data.get("budget")
    budget_str = f"{int(budget):,}".replace(",", " ") + " сум" if budget else "—"
    lines = [
        i18n.t("preview_request", lang),
        f"{i18n.t('preview_deal', lang)}: {deal}",
        f"{i18n.t('preview_district', lang)}: {esc(data.get('district'))}",
        f"{i18n.t('preview_budget', lang)}: {budget_str}",
        f"{i18n.t('preview_rooms', lang)}: {esc(data.get('rooms'))}",
        f"{i18n.t('preview_residents', lang)}: {esc(data.get('residents'))}",
        f"{i18n.t('preview_move_in', lang)}: {esc(data.get('move_date'))}",
        f"{i18n.t('preview_phone', lang)}: {esc(data.get('phone'))}",
    ]
    return "\n".join(lines)


def parse_date_iso(value: str | None):
    if not value:
        return None
    import datetime as dt

    try:
        return dt.date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


async def _notify_admins(bot: Bot, text: str) -> None:
    for admin_id in get_settings().admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:  # noqa: BLE001 - админ мог не запускать бота
            logger.debug("Не удалось уведомить админа %s", admin_id)
