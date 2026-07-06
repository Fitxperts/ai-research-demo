"""FSM-состояния сценария администратора."""
from aiogram.fsm.state import State, StatesGroup


class Moderation(StatesGroup):
    reject_reason = State()
