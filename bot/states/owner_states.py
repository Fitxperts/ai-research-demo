"""FSM-состояния сценария собственника (создание объявления)."""
from aiogram.fsm.state import State, StatesGroup


class ListingCreate(StatesGroup):
    deal_type = State()
    property_type = State()
    title = State()
    description = State()
    price = State()
    rooms = State()
    area = State()
    district = State()
    address = State()
    photos = State()
    confirm = State()
