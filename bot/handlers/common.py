"""Общий роутер: определение роли пользователя и меню ролей.

Логика первого/повторного входа:
- админ (ADMIN_TELEGRAM_ID) обрабатывается в admin-роутере (зарегистрирован выше);
- новый пользователь → выбор роли (Ищу жильё / Хочу сдать-продать);
- вернувшийся → сразу открываем сценарий по сохранённой роли;
- кнопка «Сменить роль» в меню.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database import crud
from bot.database.models import BotUser, UserRole
from bot.handlers.client import begin_client_form
from bot.handlers.owner import begin_property_form
from bot.keyboards import common_kb
from bot.utils.formatters import PROPERTY_STATUS_LABELS, format_property_card

router = Router(name="common")


# ---------------------------------------------------------------------------
# Точки входа
# ---------------------------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    user = await _ensure_user(message, session)
    if not user.role_chosen:
        await message.answer("👋 Здравствуйте! Что вас интересует?", reply_markup=common_kb.role_choice_kb())
    else:
        await _open_scenario(message, state, user.role)


@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def first_touch(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Первое (или случайное вне сценария) сообщение — определяем роль."""
    if get_settings().is_admin(message.from_user.id):
        return
    user = await _ensure_user(message, session)
    if not user.role_chosen:
        await message.answer("👋 Что вас интересует?", reply_markup=common_kb.role_choice_kb())
    else:
        await _open_menu(message, user.role)


# ---------------------------------------------------------------------------
# Выбор / смена роли
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith("role:"))
async def choose_role(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    role = UserRole(callback.data.split(":")[1])
    await crud.choose_role(session, callback.from_user.id, role)
    await callback.message.edit_reply_markup(reply_markup=None)
    await _open_scenario(callback.message, state, role)
    await callback.answer()


@router.message(F.text == "↩️ Сменить роль")
async def change_role(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Кем вы хотите быть?", reply_markup=common_kb.role_choice_kb())


# ---------------------------------------------------------------------------
# Кнопки меню ролей
# ---------------------------------------------------------------------------
@router.message(F.text == "🔎 Подобрать жильё")
async def menu_client(message: Message, state: FSMContext) -> None:
    await state.clear()
    await begin_client_form(message, state)


@router.message(F.text == "➕ Разместить объект")
async def menu_owner(message: Message, state: FSMContext) -> None:
    await state.clear()
    await begin_property_form(message, state)


@router.message(F.text == "📋 Мои объекты")
async def menu_my_objects(message: Message, session: AsyncSession) -> None:
    props = await crud.list_owner_properties(session, message.from_user.id)
    if not props:
        await message.answer("У вас пока нет размещённых объектов.")
        return
    for prop in props:
        status = PROPERTY_STATUS_LABELS.get(prop.status, prop.status.value)
        await message.answer(f"[{status}] " + format_property_card(prop))


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
async def _ensure_user(message: Message, session: AsyncSession) -> BotUser:
    return await crud.get_or_create_user(
        session,
        message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        is_admin=get_settings().is_admin(message.from_user.id),
    )


async def _open_scenario(message: Message, state: FSMContext, role: UserRole) -> None:
    if role == UserRole.owner:
        await message.answer("🏠 Режим собственника.", reply_markup=common_kb.owner_menu())
        await begin_property_form(message, state)
    else:
        await message.answer("🔎 Режим поиска жилья.", reply_markup=common_kb.client_menu())
        await begin_client_form(message, state)


async def _open_menu(message: Message, role: UserRole) -> None:
    if role == UserRole.owner:
        await message.answer("🏠 Меню собственника:", reply_markup=common_kb.owner_menu())
    else:
        await message.answer("🔎 Меню поиска жилья:", reply_markup=common_kb.client_menu())
