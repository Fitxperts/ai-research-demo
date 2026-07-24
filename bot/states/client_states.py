"""FSM-состояния сценария клиента (заявка на подбор недвижимости)."""
from aiogram.fsm.state import State, StatesGroup


class ClientForm(StatesGroup):
    deal_type = State()   # аренда или покупка
    district = State()    # район
    budget = State()      # бюджет
    phone = State()       # телефон
    confirm = State()     # подтверждение
