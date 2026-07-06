"""Хендлеры клиента: заявка на подбор недвижимости (FSM)."""
from __future__ import annotations

import logging

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
async def begin_client_form(message: Message, state: FSMContext, *, full_name: str | None = None) -> None:
    await state.set_state(ClientForm.deal_type)
    # full_name передаётся у реального пользователя (в callback message.from_user == бот)
    await state.update_data(name=full_name or message.from_user.full_name)
    await message.answer(
        "Помогу подобрать недвижимость в Фергане.\n"
        "Вы хотите <b>арендовать</b> или <b>купить</b>?",
        reply_markup=client_kb.deal_type_kb(),
    )


# ---------------------------------------------------------------------------
# Шаг 1. Тип сделки
# ---------------------------------------------------------------------------
@router.callback_query(ClientForm.deal_type, F.data.startswith(f"{client_kb.PREFIX}:deal:"))
async def deal_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(deal_type=callback.data.split(":")[2])
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_district(callback.message, state)
    await callback.answer()


@router.message(ClientForm.deal_type, F.text)
async def deal_txt(message: Message, state: FSMContext) -> None:
    text = message.text.lower()
    if any(w in text for w in ("аренд", "снять", "сним")):
        await state.update_data(deal_type=ClientDealType.rent.value)
    elif any(w in text for w in ("покуп", "куп")):
        await state.update_data(deal_type=ClientDealType.buy.value)
    else:
        await message.answer("Выберите: аренда или покупка.", reply_markup=client_kb.deal_type_kb())
        return
    await _ask_district(message, state)


# ---------------------------------------------------------------------------
# Шаг 2. Район
# ---------------------------------------------------------------------------
async def _ask_district(message: Message, state: FSMContext) -> None:
    await state.set_state(ClientForm.district)
    await message.answer("📍 В каком районе ищете? Выберите или напишите свой:", reply_markup=client_kb.districts_kb())


@router.callback_query(ClientForm.district, F.data.startswith(f"{client_kb.PREFIX}:dist:"))
async def district_cb(callback: CallbackQuery, state: FSMContext) -> None:
    district = client_kb.get_district(callback.data.split(":")[2])
    if district is None:
        await callback.message.answer("Напишите название района текстом:")
        await callback.answer()
        return
    await state.update_data(district=district)
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_budget(callback.message, state)
    await callback.answer()


@router.message(ClientForm.district, F.text)
async def district_txt(message: Message, state: FSMContext) -> None:
    await state.update_data(district=message.text.strip()[:128])
    await _ask_budget(message, state)


# ---------------------------------------------------------------------------
# Шаг 3. Бюджет
# ---------------------------------------------------------------------------
async def _ask_budget(message: Message, state: FSMContext) -> None:
    await state.set_state(ClientForm.budget)
    await message.answer("💰 Какой у вас бюджет? Напишите сумму (например, 3000000):")


@router.message(ClientForm.budget, F.text)
async def budget_txt(message: Message, state: FSMContext) -> None:
    budget = parse_price(message.text)
    if budget is None:
        await message.answer("Не понял сумму. Введите число, например 3000000.")
        return
    await state.update_data(budget=budget)
    await _ask_rooms(message, state)


# ---------------------------------------------------------------------------
# Шаг 4. Количество комнат
# ---------------------------------------------------------------------------
async def _ask_rooms(message: Message, state: FSMContext) -> None:
    await state.set_state(ClientForm.rooms)
    await message.answer("🛏 Сколько комнат нужно?", reply_markup=client_kb.rooms_kb())


@router.callback_query(ClientForm.rooms, F.data.startswith(f"{client_kb.PREFIX}:rooms:"))
async def rooms_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(rooms=int(callback.data.split(":")[2]))
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_residents(callback.message, state)
    await callback.answer()


@router.message(ClientForm.rooms, F.text)
async def rooms_txt(message: Message, state: FSMContext) -> None:
    rooms = parse_int(message.text)
    if rooms is None:
        await message.answer("Введите число комнат или выберите кнопкой.", reply_markup=client_kb.rooms_kb())
        return
    await state.update_data(rooms=rooms)
    await _ask_residents(message, state)


# ---------------------------------------------------------------------------
# Шаг 5. Состав проживающих
# ---------------------------------------------------------------------------
async def _ask_residents(message: Message, state: FSMContext) -> None:
    await state.set_state(ClientForm.residents)
    await message.answer("👨‍👩‍👧 Кто будет жить?", reply_markup=client_kb.residents_kb())


@router.callback_query(ClientForm.residents, F.data.startswith(f"{client_kb.PREFIX}:res:"))
async def residents_cb(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":")[2]
    await state.update_data(residents=client_kb.RESIDENTS.get(key, key))
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_move_date(callback.message, state)
    await callback.answer()


@router.message(ClientForm.residents, F.text)
async def residents_txt(message: Message, state: FSMContext) -> None:
    await state.update_data(residents=message.text.strip()[:128])
    await _ask_move_date(message, state)


# ---------------------------------------------------------------------------
# Шаг 6. Дата заселения
# ---------------------------------------------------------------------------
async def _ask_move_date(message: Message, state: FSMContext) -> None:
    await state.set_state(ClientForm.move_date)
    await message.answer(
        "📅 Когда планируете заселение? (ДД.ММ.ГГГГ)", reply_markup=client_kb.skip_date_kb()
    )


@router.callback_query(ClientForm.move_date, F.data == f"{client_kb.PREFIX}:skipdate")
async def skip_date_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(move_date=None)
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_phone(callback.message, state)
    await callback.answer()


@router.message(ClientForm.move_date, F.text)
async def move_date_txt(message: Message, state: FSMContext) -> None:
    parsed = parse_date(message.text)
    if parsed is None:
        await message.answer(
            "Не понял дату. Формат ДД.ММ.ГГГГ или нажмите «Пропустить».",
            reply_markup=client_kb.skip_date_kb(),
        )
        return
    await state.update_data(move_date=parsed.isoformat())
    await _ask_phone(message, state)


# ---------------------------------------------------------------------------
# Шаг 7. Телефон
# ---------------------------------------------------------------------------
async def _ask_phone(message: Message, state: FSMContext) -> None:
    await state.set_state(ClientForm.phone)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer("📞 Оставьте телефон для связи (или отправьте номер кнопкой):", reply_markup=kb)


@router.message(ClientForm.phone, F.contact)
async def phone_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.contact.phone_number)
    await _show_confirm(message, state)


@router.message(ClientForm.phone, F.text)
async def phone_txt(message: Message, state: FSMContext) -> None:
    if not is_valid_phone(message.text):
        await message.answer("Похоже, номер некорректный. Введите ещё раз, например +998901234567.")
        return
    await state.update_data(phone=message.text.strip())
    await _show_confirm(message, state)


# ---------------------------------------------------------------------------
# Шаг 8. Подтверждение
# ---------------------------------------------------------------------------
async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    preview = _preview_card(data)
    await state.set_state(ClientForm.confirm)
    await message.answer("Проверьте заявку:", reply_markup=ReplyKeyboardRemove())
    await message.answer(preview, reply_markup=client_kb.confirm_kb())


@router.callback_query(ClientForm.confirm, F.data == f"{client_kb.PREFIX}:cancel")
async def confirm_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Заявка отменена. Нажмите /start, чтобы начать заново.")
    await callback.answer()


@router.callback_query(ClientForm.confirm, F.data == f"{client_kb.PREFIX}:confirm")
async def confirm_save(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
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
    await callback.message.answer("✅ Заявка принята! Риелтор скоро свяжется с вами.")
    await callback.answer()

    # Уведомление администратору
    await _notify_admins(bot, format_client_card(client))

    # Подходящие объекты
    matches = await matcher.find_for_client(session, client)
    if matches:
        await callback.message.answer("🔎 Нашлись подходящие варианты:")
        for prop in matches:
            await callback.message.answer(format_property_card(prop))
    else:
        await callback.message.answer("Пока подходящих объектов нет — сообщим, как появятся.")

    # Выбор времени для звонка
    await callback.message.answer(
        "🕐 Когда вам удобно, чтобы риелтор позвонил?", reply_markup=client_kb.period_kb()
    )


# ---------------------------------------------------------------------------
# Выбор времени звонка (после анкеты, без состояния)
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith(f"{client_kb.PREFIX}:period:"))
async def pick_period(callback: CallbackQuery) -> None:
    period = callback.data.split(":")[2]
    await callback.message.edit_text(
        f"🕐 {client_kb.PERIOD_LABELS.get(period, period)} — выберите время:",
        reply_markup=client_kb.slots_kb(period),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{client_kb.PREFIX}:slot:"))
async def pick_slot(callback: CallbackQuery, bot: Bot) -> None:
    slot = callback.data.split(":", 2)[2]
    await callback.message.edit_text(f"✅ Отлично! Риелтор позвонит вам в {slot}.")
    await callback.answer()

    who = callback.from_user.full_name
    username = f" (@{callback.from_user.username})" if callback.from_user.username else ""
    await _notify_admins(bot, f"📞 Клиент {who}{username} просит звонок в <b>{slot}</b>.")


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def _preview_card(data: dict) -> str:
    deal = {"rent": "Аренда", "buy": "Покупка"}.get(data.get("deal_type"), "—")
    budget = data.get("budget")
    budget_str = f"{int(budget):,}".replace(",", " ") + " сум" if budget else "—"
    lines = [
        "<b>Ваша заявка</b>",
        f"Сделка: {deal}",
        f"Район: {data.get('district') or '—'}",
        f"Бюджет: {budget_str}",
        f"Комнат: {data.get('rooms') or '—'}",
        f"Кто будет жить: {data.get('residents') or '—'}",
        f"Заселение: {data.get('move_date') or '—'}",
        f"Телефон: {data.get('phone') or '—'}",
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
