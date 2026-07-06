"""Хендлеры собственника: создание и управление объявлениями."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database import crud
from bot.database.models import DealType, Listing, ListingStatus, PropertyType
from bot.keyboards.admin_kb import moderation_keyboard
from bot.keyboards.common_kb import (
    confirm_keyboard,
    deal_type_keyboard,
    property_type_keyboard,
    skip_keyboard,
)
from bot.keyboards.owner_kb import listing_actions_keyboard, photos_done_keyboard
from bot.services import publisher
from bot.states.owner_states import ListingCreate
from bot.utils.formatters import format_listing
from bot.utils.validators import parse_int, parse_price

router = Router(name="owner")
PREFIX = "owner"


# ---------------------------------------------------------------------------
# Создание объявления (FSM)
# ---------------------------------------------------------------------------
@router.message(F.text == "➕ Разместить объявление")
async def start_create(message: Message, state: FSMContext) -> None:
    await state.set_state(ListingCreate.deal_type)
    await message.answer("Тип сделки?", reply_markup=deal_type_keyboard(PREFIX))


@router.callback_query(ListingCreate.deal_type, F.data.startswith(f"{PREFIX}:deal:"))
async def set_deal(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(deal_type=callback.data.rsplit(":", 1)[1])
    await state.set_state(ListingCreate.property_type)
    await callback.message.edit_text("Тип объекта?", reply_markup=property_type_keyboard(PREFIX))
    await callback.answer()


@router.callback_query(ListingCreate.property_type, F.data.startswith(f"{PREFIX}:prop:"))
async def set_property(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(property_type=callback.data.rsplit(":", 1)[1])
    await state.set_state(ListingCreate.title)
    await callback.message.edit_text("Введите заголовок объявления:")
    await callback.answer()


@router.message(ListingCreate.title, F.text)
async def set_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip()[:255])
    await state.set_state(ListingCreate.description)
    await message.answer("Опишите объект:", reply_markup=skip_keyboard(PREFIX))


@router.message(ListingCreate.description, F.text)
async def set_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await _ask_price(message, state)


@router.message(ListingCreate.price, F.text)
async def set_price(message: Message, state: FSMContext) -> None:
    price = parse_price(message.text)
    if price is None:
        await message.answer("Не понял цену. Введите число, например 4500000.")
        return
    await state.update_data(price=price)
    await state.set_state(ListingCreate.rooms)
    await message.answer("Сколько комнат?", reply_markup=skip_keyboard(PREFIX))


@router.message(ListingCreate.rooms, F.text)
async def set_rooms(message: Message, state: FSMContext) -> None:
    rooms = parse_int(message.text)
    if rooms is None:
        await message.answer("Введите целое число комнат или нажмите «Пропустить».")
        return
    await state.update_data(rooms=rooms)
    await state.set_state(ListingCreate.area)
    await message.answer("Площадь (м²)?", reply_markup=skip_keyboard(PREFIX))


@router.message(ListingCreate.area, F.text)
async def set_area(message: Message, state: FSMContext) -> None:
    area = parse_price(message.text)
    if area is None:
        await message.answer("Введите площадь числом или нажмите «Пропустить».")
        return
    await state.update_data(area=area)
    await state.set_state(ListingCreate.district)
    await message.answer("Район?", reply_markup=skip_keyboard(PREFIX))


@router.message(ListingCreate.district, F.text)
async def set_district(message: Message, state: FSMContext) -> None:
    await state.update_data(district=message.text.strip()[:128])
    await state.set_state(ListingCreate.address)
    await message.answer("Адрес?", reply_markup=skip_keyboard(PREFIX))


@router.message(ListingCreate.address, F.text)
async def set_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip()[:255])
    await _ask_photos(message, state)


@router.message(ListingCreate.photos, F.photo)
async def collect_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos: list[str] = data.get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(
        f"Фото добавлено ({len(photos)}). Пришлите ещё или нажмите «Готово».",
        reply_markup=photos_done_keyboard(),
    )


# --- обработка «Пропустить» на разных шагах ---
@router.callback_query(F.data == f"{PREFIX}:skip")
async def skip_step(callback: CallbackQuery, state: FSMContext) -> None:
    current = await state.get_state()
    if current == ListingCreate.description.state:
        await state.update_data(description="")
        await _ask_price(callback.message, state)
    elif current == ListingCreate.rooms.state:
        await state.set_state(ListingCreate.area)
        await callback.message.answer("Площадь (м²)?", reply_markup=skip_keyboard(PREFIX))
    elif current == ListingCreate.area.state:
        await state.set_state(ListingCreate.district)
        await callback.message.answer("Район?", reply_markup=skip_keyboard(PREFIX))
    elif current == ListingCreate.district.state:
        await state.set_state(ListingCreate.address)
        await callback.message.answer("Адрес?", reply_markup=skip_keyboard(PREFIX))
    elif current == ListingCreate.address.state:
        await _ask_photos(callback.message, state)
    await callback.answer()


@router.callback_query(ListingCreate.photos, F.data == f"{PREFIX}:photos_done")
async def photos_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await _show_preview(callback.message, state, session)
    await callback.answer()


@router.callback_query(ListingCreate.confirm, F.data == f"{PREFIX}:confirm")
async def confirm_create(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    data = await state.get_data()
    user = await crud.get_user(session, callback.from_user.id)
    listing = await crud.create_listing(
        session,
        owner_id=user.id,
        title=data["title"],
        description=data.get("description", ""),
        deal_type=DealType(data["deal_type"]),
        property_type=PropertyType(data["property_type"]),
        price=data["price"],
        rooms=data.get("rooms"),
        area=data.get("area"),
        district=data.get("district"),
        address=data.get("address"),
        status=ListingStatus.pending,
    )
    photos = data.get("photos", [])
    if photos:
        listing.set_photos(photos)
        await session.commit()

    await state.clear()
    await callback.message.answer("✅ Объявление отправлено на модерацию!")
    await _notify_admins(bot, listing)
    await callback.answer()


@router.callback_query(ListingCreate.confirm, F.data == f"{PREFIX}:cancel")
async def cancel_create(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Создание объявления отменено.")
    await callback.answer()


# ---------------------------------------------------------------------------
# Управление своими объявлениями
# ---------------------------------------------------------------------------
@router.message(F.text == "📋 Мои объявления")
async def my_listings(message: Message, session: AsyncSession) -> None:
    user = await crud.get_user(session, message.from_user.id)
    listings = await crud.list_owner_listings(session, user.id)
    if not listings:
        await message.answer("У вас пока нет объявлений.")
        return
    for listing in listings:
        await message.answer(
            format_listing(listing, with_status=True),
            parse_mode="HTML",
            reply_markup=listing_actions_keyboard(listing),
        )


@router.callback_query(F.data.startswith(f"{PREFIX}:bump:"))
async def bump(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    listing = await crud.get_listing(session, int(callback.data.rsplit(":", 1)[1]))
    if listing:
        await publisher.bump_listing(bot, session, listing)
        await callback.answer("Объявление поднято ⬆️", show_alert=True)
    else:
        await callback.answer("Объявление не найдено", show_alert=True)


@router.callback_query(F.data.startswith(f"{PREFIX}:archive:"))
async def archive(callback: CallbackQuery, session: AsyncSession) -> None:
    listing_id = int(callback.data.rsplit(":", 1)[1])
    await crud.set_listing_status(session, listing_id, ListingStatus.archived)
    await callback.answer("Снято с публикации 🗄", show_alert=True)


@router.callback_query(F.data.startswith(f"{PREFIX}:submit:"))
async def resubmit(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    listing_id = int(callback.data.rsplit(":", 1)[1])
    listing = await crud.set_listing_status(session, listing_id, ListingStatus.pending)
    if listing:
        await _notify_admins(bot, listing)
        await callback.answer("Отправлено на модерацию 📤", show_alert=True)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
async def _ask_price(message: Message, state: FSMContext) -> None:
    await state.set_state(ListingCreate.price)
    await message.answer("Цена (₽)?")


async def _ask_photos(message: Message, state: FSMContext) -> None:
    await state.set_state(ListingCreate.photos)
    await message.answer(
        "Пришлите фотографии объекта (по одной) или нажмите «Готово».",
        reply_markup=photos_done_keyboard(),
    )


async def _show_preview(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    preview = Listing(
        title=data["title"],
        description=data.get("description", ""),
        deal_type=DealType(data["deal_type"]),
        property_type=PropertyType(data["property_type"]),
        price=data["price"],
        rooms=data.get("rooms"),
        area=data.get("area"),
        district=data.get("district"),
        address=data.get("address"),
    )
    await state.set_state(ListingCreate.confirm)
    await message.answer("Проверьте объявление:", parse_mode="HTML")
    await message.answer(
        format_listing(preview), parse_mode="HTML", reply_markup=confirm_keyboard(PREFIX)
    )


async def _notify_admins(bot: Bot, listing: Listing) -> None:
    text = "🆕 Новое объявление на модерацию:\n\n" + format_listing(listing)
    for admin_id in get_settings().admin_ids:
        try:
            await bot.send_message(
                admin_id, text, parse_mode="HTML", reply_markup=moderation_keyboard(listing.id)
            )
        except Exception:  # noqa: BLE001 - админ мог не запускать бота
            continue
