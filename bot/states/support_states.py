"""FSM-состояние обращения в поддержку (вопрос / сообщение об ошибке)."""
from aiogram.fsm.state import State, StatesGroup


class SupportForm(StatesGroup):
    waiting = State()  # ждём текст обращения от пользователя
