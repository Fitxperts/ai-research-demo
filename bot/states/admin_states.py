"""FSM-состояния сценария администратора."""
from aiogram.fsm.state import State, StatesGroup


class EditProperty(StatesGroup):
    value = State()  # ввод нового значения выбранного поля


class ScheduleMeeting(StatesGroup):
    client = State()    # выбор клиента
    property = State()  # выбор объекта
    date = State()      # дата
    time = State()      # время
