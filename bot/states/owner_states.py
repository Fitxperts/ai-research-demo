"""FSM-состояния сценария собственника (размещение объекта)."""
from aiogram.fsm.state import State, StatesGroup


class OwnerForm(StatesGroup):
    deal_type = State()      # аренда или продажа
    property_kind = State()  # квартира/дом/участок/коммерция
    address = State()        # адрес
    district = State()       # район
    rooms = State()          # комнаты
    area = State()           # площадь
    floor = State()          # этаж
    floors = State()         # этажность
    renovation = State()     # ремонт
    furniture = State()      # мебель
    appliances = State()     # техника
    gas = State()            # газ
    water = State()          # вода
    electricity = State()    # электричество
    internet = State()       # интернет
    docs = State()           # документы
    mortgage = State()       # ипотека/кредит
    price = State()          # цена
    negotiable = State()     # торг
    phone = State()          # телефон
    photos = State()         # фото (несколько)
    video = State()          # видео (опционально)
    confirm = State()        # подтверждение
