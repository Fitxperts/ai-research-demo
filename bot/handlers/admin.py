"""Хендлеры администратора: объекты, клиенты, встречи, публикации, статистика."""
from __future__ import annotations

import datetime as dt
import logging

from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import BUMP_INTERVAL_DAYS, get_settings
from bot.database import crud
from bot.database.models import (
    ClientStatus,
    MeetingStatus,
    Property,
    PropertyStatus,
)
from bot.handlers.owner import begin_property_form
from bot.keyboards import admin_kb
from bot.services import export, matcher, publisher
from bot.states.admin_states import EditProperty, ScheduleMeeting
from bot.utils import timeutils
from bot.utils.formatters import (
    PROPERTY_STATUS_LABELS,
    format_client_short,
    format_meeting,
    format_property_card,
)
from bot.utils.validators import parse_int, parse_price

logger = logging.getLogger(__name__)
P = admin_kb.PREFIX


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return bool(user and get_settings().is_admin(user.id))


router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_STATUS_FILTER = {
    "all": None,
    "active": [PropertyStatus.active],
    "pending": [PropertyStatus.pending],
    "sold": [PropertyStatus.rented, PropertyStatus.sold],
}


# ---------------------------------------------------------------------------
# Меню
# ---------------------------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await crud.get_or_create_user(
        session,
        message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        is_admin=True,
    )
    await message.answer("🛠 Панель администратора", reply_markup=admin_kb.main_menu())


@router.message(F.text == "➕ Новый объект")
async def new_object(message: Message, state: FSMContext) -> None:
    await begin_property_form(message, state, "ru")  # админ-панель на русском


# ---------------------------------------------------------------------------
# Раздел: Объекты
# ---------------------------------------------------------------------------
@router.message(F.text == "📋 Объекты")
async def objects_menu(message: Message) -> None:
    await message.answer("📋 Объекты — выберите фильтр:", reply_markup=admin_kb.object_filters_kb())


PAGE = 5  # объектов/клиентов на страницу


@router.callback_query(F.data.startswith(f"{P}:objs:"))
async def objects_list(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    parts = callback.data.split(":")
    key = parts[2]
    offset = int(parts[3]) if len(parts) > 3 else 0
    props = await crud.list_properties(session, statuses=_STATUS_FILTER.get(key), limit=PAGE, offset=offset)
    await callback.answer()
    if not props:
        await callback.message.answer("Больше объектов нет." if offset else "Ничего не найдено.")
        return
    for prop in props:
        await _show_property(callback.message, prop, admin_kb.object_actions_kb(prop))
    if len(props) == PAGE:
        await callback.message.answer(
            "…", reply_markup=admin_kb.more_kb(f"{P}:objs:{key}:{offset + PAGE}")
        )


async def _show_property(target: Message, prop: Property, kb) -> None:
    status = PROPERTY_STATUS_LABELS.get(prop.status, prop.status.value)
    text = f"[{status}] " + format_property_card(prop)
    photos = prop.photo_list
    if photos:
        await target.answer_photo(photos[0], caption=text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


# --- действия с объектом ---
@router.callback_query(F.data.startswith(f"{P}:approve:"))
async def approve(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    property_id = callback.data.split(":")[2]
    try:
        prop = await publisher.publish_property(bot, session, property_id)
    except Exception:  # noqa: BLE001 - ошибка отправки в канал не должна «вешать» callback
        logger.exception("Ошибка публикации объекта %s", property_id)
        await callback.answer("Ошибка публикации. Проверьте канал/права бота.", show_alert=True)
        return
    if prop is None:
        await callback.answer("Объект не найден", show_alert=True)
        return
    await _clear_markup(callback)
    await callback.answer("Опубликовано ✅", show_alert=True)
    await _notify_owner(bot, prop, f"✅ Ваш объект {prop.id} опубликован!")


@router.callback_query(F.data.startswith(f"{P}:hold:"))
async def hold(callback: CallbackQuery, session: AsyncSession) -> None:
    await crud.set_property_status(session, callback.data.split(":")[2], PropertyStatus.pending)
    await _clear_markup(callback)
    await callback.answer("Отложено ⏸", show_alert=True)


@router.callback_query(F.data.startswith(f"{P}:sold:"))
async def sold(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    await publisher.mark_as_rented(bot, session, callback.data.split(":")[2])
    await _clear_markup(callback)
    await callback.answer("Отмечено как сдано/продано ⛔", show_alert=True)


@router.callback_query(F.data.startswith(f"{P}:bump:"))
async def bump(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    await publisher.bump_property(bot, session, callback.data.split(":")[2])
    await callback.answer("Поднято 📢", show_alert=True)


@router.callback_query(F.data.startswith(f"{P}:arch:"))
async def archive(callback: CallbackQuery, session: AsyncSession) -> None:
    await crud.set_property_status(session, callback.data.split(":")[2], PropertyStatus.archived)
    await _clear_markup(callback)
    await callback.answer("В архиве 🗄", show_alert=True)


# --- редактирование объекта ---
@router.callback_query(F.data.startswith(f"{P}:edit:"))
async def edit_start(callback: CallbackQuery) -> None:
    property_id = callback.data.split(":")[2]
    await callback.message.answer(
        f"✏️ Редактирование {property_id}. Что изменить?",
        reply_markup=admin_kb.edit_fields_kb(property_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{P}:efield:"))
async def edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, property_id, field = callback.data.split(":")
    await state.update_data(property_id=property_id, field=field)
    await state.set_state(EditProperty.value)
    label = admin_kb.EDIT_FIELDS.get(field, field)
    await callback.message.answer(f"Введите новое значение — {label}:")
    await callback.answer()


@router.message(EditProperty.value, F.text)
async def edit_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    field, property_id = data["field"], data["property_id"]
    prop = await crud.get_property(session, property_id)
    if prop is None:
        await state.clear()
        await message.answer("Объект не найден.")
        return

    if field in ("price", "area"):
        value = parse_price(message.text)
        if value is None:
            await message.answer("Введите число.")
            return
    elif field == "rooms":
        value = parse_int(message.text)
        if value is None:
            await message.answer("Введите целое число.")
            return
    else:
        value = message.text.strip()

    setattr(prop, field, value)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Поле «{admin_kb.EDIT_FIELDS.get(field, field)}» обновлено.")


# ---------------------------------------------------------------------------
# Раздел: Клиенты
# ---------------------------------------------------------------------------
@router.message(F.text == "👥 Клиенты")
async def clients_list(message: Message, session: AsyncSession) -> None:
    await _show_clients_page(message, session, offset=0)


@router.callback_query(F.data.startswith(f"{P}:cli:"))
async def clients_more(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    await _show_clients_page(callback.message, session, offset=int(callback.data.split(":")[2]))


async def _show_clients_page(target: Message, session: AsyncSession, *, offset: int) -> None:
    clients = await crud.list_clients(session, limit=PAGE, offset=offset)
    if not clients:
        await target.answer("Больше заявок нет." if offset else "Заявок пока нет.")
        return
    for client in clients:
        await target.answer(format_client_short(client), reply_markup=admin_kb.client_actions_kb(client))
    if len(clients) == PAGE:
        await target.answer("…", reply_markup=admin_kb.more_kb(f"{P}:cli:{offset + PAGE}"))


@router.callback_query(F.data.startswith(f"{P}:cstatus:"))
async def change_client_status(callback: CallbackQuery, session: AsyncSession) -> None:
    _, _, client_id, status = callback.data.split(":")
    client = await crud.set_client_status(session, client_id, ClientStatus(status))
    if client:
        await callback.message.edit_text(
            format_client_short(client), reply_markup=admin_kb.client_actions_kb(client)
        )
    await callback.answer("Статус обновлён")


@router.callback_query(F.data.startswith(f"{P}:cmatch:"))
async def client_matches(callback: CallbackQuery, session: AsyncSession) -> None:
    client = await crud.get_client(session, callback.data.split(":")[2])
    await callback.answer()
    if client is None:
        return
    props = await matcher.find_for_client(session, client)
    if not props:
        await callback.message.answer("Подходящих объектов нет.")
        return
    await callback.message.answer(f"🔎 Подходящие объекты для {client.id}:")
    for prop in props:
        await callback.message.answer(format_property_card(prop))


# ---------------------------------------------------------------------------
# Раздел: Встречи
# ---------------------------------------------------------------------------
@router.message(F.text == "📆 Встречи")
async def meetings_list(message: Message, session: AsyncSession) -> None:
    meetings = await crud.upcoming_meetings(session)
    if meetings:
        for meeting in meetings:
            await message.answer(format_meeting(meeting), reply_markup=admin_kb.meeting_actions_kb(meeting.id))
    else:
        await message.answer("Запланированных встреч нет.")
    await message.answer("Управление встречами:", reply_markup=admin_kb.meetings_menu_kb())


@router.callback_query(F.data.startswith(f"{P}:mdone:"))
async def meeting_done(callback: CallbackQuery, session: AsyncSession) -> None:
    meeting = await crud.set_meeting_status(session, callback.data.split(":")[2], MeetingStatus.done)
    if meeting:
        await crud.set_client_status(session, meeting.client_id, ClientStatus.showing_done)
        await _clear_markup(callback)
    await callback.answer("Встреча проведена ✅", show_alert=True)


@router.callback_query(F.data.startswith(f"{P}:mcancel:"))
async def meeting_cancel(callback: CallbackQuery, session: AsyncSession) -> None:
    await crud.set_meeting_status(session, callback.data.split(":")[2], MeetingStatus.cancelled)
    await _clear_markup(callback)
    await callback.answer("Встреча отменена ❌", show_alert=True)


@router.callback_query(F.data == f"{P}:meet_new")
async def meeting_new(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    clients = await crud.list_clients(session, limit=10)
    if not clients:
        await callback.answer("Нет клиентов", show_alert=True)
        return
    await state.set_state(ScheduleMeeting.client)
    await callback.message.answer("Выберите клиента:", reply_markup=admin_kb.pick_clients_kb(clients))
    await callback.answer()


@router.callback_query(ScheduleMeeting.client, F.data.startswith(f"{P}:mclient:"))
async def meeting_pick_client(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.update_data(client_id=callback.data.split(":")[2])
    props = await crud.list_properties(session, statuses=[PropertyStatus.active], limit=10)
    if not props:
        await state.clear()
        await callback.answer("Нет активных объектов", show_alert=True)
        return
    await state.set_state(ScheduleMeeting.property)
    await callback.message.edit_text("Выберите объект:", reply_markup=admin_kb.pick_properties_kb(props))
    await callback.answer()


@router.callback_query(ScheduleMeeting.property, F.data.startswith(f"{P}:mprop:"))
async def meeting_pick_property(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(property_id=callback.data.split(":")[2])
    await state.set_state(ScheduleMeeting.date)
    await callback.message.edit_text("Дата встречи (ДД.ММ.ГГГГ):")
    await callback.answer()


@router.message(ScheduleMeeting.date, F.text)
async def meeting_date(message: Message, state: FSMContext) -> None:
    from bot.utils.validators import parse_date

    date = parse_date(message.text)
    if date is None:
        await message.answer("Не понял дату. Формат ДД.ММ.ГГГГ.")
        return
    await state.update_data(date=date.isoformat())
    await state.set_state(ScheduleMeeting.time)
    await message.answer("Время встречи (ЧЧ:ММ):")


@router.message(ScheduleMeeting.time, F.text)
async def meeting_time(message: Message, state: FSMContext, session: AsyncSession) -> None:
    try:
        time = dt.datetime.strptime(message.text.strip(), "%H:%M").time()
    except ValueError:
        await message.answer("Не понял время. Формат ЧЧ:ММ, например 15:30.")
        return
    data = await state.get_data()
    when = dt.datetime.combine(dt.date.fromisoformat(data["date"]), time)
    meeting = await crud.create_meeting(
        session, client_id=data["client_id"], property_id=data["property_id"], when=when
    )
    await crud.set_client_status(session, data["client_id"], ClientStatus.showing_set)
    await state.clear()
    await message.answer(f"✅ Встреча {meeting.id} назначена на {when.strftime('%d.%m.%Y %H:%M')}.")


# ---------------------------------------------------------------------------
# Раздел: Публикации
# ---------------------------------------------------------------------------
@router.message(F.text == "📢 Публикации")
async def publications(message: Message, session: AsyncSession) -> None:
    pending = await crud.list_properties(session, statuses=[PropertyStatus.pending])
    active = await crud.list_properties(session, statuses=[PropertyStatus.active])

    if pending:
        await message.answer("🕒 <b>Очередь на публикацию:</b>")
        for prop in pending:
            await _show_property(message, prop, admin_kb.object_actions_kb(prop))
    else:
        await message.answer("Очередь на публикацию пуста.")

    if active:
        await message.answer("📢 <b>Опубликованные:</b>")
        for prop in active:
            await message.answer(format_property_card(prop), reply_markup=admin_kb.bump_kb(prop.id))


# ---------------------------------------------------------------------------
# Раздел: Статистика
# ---------------------------------------------------------------------------
@router.message(F.text == "📊 Статистика")
async def statistics(message: Message, session: AsyncSession) -> None:
    prop_stats = await crud.count_properties_by_status(session)
    client_stats = await crud.count_clients_by_status(session)

    threshold = timeutils.now() - dt.timedelta(days=BUMP_INTERVAL_DAYS)
    due = await crud.properties_due_for_bump(session, threshold)

    total = sum(prop_stats.values())
    lines = [
        "📊 <b>Статистика</b>",
        "",
        f"🏠 Объектов всего: {total}",
        f"  • активных: {prop_stats.get('active', 0)}",
        f"  • на проверке: {prop_stats.get('pending', 0)}",
        f"  • сдано: {prop_stats.get('rented', 0)} · продано: {prop_stats.get('sold', 0)}",
        f"  • архив: {prop_stats.get('archived', 0)}",
        "",
        "👥 <b>Клиенты по воронке:</b>",
        f"  • Новый: {client_stats.get('new', 0)}",
        f"  • Связались: {client_stats.get('contacted', 0)}",
        f"  • Показ назначен: {client_stats.get('showing_set', 0)}",
        f"  • Показ проведён: {client_stats.get('showing_done', 0)}",
        f"  • Сделка: {client_stats.get('deal', 0)}",
        f"  • Закрыт: {client_stats.get('closed', 0)}",
        "",
        f"📢 Нужно поднять сегодня: {len(due)}",
    ]
    await message.answer("\n".join(lines), reply_markup=admin_kb.export_kb())


@router.callback_query(F.data.startswith(f"{P}:export:"))
async def export_data(callback: CallbackQuery, session: AsyncSession) -> None:
    _, _, what, fmt = callback.data.split(":")
    if what == "props":
        data, filename = await export.export_properties(session, fmt)
    else:
        data, filename = await export.export_clients(session, fmt)
    await callback.message.answer_document(BufferedInputFile(data, filename=filename))
    await callback.answer("Готово ✅")


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
async def _clear_markup(callback: CallbackQuery) -> None:
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 - сообщение могло быть без клавиатуры
        pass


async def _notify_owner(bot: Bot, prop: Property, text: str) -> None:
    if not prop.owner_telegram_id:
        return
    try:
        await bot.send_message(prop.owner_telegram_id, text)
    except Exception:  # noqa: BLE001 - собственник мог заблокировать бота
        logger.debug("Не удалось уведомить собственника %s", prop.owner_telegram_id)
