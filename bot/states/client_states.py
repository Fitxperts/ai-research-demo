"""FSM-состояния сценария клиента (подбор недвижимости)."""
from aiogram.fsm.state import State, StatesGroup


class ClientSearch(StatesGroup):
    deal_type = State()
    property_type = State()
    district = State()
    budget = State()
    rooms = State()
    confirm = State()


class ClientAI(StatesGroup):
    """Свободный диалог с ИИ-ассистентом по подбору."""

    chatting = State()
