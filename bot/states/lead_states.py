"""FSM-состояние заявки с канала (лид по конкретному объекту)."""
from aiogram.fsm.state import State, StatesGroup


class LeadForm(StatesGroup):
    phone = State()  # ждём телефон лида, пришедшего по кнопке под постом
