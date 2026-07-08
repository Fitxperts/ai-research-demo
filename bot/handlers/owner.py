"""Хендлеры собственника: размещение объекта недвижимости (FSM, мультиязычно)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import i18n
from bot.config import get_settings
from bot.database import crud
from bot.database.models import (
    Property,
    PropertyKind,
    PropertyStatus,
    PropertyType,
    UserRole,
)
from bot.keyboards import owner_kb
from bot.keyboards.admin_kb import moderation_kb
from bot.services import duplicate_checker
from bot.services.ai_service import get_ai_service
from bot.states.owner_states import OwnerForm
from bot.utils.formatters import format_property_brief, format_property_card
from bot.utils.validators import is_valid_phone, parse_int, parse_price

logger = logging.getLogger(__name__)
router = Router(name="owner")
P = owner_kb.PREFIX

# Сериализация записи фото в FSM (фото альбома приходят как конкурентные апдейты).
_photo_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Вход
# ---------------------------------------------------------------------------
async def begin_property_form(message: Message, state: FSMContext, lang: str) -> None:
    """Начать анкету размещения объекта (используется и админом)."""
    await state.clear()
    await state.set_state(OwnerForm.deal_type)
    await state.update_data(lang=lang)
    await message.answer(i18n.t("owner_intro", lang), reply_markup=owner_kb.deal_type_kb(lang))


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext, session: AsyncSession, lang: str) -> None:
    await crud.get_or_create_user(
        session,
        message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        is_admin=get_settings().is_admin(message.from_user.id),
    )
    if not get_settings().is_admin(message.from_user.id):
        await crud.set_user_role(session, message.from_user.id, UserRole.owner)
    await begin_property_form(message, state, lang)


# ---------------------------------------------------------------------------
# Тип сделки → вид объекта → адрес → район
# ---------------------------------------------------------------------------
@router.callback_query(OwnerForm.deal_type, F.data.startswith(f"{P}:deal:"))
async def deal_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.update_data(deal_type=callback.data.split(":")[2])
    await state.set_state(OwnerForm.property_kind)
    await callback.message.edit_text(i18n.t("owner_kind_q", lang), reply_markup=owner_kb.kind_kb(lang))
    await callback.answer()


@router.message(OwnerForm.deal_type, F.text)
async def quick_add(message: Message, state: FSMContext, lang: str) -> None:
    """Быстрое добавление: собственник прислал всё одним сообщением."""
    parsed = await get_ai_service().parse_free_text(message.text)
    if parsed.get("rooms") and "property_kind" not in parsed:
        parsed["property_kind"] = "apartment"

    if not {"deal_type", "property_kind", "price"} <= parsed.keys():
        await message.answer(i18n.t("owner_quick_fail", lang), reply_markup=owner_kb.deal_type_kb(lang))
        return

    await state.update_data(
        deal_type=parsed["deal_type"],
        property_kind=parsed["property_kind"],
        price=parsed["price"],
        rooms=parsed.get("rooms"),
        district=parsed.get("district"),
        owner_phone=parsed.get("phone"),
    )
    await message.answer(i18n.t("owner_quick_ok", lang))
    await _show_confirm(message, state, lang)


@router.callback_query(OwnerForm.property_kind, F.data.startswith(f"{P}:kind:"))
async def kind_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.update_data(property_kind=callback.data.split(":")[2])
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_address(callback.message, state, lang)
    await callback.answer()


async def _ask_address(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.address)
    await message.answer(i18n.t("ask_address", lang))


@router.message(OwnerForm.address, F.text)
async def address_txt(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(address=message.text.strip()[:255])
    await state.set_state(OwnerForm.district)
    await message.answer(i18n.t("ask_owner_district", lang))


@router.message(OwnerForm.district, F.text)
async def district_txt(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(district=message.text.strip()[:128])
    await _ask_rooms(message, state, lang)


# ---------------------------------------------------------------------------
# Числовые поля: комнаты → площадь → этаж → этажность
# ---------------------------------------------------------------------------
async def _ask_rooms(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.rooms)
    await message.answer(i18n.t("owner_ask_rooms", lang), reply_markup=owner_kb.skip_kb(lang))


@router.message(OwnerForm.rooms, F.text)
async def rooms_txt(message: Message, state: FSMContext, lang: str) -> None:
    value = parse_int(message.text)
    if value is None:
        await message.answer(i18n.t("num_bad", lang), reply_markup=owner_kb.skip_kb(lang))
        return
    await state.update_data(rooms=value)
    await _ask_area(message, state, lang)


async def _ask_area(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.area)
    await message.answer(i18n.t("ask_area", lang), reply_markup=owner_kb.skip_kb(lang))


@router.message(OwnerForm.area, F.text)
async def area_txt(message: Message, state: FSMContext, lang: str) -> None:
    value = parse_price(message.text)
    if value is None:
        await message.answer(i18n.t("area_bad", lang), reply_markup=owner_kb.skip_kb(lang))
        return
    await state.update_data(area=value)
    await _ask_floor(message, state, lang)


async def _ask_floor(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.floor)
    await message.answer(i18n.t("ask_floor", lang), reply_markup=owner_kb.skip_kb(lang))


@router.message(OwnerForm.floor, F.text)
async def floor_txt(message: Message, state: FSMContext, lang: str) -> None:
    value = parse_int(message.text)
    if value is None:
        await message.answer(i18n.t("num_bad", lang), reply_markup=owner_kb.skip_kb(lang))
        return
    await state.update_data(floor=value)
    await _ask_floors(message, state, lang)


async def _ask_floors(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.floors)
    await message.answer(i18n.t("ask_floors", lang), reply_markup=owner_kb.skip_kb(lang))


@router.message(OwnerForm.floors, F.text)
async def floors_txt(message: Message, state: FSMContext, lang: str) -> None:
    value = parse_int(message.text)
    if value is None:
        await message.answer(i18n.t("num_bad", lang), reply_markup=owner_kb.skip_kb(lang))
        return
    await state.update_data(floors=value)
    await _ask_renovation(message, state, lang)


# ---------------------------------------------------------------------------
# Ремонт
# ---------------------------------------------------------------------------
async def _ask_renovation(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.renovation)
    await message.answer(i18n.t("ask_renovation", lang), reply_markup=owner_kb.renovation_kb(lang))


@router.callback_query(OwnerForm.renovation, F.data.startswith(f"{P}:reno:"))
async def reno_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    key = callback.data.split(":")[2]
    msg_key = owner_kb.RENOVATION.get(key)
    await state.update_data(renovation=i18n.t(msg_key, lang) if msg_key else key)
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_furniture(callback.message, state, lang)
    await callback.answer()


@router.message(OwnerForm.renovation, F.text)
async def reno_txt(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(renovation=message.text.strip()[:128])
    await _ask_furniture(message, state, lang)


# ---------------------------------------------------------------------------
# Булевы поля (Да/Нет)
# ---------------------------------------------------------------------------
async def _ask_bool(message: Message, state: FSMContext, target, msg_key: str, lang: str) -> None:
    await state.set_state(target)
    await message.answer(i18n.t(msg_key, lang), reply_markup=owner_kb.yesno_kb(lang))


async def _ask_furniture(m: Message, s: FSMContext, lang: str) -> None:
    await _ask_bool(m, s, OwnerForm.furniture, "ask_furniture", lang)


async def _ask_appliances(m: Message, s: FSMContext, lang: str) -> None:
    await _ask_bool(m, s, OwnerForm.appliances, "ask_appliances", lang)


async def _ask_gas(m: Message, s: FSMContext, lang: str) -> None:
    await _ask_bool(m, s, OwnerForm.gas, "ask_gas", lang)


async def _ask_water(m: Message, s: FSMContext, lang: str) -> None:
    await _ask_bool(m, s, OwnerForm.water, "ask_water", lang)


async def _ask_electricity(m: Message, s: FSMContext, lang: str) -> None:
    await _ask_bool(m, s, OwnerForm.electricity, "ask_electricity", lang)


async def _ask_internet(m: Message, s: FSMContext, lang: str) -> None:
    await _ask_bool(m, s, OwnerForm.internet, "ask_internet", lang)


async def _ask_docs(m: Message, s: FSMContext, lang: str) -> None:
    await _ask_bool(m, s, OwnerForm.docs, "ask_docs", lang)


async def _ask_mortgage(m: Message, s: FSMContext, lang: str) -> None:
    await _ask_bool(m, s, OwnerForm.mortgage, "ask_mortgage", lang)


# Карта: текущее булево состояние -> (поле модели, следующий вопрос)
_BOOL_FLOW = {
    OwnerForm.furniture: ("furniture", _ask_appliances),
    OwnerForm.appliances: ("appliances", _ask_gas),
    OwnerForm.gas: ("gas", _ask_water),
    OwnerForm.water: ("water", _ask_electricity),
    OwnerForm.electricity: ("electricity", _ask_internet),
    OwnerForm.internet: ("internet", _ask_docs),
    OwnerForm.docs: ("docs", _ask_mortgage),
    OwnerForm.mortgage: ("mortgage", None),  # None → перейти к цене
}


async def _bool_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    current = await state.get_state()
    pair = next((p for st, p in _BOOL_FLOW.items() if st.state == current), None)
    if pair is None:
        await callback.answer()
        return
    field, nxt = pair
    await state.update_data(**{field: callback.data.split(":")[2] == "yes"})
    await callback.message.edit_reply_markup(reply_markup=None)
    if nxt is None:
        await _ask_price(callback.message, state, lang)
    else:
        await nxt(callback.message, state, lang)
    await callback.answer()


# ---------------------------------------------------------------------------
# Цена → торг → телефон
# ---------------------------------------------------------------------------
async def _ask_price(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.price)
    await message.answer(i18n.t("ask_price", lang))


@router.message(OwnerForm.price, F.text)
async def price_txt(message: Message, state: FSMContext, lang: str) -> None:
    value = parse_price(message.text)
    if value is None:
        await message.answer(i18n.t("price_bad", lang))
        return
    await state.update_data(price=value)
    await _ask_bool(message, state, OwnerForm.negotiable, "ask_negotiable", lang)


@router.callback_query(OwnerForm.negotiable, F.data.startswith(f"{P}:bool:"))
async def negotiable_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.update_data(negotiable=callback.data.split(":")[2] == "yes")
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_phone(callback.message, state, lang)
    await callback.answer()


async def _ask_phone(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.phone)
    await message.answer(i18n.t("owner_ask_phone", lang))


@router.message(OwnerForm.phone, F.text)
async def phone_txt(message: Message, state: FSMContext, lang: str) -> None:
    if not is_valid_phone(message.text):
        await message.answer(i18n.t("owner_phone_bad", lang))
        return
    await state.update_data(owner_phone=message.text.strip())
    await _ask_photos(message, state, lang)


# ---------------------------------------------------------------------------
# Фото (несколько) → видео (опционально)
# ---------------------------------------------------------------------------
async def _ask_photos(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.photos)
    await message.answer(i18n.t("ask_photos", lang), reply_markup=owner_kb.photos_done_kb(lang))


@router.message(OwnerForm.photos, F.photo)
async def collect_photo(message: Message, state: FSMContext, lang: str) -> None:
    async with _photo_lock:
        data = await state.get_data()
        photos: list[str] = data.get("photos", [])
        photos.append(message.photo[-1].file_id)
        notify = not message.media_group_id or data.get("_mg") != message.media_group_id
        await state.update_data(photos=photos, _mg=message.media_group_id)
    if notify:
        await message.answer(
            i18n.t("photo_accepted", lang, n=len(photos)),
            reply_markup=owner_kb.photos_done_kb(lang),
        )


@router.callback_query(OwnerForm.photos, F.data == f"{P}:pdone")
async def photos_done(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerForm.video)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(i18n.t("ask_video", lang), reply_markup=owner_kb.video_skip_kb(lang))
    await callback.answer()


@router.message(OwnerForm.video, F.video)
async def collect_video(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(video=message.video.file_id)
    await _show_confirm(message, state, lang)


@router.callback_query(OwnerForm.video, F.data == f"{P}:novideo")
async def skip_video(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await _show_confirm(callback.message, state, lang)
    await callback.answer()


# ---------------------------------------------------------------------------
# Пропуск числовых полей
# ---------------------------------------------------------------------------
_SKIP_NEXT = {
    OwnerForm.rooms.state: _ask_area,
    OwnerForm.area.state: _ask_floor,
    OwnerForm.floor.state: _ask_floors,
    OwnerForm.floors.state: _ask_renovation,
}


@router.callback_query(F.data == f"{P}:skip")
async def skip_numeric(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    nxt = _SKIP_NEXT.get(await state.get_state())
    if nxt:
        await callback.message.edit_reply_markup(reply_markup=None)
        await nxt(callback.message, state, lang)
    await callback.answer()


# ---------------------------------------------------------------------------
# Подтверждение и сохранение
# ---------------------------------------------------------------------------
async def _show_confirm(message: Message, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    preview = _build_preview(data)
    await state.set_state(OwnerForm.confirm)
    await message.answer(i18n.t("owner_confirm_title", lang))
    await message.answer(format_property_card(preview, lang), reply_markup=owner_kb.confirm_kb(lang))


@router.callback_query(OwnerForm.confirm, F.data == f"{P}:cancel")
async def confirm_cancel(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(i18n.t("owner_cancelled", lang))
    await callback.answer()


@router.callback_query(OwnerForm.confirm, F.data == f"{P}:confirm")
async def confirm_save(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, lang: str
) -> None:
    data = await state.get_data()

    dups = await duplicate_checker.check_duplicates(session, data)
    if dups:
        brief = "\n".join("• " + format_property_brief(p) for p in dups)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            i18n.t("dup_warning", lang, brief=brief),
            reply_markup=owner_kb.dup_confirm_kb(lang),
        )
        await _notify_admins_text(bot, "⚠️ Возможный дубль при добавлении объекта:\n" + brief)
        await callback.answer()
        return

    await _save_property(callback, state, session, bot, lang)


@router.callback_query(OwnerForm.confirm, F.data == f"{P}:dupyes")
async def dup_yes(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, lang: str) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await _save_property(callback, state, session, bot, lang)


@router.callback_query(OwnerForm.confirm, F.data == f"{P}:dupno")
async def dup_no(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(i18n.t("dup_cancelled", lang))
    await callback.answer()


async def _save_property(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, lang: str
) -> None:
    data = await state.get_data()

    description = await get_ai_service().generate_short_description(data)

    photos = data.get("photos", [])
    prop = await crud.create_property(
        session,
        property_kind=PropertyKind(data["property_kind"]),
        type=PropertyType(data["deal_type"]),
        status=PropertyStatus.pending,
        owner_name=callback.from_user.full_name,
        owner_phone=data.get("owner_phone"),
        owner_telegram_id=callback.from_user.id,
        district=data.get("district"),
        address=data.get("address"),
        rooms=data.get("rooms"),
        area=data.get("area"),
        floor=data.get("floor"),
        floors=data.get("floors"),
        renovation=data.get("renovation"),
        furniture=bool(data.get("furniture")),
        appliances=bool(data.get("appliances")),
        gas=bool(data.get("gas")),
        water=bool(data.get("water")),
        electricity=bool(data.get("electricity")),
        internet=bool(data.get("internet")),
        docs=bool(data.get("docs")),
        mortgage=bool(data.get("mortgage")),
        price=data.get("price"),
        currency="сум",
        negotiable=bool(data.get("negotiable")),
        description=description,
        photos=",".join(photos),
        video=data.get("video"),
    )
    await state.clear()

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(i18n.t("sent_to_moderation", lang, id=prop.id))
    await callback.answer()

    await _notify_admins(bot, prop)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def _build_preview(data: dict) -> Property:
    return Property(
        id="—",
        type=PropertyType(data["deal_type"]),
        property_kind=PropertyKind(data["property_kind"]),
        owner_phone=data.get("owner_phone"),
        district=data.get("district"),
        address=data.get("address"),
        rooms=data.get("rooms"),
        area=data.get("area"),
        floor=data.get("floor"),
        floors=data.get("floors"),
        renovation=data.get("renovation"),
        furniture=bool(data.get("furniture")),
        appliances=bool(data.get("appliances")),
        gas=bool(data.get("gas")),
        water=bool(data.get("water")),
        electricity=bool(data.get("electricity")),
        internet=bool(data.get("internet")),
        price=data.get("price"),
        currency="сум",
        negotiable=bool(data.get("negotiable")),
    )


async def _notify_admins_text(bot: Bot, text: str) -> None:
    for admin_id in get_settings().admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:  # noqa: BLE001
            logger.debug("Не удалось уведомить админа %s", admin_id)


async def _notify_admins(bot: Bot, prop: Property) -> None:
    text = "🆕 <b>Объект на модерацию</b>\n\n" + format_property_card(prop)
    kb = moderation_kb(prop.id)
    photos = prop.photo_list
    for admin_id in get_settings().admin_ids:
        try:
            if photos:
                await bot.send_photo(admin_id, photo=photos[0], caption=text, reply_markup=kb)
            else:
                await bot.send_message(admin_id, text, reply_markup=kb)
        except Exception:  # noqa: BLE001 - админ мог не запускать бота
            logger.debug("Не удалось уведомить админа %s", admin_id)


# Регистрация обобщённых Да/Нет обработчиков для булевых состояний
for _state in _BOOL_FLOW:
    router.callback_query.register(_bool_cb, _state, F.data.startswith(f"{P}:bool:"))
