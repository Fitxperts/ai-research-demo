"""Общие хендлеры: старт, выбор роли, отмена."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database import crud
from bot.database.models import UserRole
from bot.keyboards.common_kb import admin_menu, client_menu, owner_menu, role_keyboard

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    user = await crud.get_or_create_user(
        session,
        message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    if get_settings().is_admin(message.from_user.id):
        if user.role != UserRole.admin:
            await crud.set_user_role(session, user.telegram_id, UserRole.admin)
        await message.answer(
            "👋 Панель администратора РиелторБота.", reply_markup=admin_menu()
        )
        return

    if user.role == UserRole.client:
        await message.answer(
            "👋 Добро пожаловать! Я помогу подобрать недвижимость.",
            reply_markup=client_menu(),
        )
    elif user.role == UserRole.owner:
        await message.answer(
            "👋 С возвращением! Управляйте своими объявлениями.",
            reply_markup=owner_menu(),
        )
    else:
        await message.answer(
            "👋 Здравствуйте! Выберите, что вас интересует:",
            reply_markup=role_keyboard(),
        )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.")


@router.message(F.text == "↩️ Сменить роль")
async def change_role(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Кем вы хотите быть?", reply_markup=role_keyboard())


@router.callback_query(F.data.startswith("role:"))
async def choose_role(callback: CallbackQuery, session: AsyncSession) -> None:
    _, role_value = callback.data.split(":", 1)
    role = UserRole(role_value)
    await crud.set_user_role(session, callback.from_user.id, role)

    if role == UserRole.client:
        await callback.message.answer(
            "Отлично! Ищем недвижимость 🔎", reply_markup=client_menu()
        )
    else:
        await callback.message.answer(
            "Отлично! Разместим ваши объекты 🏠", reply_markup=owner_menu()
        )
    await callback.answer()
