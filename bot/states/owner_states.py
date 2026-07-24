"""FSM-состояния сценария собственника (размещение объекта одним сообщением)."""
from aiogram.fsm.state import State, StatesGroup


class OwnerForm(StatesGroup):
    raw = State()        # объявление одним сообщением (осн. путь)
    deal_type = State()  # тип сделки (дозапрос, если не распознан)
    price = State()      # цена (дозапрос)
    district = State()   # район/массив (дозапрос: выбор из списка или свой)
    phone = State()      # телефон (дозапрос)
    photos = State()     # медиа-шаг (фото/видео) + «Готово»
    confirm = State()    # подтверждение
