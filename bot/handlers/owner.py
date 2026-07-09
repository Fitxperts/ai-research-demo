"""Хендлеры собственника: размещение объекта одним сообщением (осн. путь).

Логика: пользователь присылает объявление целиком (своё или готовое от
партнёра) — ИИ разбирает поля и оформляет описание в стиле агентства.
Вручную бот спрашивает ТОЛЬКО то, что не удалось распознать и что критично
для публикации: тип сделки, цену, телефон. Затем фото и подтверждение.
"""
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
from bot.utils.validators import is_valid_phone, parse_price

logger = logging.getLogger(__name__)
router = Router(name="owner")
P = owner_kb.PREFIX

# Сериализация записи фото в FSM (фото альбома приходят конкурентно).
_photo_lock = asyncio.Lock()

# Поля, которые переносим из разбора объявления в состояние
_LISTING_FIELDS = ("deal_type", "property_kind", "rooms", "district", "address",
                   "area", "floor", "floors", "description")


# ---------------------------------------------------------------------------
# Вход: просим прислать объявление одним сообщением
# ---------------------------------------------------------------------------
async def begin_property_form(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await state.set_state(OwnerForm.raw)
    await state.update_data(lang=lang)
    await message.answer(i18n.t("owner_intro", lang))


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
# Разбор объявления (текст или фото с подписью)
# ---------------------------------------------------------------------------
@router.message(OwnerForm.raw, F.text)
async def listing_text(message: Message, state: FSMContext, lang: str) -> None:
    await _handle_listing(message, state, lang, message.text)


@router.message(OwnerForm.raw, F.photo)
async def listing_photo(message: Message, state: FSMContext, lang: str) -> None:
    async with _photo_lock:
        data = await state.get_data()
        photos: list[str] = data.get("photos", [])
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)
    caption = (message.caption or "").strip()
    if caption:
        await _handle_listing(message, state, lang, caption)
    else:
        # Фото без подписи: ждём текст объявления (просим один раз).
        data = await state.get_data()
        if not data.get("_asked_text"):
            await state.update_data(_asked_text=True)
            await message.answer(i18n.t("owner_send_text", lang))


async def _handle_listing(message: Message, state: FSMContext, lang: str, text: str) -> None:
    parsed = await get_ai_service().parse_listing(text)
    # комнаты есть, а вид не распознан → по умолчанию квартира
    if parsed.get("rooms") and not parsed.get("property_kind"):
        parsed["property_kind"] = "apartment"

    update = {k: parsed[k] for k in _LISTING_FIELDS if parsed.get(k) is not None}
    if parsed.get("price") is not None:
        update["price"] = parsed["price"]
    if parsed.get("phone"):
        update["owner_phone"] = parsed["phone"]
    await state.update_data(**update)

    await message.answer(i18n.t("owner_quick_ok", lang))
    await _route_missing(message, state, lang)


# ---------------------------------------------------------------------------
# Дозапрос только недостающего критичного: сделка → цена → телефон → фото
# ---------------------------------------------------------------------------
async def _route_missing(message: Message, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    if not data.get("deal_type"):
        await state.set_state(OwnerForm.deal_type)
        await message.answer(i18n.t("owner_need_deal", lang), reply_markup=owner_kb.deal_type_kb(lang))
        return
    if not data.get("property_kind"):
        await state.update_data(property_kind="apartment")  # тип по умолчанию, не спрашиваем
    if data.get("price") is None:
        await state.set_state(OwnerForm.price)
        await message.answer(i18n.t("owner_need_price", lang))
        return
    if not data.get("owner_phone"):
        await state.set_state(OwnerForm.phone)
        await message.answer(i18n.t("owner_ask_phone", lang))
        return
    await _ask_photos(message, state, lang)


@router.callback_query(OwnerForm.deal_type, F.data.startswith(f"{P}:deal:"))
async def deal_cb(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.update_data(deal_type=callback.data.split(":")[2])
    await callback.message.edit_reply_markup(reply_markup=None)
    await _route_missing(callback.message, state, lang)
    await callback.answer()


@router.message(OwnerForm.price, F.text)
async def price_txt(message: Message, state: FSMContext, lang: str) -> None:
    value = parse_price(message.text)
    if value is None:
        await message.answer(i18n.t("price_bad", lang))
        return
    await state.update_data(price=value)
    await _route_missing(message, state, lang)


@router.message(OwnerForm.phone, F.text)
async def phone_txt(message: Message, state: FSMContext, lang: str) -> None:
    if not is_valid_phone(message.text):
        await message.answer(i18n.t("owner_phone_bad", lang))
        return
    await state.update_data(owner_phone=message.text.strip())
    await _route_missing(message, state, lang)


# ---------------------------------------------------------------------------
# Фото → видео (опционально) → подтверждение
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

    # Описание: причёсанное ИИ из объявления; иначе — офлайн-фолбэк.
    description = data.get("description") or await get_ai_service().generate_short_description(data)

    photos = data.get("photos", [])
    prop = await crud.create_property(
        session,
        property_kind=PropertyKind(data.get("property_kind", "apartment")),
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
        price=data.get("price"),
        currency="сум",
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
        property_kind=PropertyKind(data.get("property_kind", "apartment")),
        owner_phone=data.get("owner_phone"),
        district=data.get("district"),
        address=data.get("address"),
        rooms=data.get("rooms"),
        area=data.get("area"),
        floor=data.get("floor"),
        floors=data.get("floors"),
        renovation=data.get("renovation"),
        price=data.get("price"),
        currency="сум",
        description=data.get("description"),
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
