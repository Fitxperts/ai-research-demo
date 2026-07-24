"""FSM-состояния сценария клиента (заявка на подбор недвижимости)."""
from aiogram.fsm.state import State, StatesGroup


class ClientForm(StatesGroup):
    deal_type = State()   # аренда или покупка
    district = State()    # район
    budget = State()      # бюджет
    residents = State()   # кто будет жить
    move_date = State()   # дата заселения
    phone = State()       # телефон
    confirm = State()     # подтверждение
