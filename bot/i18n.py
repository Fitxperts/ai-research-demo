"""Мультиязычность РиелторБота: узбекский, русский, английский.

- ``LANGUAGES`` — поддерживаемые языки и их подписи для выбора;
- ``t(key, lang, **kwargs)`` — перевод сообщения с подстановкой параметров;
- ``btn(action, lang)`` — подпись кнопки;
- ``btn_variants(action)`` / ``all_menu_texts()`` — множества всех переводов
  подписи (нужны, чтобы ловить reply-кнопки на любом языке через ``F.text.in_``).

Тексты канала (публичное объявление) и админ-панель здесь НЕ переводятся:
объявление в канал одно на всех (узбекский шаблон), админку видит только
оператор-риелтор.
"""
from __future__ import annotations

# Порядок = порядок кнопок выбора языка
LANGUAGES: dict[str, str] = {
    "uz": "🇺🇿 O‘zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}
DEFAULT_LANG = "ru"


def normalize(lang: str | None) -> str:
    return lang if lang in LANGUAGES else DEFAULT_LANG


# ---------------------------------------------------------------------------
# Подписи кнопок: action -> {lang: label}
# ---------------------------------------------------------------------------
BUTTONS: dict[str, dict[str, str]] = {
    # Reply-меню (матчатся по тексту — нужны все языки)
    "find_housing": {"uz": "🔎 Uy tanlash", "ru": "🔎 Подобрать жильё", "en": "🔎 Find housing"},
    "add_object": {"uz": "➕ E’lon joylash", "ru": "➕ Разместить объект", "en": "➕ Post a listing"},
    "my_objects": {"uz": "📋 Mening e’lonlarim", "ru": "📋 Мои объекты", "en": "📋 My listings"},
    "change_role": {"uz": "↩️ Rolni almashtirish", "ru": "↩️ Сменить роль", "en": "↩️ Change role"},
    "language": {"uz": "🌐 Til", "ru": "🌐 Язык", "en": "🌐 Language"},
    # Роли (inline)
    "role_client": {"uz": "🔎 Uy qidiryapman", "ru": "🔎 Ищу жильё", "en": "🔎 Looking for housing"},
    "role_owner": {"uz": "🏠 Sotaman/ijaraga beraman", "ru": "🏠 Хочу сдать/продать", "en": "🏠 Sell / rent out"},
    # Клиент: сделка
    "deal_rent": {"uz": "🔑 Ijara", "ru": "🔑 Аренда", "en": "🔑 Rent"},
    "deal_buy": {"uz": "🏷 Sotib olish", "ru": "🏷 Покупка", "en": "🏷 Buy"},
    # Общие
    "district_other": {"uz": "✍️ Boshqa tuman", "ru": "✍️ Другой район", "en": "✍️ Other district"},
    "skip": {"uz": "Oʻtkazib yuborish", "ru": "Пропустить", "en": "Skip"},
    "send_phone": {"uz": "📱 Raqamimni yuborish", "ru": "📱 Отправить мой номер", "en": "📱 Share my number"},
    "confirm_send": {"uz": "✅ Yuborish", "ru": "✅ Отправить", "en": "✅ Submit"},
    "cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена", "en": "❌ Cancel"},
    "support": {"uz": "✍️ Savol / xatolik", "ru": "✍️ Задать вопрос / ошибка", "en": "✍️ Ask / report a bug"},
    "yes": {"uz": "Ha", "ru": "Да", "en": "Yes"},
    "no": {"uz": "Yoʻq", "ru": "Нет", "en": "No"},
    "done": {"uz": "Tayyor", "ru": "Готово", "en": "Done"},
    # Владелец: виды объектов
    "kind_apartment": {"uz": "🏢 Kvartira", "ru": "🏢 Квартира", "en": "🏢 Apartment"},
    "kind_house": {"uz": "🏡 Hovli", "ru": "🏡 Дом", "en": "🏡 House"},
    "kind_land": {"uz": "🌳 Yer uchastka", "ru": "🌳 Участок", "en": "🌳 Land"},
    "kind_commercial": {"uz": "🏬 Tijorat obyekti", "ru": "🏬 Коммерция", "en": "🏬 Commercial"},
}


def btn(action: str, lang: str) -> str:
    variants = BUTTONS.get(action, {})
    return variants.get(normalize(lang)) or variants.get(DEFAULT_LANG, action)


def btn_variants(action: str) -> set[str]:
    """Все языковые варианты подписи — для матчинга reply-кнопок."""
    return set(BUTTONS.get(action, {}).values())


# Тексты reply-меню, которые нужно исключать из catch-all (все языки)
_MENU_ACTIONS = ("find_housing", "add_object", "my_objects", "change_role", "language")


def all_menu_texts() -> set[str]:
    texts: set[str] = set()
    for action in _MENU_ACTIONS:
        texts |= btn_variants(action)
    return texts


# ---------------------------------------------------------------------------
# Сообщения: key -> {lang: text}
# ---------------------------------------------------------------------------
MESSAGES: dict[str, dict[str, str]] = {
    # --- Язык / роль / меню ---
    "choose_language": {
        "uz": "Tilni tanlang:",
        "ru": "Выберите язык:",
        "en": "Choose your language:",
    },
    "language_saved": {
        "uz": "✅ Til oʻzgartirildi: {name}",
        "ru": "✅ Язык изменён: {name}",
        "en": "✅ Language set: {name}",
    },
    "choose_role": {
        "uz": "👋 Assalomu alaykum! Sizni nima qiziqtiradi?",
        "ru": "👋 Здравствуйте! Что вас интересует?",
        "en": "👋 Hello! What are you interested in?",
    },
    "choose_role_short": {
        "uz": "Kim boʻlishni xohlaysiz?",
        "ru": "Кем вы хотите быть?",
        "en": "What would you like to do?",
    },
    "client_mode": {
        "uz": "🔎 Uy qidirish rejimi.",
        "ru": "🔎 Режим поиска жилья.",
        "en": "🔎 Housing search mode.",
    },
    "owner_mode": {
        "uz": "🏠 Egasi rejimi.",
        "ru": "🏠 Режим собственника.",
        "en": "🏠 Owner mode.",
    },
    "client_menu_title": {
        "uz": "🔎 Uy qidirish menyusi:",
        "ru": "🔎 Меню поиска жилья:",
        "en": "🔎 Housing search menu:",
    },
    "owner_menu_title": {
        "uz": "🏠 Egasi menyusi:",
        "ru": "🏠 Меню собственника:",
        "en": "🏠 Owner menu:",
    },
    "no_objects": {
        "uz": "Sizda hozircha joylangan obyektlar yoʻq.",
        "ru": "У вас пока нет размещённых объектов.",
        "en": "You have no listings yet.",
    },
    # --- Служебное ---
    "cancel_none": {
        "uz": "Faol amal yoʻq.",
        "ru": "Нет активного действия.",
        "en": "No active action.",
    },
    "cancel_done": {
        "uz": "✖️ Amal bekor qilindi. /start — menyu.",
        "ru": "✖️ Действие отменено. /start — в меню.",
        "en": "✖️ Action cancelled. /start — menu.",
    },
    # --- Помощь / поддержка ---
    "help_text": {
        "uz": (
            "ℹ️ <b>RieltorBot — Fargʻona</b>\n\n"
            "• /start — boshlash / rolni tanlash\n"
            "• /add — obyekt joylash (egalar uchun)\n"
            "• /cancel — joriy amalni bekor qilish\n\n"
            "Mijoz: ariza qoldiring — variant tanlaymiz va yangilaridan xabar beramiz.\n"
            "Egasi: obyektni bosqichma-bosqich yoki bitta xabarda joylang.\n\n"
            "Savol yoki xatolik bormi? Pastdagi tugmani bosing 👇"
        ),
        "ru": (
            "ℹ️ <b>РиелторБот — Фергана</b>\n\n"
            "• /start — начать / выбрать роль\n"
            "• /add — разместить объект (для собственника)\n"
            "• /cancel — отменить текущее действие\n\n"
            "Клиент: оставьте заявку — подберём варианты и сообщим о новых.\n"
            "Собственник: разместите объект по шагам или одним сообщением.\n\n"
            "Есть вопрос или нашли ошибку? Нажмите кнопку ниже 👇"
        ),
        "en": (
            "ℹ️ <b>RealtorBot — Fergana</b>\n\n"
            "• /start — begin / choose role\n"
            "• /add — post a listing (for owners)\n"
            "• /cancel — cancel current action\n\n"
            "Client: leave a request — we’ll find options and notify you of new ones.\n"
            "Owner: post a property step by step or in a single message.\n\n"
            "Have a question or found a bug? Tap the button below 👇"
        ),
    },
    "support_prompt": {
        "uz": "✍️ Savolingiz yoki xatolik haqida yozing — xabar administratorga yetkaziladi. Bekor qilish: /cancel",
        "ru": "✍️ Напишите ваш вопрос или опишите ошибку — сообщение уйдёт администратору. Отмена: /cancel",
        "en": "✍️ Write your question or describe the bug — it will be sent to the administrator. Cancel: /cancel",
    },
    "support_sent": {
        "uz": "✅ Xabaringiz yuborildi. Tez orada javob beramiz.",
        "ru": "✅ Ваше сообщение отправлено. Мы скоро ответим.",
        "en": "✅ Your message has been sent. We’ll get back to you soon.",
    },
    "support_reply_delivered": {
        "uz": "💬 <b>Qoʻllab-quvvatlash javobi:</b>\n{text}",
        "ru": "💬 <b>Ответ поддержки:</b>\n{text}",
        "en": "💬 <b>Support reply:</b>\n{text}",
    },
    # --- Клиент: анкета ---
    "client_intro": {
        "uz": "Fargʻonada uy tanlashda yordam beraman.\nSiz <b>ijaraga olmoqchimisiz</b> yoki <b>sotib olmoqchimisiz</b>?",
        "ru": "Помогу подобрать недвижимость в Фергане.\nВы хотите <b>арендовать</b> или <b>купить</b>?",
        "en": "I’ll help you find property in Fergana.\nDo you want to <b>rent</b> or <b>buy</b>?",
    },
    "client_pick_deal": {
        "uz": "Tanlang: ijara yoki sotib olish.",
        "ru": "Выберите: аренда или покупка.",
        "en": "Choose: rent or buy.",
    },
    "ask_district": {
        "uz": "📍 Qaysi tumandan qidiryapsiz? Tanlang yoki oʻzingiznikini yozing:",
        "ru": "📍 В каком районе ищете? Выберите или напишите свой:",
        "en": "📍 Which district? Pick one or type your own:",
    },
    "district_write": {
        "uz": "Tuman nomini matn bilan yozing:",
        "ru": "Напишите название района текстом:",
        "en": "Type the district name:",
    },
    "ask_budget": {
        "uz": "💰 Byudjetingiz qancha? Summani yozing (masalan, 3000000):",
        "ru": "💰 Какой у вас бюджет? Напишите сумму (например, 3000000):",
        "en": "💰 What’s your budget? Enter an amount (e.g. 3000000):",
    },
    "budget_bad": {
        "uz": "Summa tushunarsiz. Raqam kiriting, masalan 3000000.",
        "ru": "Не понял сумму. Введите число, например 3000000.",
        "en": "Couldn’t read the amount. Enter a number, e.g. 3000000.",
    },
    "ask_rooms": {
        "uz": "🛏 Nechta xona kerak?",
        "ru": "🛏 Сколько комнат нужно?",
        "en": "🛏 How many rooms do you need?",
    },
    "rooms_bad": {
        "uz": "Xonalar sonini kiriting yoki tugmani tanlang.",
        "ru": "Введите число комнат или выберите кнопкой.",
        "en": "Enter the number of rooms or use a button.",
    },
    "ask_residents": {
        "uz": "👨‍👩‍👧 Kim yashaydi?",
        "ru": "👨‍👩‍👧 Кто будет жить?",
        "en": "👨‍👩‍👧 Who will live there?",
    },
    "ask_move_date": {
        "uz": "📅 Koʻchib oʻtishni qachon rejalashtiryapsiz? (KK.OO.YYYY)",
        "ru": "📅 Когда планируете заселение? (ДД.ММ.ГГГГ)",
        "en": "📅 When do you plan to move in? (DD.MM.YYYY)",
    },
    "date_bad": {
        "uz": "Sana tushunarsiz. KK.OO.YYYY formati yoki «Oʻtkazib yuborish».",
        "ru": "Не понял дату. Формат ДД.ММ.ГГГГ или нажмите «Пропустить».",
        "en": "Couldn’t read the date. Use DD.MM.YYYY or tap “Skip”.",
    },
    "ask_phone": {
        "uz": "📞 Bogʻlanish uchun telefon qoldiring (yoki tugma bilan yuboring):",
        "ru": "📞 Оставьте телефон для связи (или отправьте номер кнопкой):",
        "en": "📞 Leave a contact phone (or share it with the button):",
    },
    "phone_bad": {
        "uz": "Raqam notoʻgʻriga oʻxshaydi. Qayta kiriting, masalan +998901234567.",
        "ru": "Похоже, номер некорректный. Введите ещё раз, например +998901234567.",
        "en": "That number looks invalid. Try again, e.g. +998901234567.",
    },
    "confirm_title": {
        "uz": "Arizani tekshiring:",
        "ru": "Проверьте заявку:",
        "en": "Review your request:",
    },
    "request_accepted": {
        "uz": "✅ Ariza qabul qilindi! Rieltor tez orada bogʻlanadi.",
        "ru": "✅ Заявка принята! Риелтор скоро свяжется с вами.",
        "en": "✅ Request received! An agent will contact you soon.",
    },
    "request_cancelled": {
        "uz": "Ariza bekor qilindi. Qaytadan boshlash uchun /start bosing.",
        "ru": "Заявка отменена. Нажмите /start, чтобы начать заново.",
        "en": "Request cancelled. Tap /start to begin again.",
    },
    "matches_found": {
        "uz": "🔎 Mos variantlar topildi:",
        "ru": "🔎 Нашлись подходящие варианты:",
        "en": "🔎 We found matching options:",
    },
    "no_matches": {
        "uz": "Hozircha mos obyekt yoʻq — paydo boʻlishi bilan xabar beramiz.",
        "ru": "Пока подходящих объектов нет — сообщим, как появятся.",
        "en": "No matches yet — we’ll notify you when they appear.",
    },
    "ask_call_time": {
        "uz": "🕐 Rieltor qachon qoʻngʻiroq qilsa qulay?",
        "ru": "🕐 Когда вам удобно, чтобы риелтор позвонил?",
        "en": "🕐 When is it convenient for the agent to call?",
    },
    "pick_time": {
        "uz": "🕐 {period} — vaqtni tanlang:",
        "ru": "🕐 {period} — выберите время:",
        "en": "🕐 {period} — choose a time:",
    },
    "call_scheduled": {
        "uz": "✅ Ajoyib! Rieltor sizga {slot} da qoʻngʻiroq qiladi.",
        "ru": "✅ Отлично! Риелтор позвонит вам в {slot}.",
        "en": "✅ Great! The agent will call you at {slot}.",
    },
    # Превью заявки клиента
    "preview_request": {"uz": "<b>Sizning arizangiz</b>", "ru": "<b>Ваша заявка</b>", "en": "<b>Your request</b>"},
    "preview_deal": {"uz": "Bitim", "ru": "Сделка", "en": "Deal"},
    "preview_district": {"uz": "Tuman", "ru": "Район", "en": "District"},
    "preview_budget": {"uz": "Byudjet", "ru": "Бюджет", "en": "Budget"},
    "preview_rooms": {"uz": "Xonalar", "ru": "Комнат", "en": "Rooms"},
    "preview_residents": {"uz": "Kim yashaydi", "ru": "Кто будет жить", "en": "Residents"},
    "preview_move_in": {"uz": "Koʻchib oʻtish", "ru": "Заселение", "en": "Move-in"},
    "preview_phone": {"uz": "Telefon", "ru": "Телефон", "en": "Phone"},
    "deal_rent_word": {"uz": "Ijara", "ru": "Аренда", "en": "Rent"},
    "deal_buy_word": {"uz": "Sotib olish", "ru": "Покупка", "en": "Buy"},
    # Состав проживающих (значения)
    "res_one": {"uz": "Bir kishi", "ru": "Один", "en": "One person"},
    "res_couple": {"uz": "Er-xotin", "ru": "Пара", "en": "Couple"},
    "res_family": {"uz": "Bolali oila", "ru": "Семья с детьми", "en": "Family with kids"},
    "res_students": {"uz": "Talabalar", "ru": "Студенты", "en": "Students"},
    # Периоды звонка
    "period_morning": {"uz": "Ertalab", "ru": "Утро", "en": "Morning"},
    "period_day": {"uz": "Kunduzi", "ru": "День", "en": "Day"},
    "period_evening": {"uz": "Kechqurun", "ru": "Вечер", "en": "Evening"},
    # --- Собственник ---
    "owner_intro": {
        "uz": (
            "🏠 Obyektni joylaymiz. Bitim turini tanlang —\n"
            "<i>yoki obyektni bitta xabarda yozing, masalan:</i>\n"
            "<code>2x margʻilon 450000 sotuv egasi +998901234567</code>"
        ),
        "ru": (
            "🏠 Разместим объект. Выберите тип сделки —\n"
            "<i>или опишите объект одним сообщением, например:</i>\n"
            "<code>2к маргилан 450000 продажа хозяин +998901234567</code>"
        ),
        "en": (
            "🏠 Let’s post your property. Choose the deal type —\n"
            "<i>or describe it in a single message, e.g.:</i>\n"
            "<code>2r margilan 450000 sale owner +998901234567</code>"
        ),
    },
    "owner_deal_rent": {"uz": "🔑 Ijaraga", "ru": "🔑 Аренда", "en": "🔑 Rent out"},
    "owner_deal_sale": {"uz": "🏷 Sotuv", "ru": "🏷 Продажа", "en": "🏷 Sale"},
    "owner_kind_q": {"uz": "Obyekt turi?", "ru": "Вид объекта?", "en": "Property type?"},
    "owner_quick_fail": {
        "uz": "Hammasini tanib boʻlmadi. Bitim turini tugma bilan tanlang, bosqichma-bosqich toʻldiramiz.",
        "ru": "Не удалось разобрать всё. Выберите тип сделки кнопкой и заполним по шагам.",
        "en": "Couldn’t parse everything. Pick the deal type and we’ll fill it step by step.",
    },
    "owner_quick_ok": {
        "uz": "✅ Eʼlon matndan tanildi. Tekshiring:",
        "ru": "✅ Распознал объявление из текста. Проверьте:",
        "en": "✅ Parsed the listing from text. Please check:",
    },
    "ask_address": {"uz": "📍 Obyekt manzilini kiriting:", "ru": "📍 Укажите адрес объекта:", "en": "📍 Enter the property address:"},
    "ask_owner_district": {"uz": "Tuman?", "ru": "Район?", "en": "District?"},
    "owner_ask_rooms": {"uz": "🛏 Nechta xona?", "ru": "🛏 Сколько комнат?", "en": "🛏 How many rooms?"},
    "ask_area": {"uz": "📐 Maydoni, m²?", "ru": "📐 Площадь, м²?", "en": "📐 Area, m²?"},
    "ask_floor": {"uz": "🏢 Qavat?", "ru": "🏢 Этаж?", "en": "🏢 Floor?"},
    "ask_floors": {"uz": "Bino qavatliligi?", "ru": "Этажность дома?", "en": "Total floors?"},
    "num_bad": {"uz": "Raqam kiriting yoki «Oʻtkazib yuborish».", "ru": "Введите число или «Пропустить».", "en": "Enter a number or “Skip”."},
    "area_bad": {"uz": "Maydonni raqam bilan kiriting yoki «Oʻtkazib yuborish».", "ru": "Введите площадь числом или «Пропустить».", "en": "Enter the area as a number or “Skip”."},
    "ask_renovation": {"uz": "🛠 Taʼmir?", "ru": "🛠 Ремонт?", "en": "🛠 Renovation?"},
    "reno_rough": {"uz": "Qora taʼmir", "ru": "Черновая", "en": "Rough finish"},
    "reno_cosmetic": {"uz": "Kosmetik", "ru": "Косметический", "en": "Cosmetic"},
    "reno_euro": {"uz": "Yevro taʼmir", "ru": "Евроремонт", "en": "Euro renovation"},
    "reno_designer": {"uz": "Dizaynerlik", "ru": "Дизайнерский", "en": "Designer"},
    "ask_furniture": {"uz": "🛋 Mebel bormi?", "ru": "🛋 Мебель есть?", "en": "🛋 Is there furniture?"},
    "ask_appliances": {"uz": "🔌 Maishiy texnika?", "ru": "🔌 Бытовая техника?", "en": "🔌 Appliances?"},
    "ask_gas": {"uz": "🔥 Gaz?", "ru": "🔥 Газ?", "en": "🔥 Gas?"},
    "ask_water": {"uz": "💧 Suv?", "ru": "💧 Вода?", "en": "💧 Water?"},
    "ask_electricity": {"uz": "💡 Elektr?", "ru": "💡 Электричество?", "en": "💡 Electricity?"},
    "ask_internet": {"uz": "🌐 Internet?", "ru": "🌐 Интернет?", "en": "🌐 Internet?"},
    "ask_docs": {"uz": "📄 Hujjatlar joyidami?", "ru": "📄 Документы в порядке?", "en": "📄 Documents in order?"},
    "ask_mortgage": {"uz": "🏦 Ipoteka/kredit mumkinmi?", "ru": "🏦 Возможна ипотека/кредит?", "en": "🏦 Mortgage/credit possible?"},
    "ask_price": {"uz": "💰 Narxi?", "ru": "💰 Цена?", "en": "💰 Price?"},
    "price_bad": {"uz": "Narxni raqam bilan kiriting, masalan 45000000.", "ru": "Введите цену числом, например 45000000.", "en": "Enter the price as a number, e.g. 45000000."},
    "ask_negotiable": {"uz": "🤝 Savdo mumkinmi?", "ru": "🤝 Торг уместен?", "en": "🤝 Is the price negotiable?"},
    "owner_ask_phone": {"uz": "📞 Egasining aloqa telefoni:", "ru": "📞 Контактный телефон собственника:", "en": "📞 Owner’s contact phone:"},
    "owner_phone_bad": {"uz": "Notoʻgʻri raqam. Masalan: +998901234567.", "ru": "Некорректный номер. Пример: +998901234567.", "en": "Invalid number. Example: +998901234567."},
    "ask_photos": {
        "uz": "📷 Obyekt suratlarini yuboring (bir nechta/albom mumkin), soʻng «Tayyor».",
        "ru": "📷 Пришлите фотографии объекта (можно несколько/альбомом), затем «Готово».",
        "en": "📷 Send property photos (several/an album is fine), then “Done”.",
    },
    "photo_accepted": {
        "uz": "Surat qabul qilindi ({n}). Yana yoki «Tayyor».",
        "ru": "Фото принято ({n}). Ещё или «Готово».",
        "en": "Photo received ({n}). More or “Done”.",
    },
    "ask_video": {
        "uz": "🎥 Video yuboring (ixtiyoriy) yoki oʻtkazib yuboring.",
        "ru": "🎥 Пришлите видео (необязательно) или пропустите.",
        "en": "🎥 Send a video (optional) or skip.",
    },
    "owner_confirm_title": {"uz": "Eʼlonni tekshiring:", "ru": "Проверьте объявление:", "en": "Review the listing:"},
    "owner_cancelled": {
        "uz": "Joylash bekor qilindi. Qaytadan: /add.",
        "ru": "Размещение отменено. Команда /add — начать заново.",
        "en": "Posting cancelled. Use /add to start over.",
    },
    "dup_warning": {
        "uz": "⚠️ <b>Ehtimoliy dublikat!</b>\n\nQuyidagiga oʻxshaydi:\n{brief}\n\nBaribir qoʻshaymi?",
        "ru": "⚠️ <b>Возможный дубль!</b>\n\nПохож на:\n{brief}\n\nВсё равно добавить?",
        "en": "⚠️ <b>Possible duplicate!</b>\n\nSimilar to:\n{brief}\n\nAdd anyway?",
    },
    "dup_cancelled": {"uz": "Qoʻshish bekor qilindi.", "ru": "Добавление отменено.", "en": "Adding cancelled."},
    "sent_to_moderation": {
        "uz": "✅ {id} obyekti moderatsiyaga yuborildi. Eʼlon qilinishi haqida xabar beramiz.",
        "ru": "✅ Объект {id} отправлен на модерацию. Мы сообщим о публикации.",
        "en": "✅ Listing {id} sent for moderation. We’ll notify you when it’s published.",
    },
}


def t(key: str, lang: str | None, **kwargs) -> str:
    lang = normalize(lang)
    variants = MESSAGES.get(key, {})
    text = variants.get(lang) or variants.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
