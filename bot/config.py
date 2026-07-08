"""Конфигурация приложения и глобальные константы."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

# --- Константы приложения ---
TIMEZONE = "Asia/Tashkent"          # часовой пояс планировщика и напоминаний
BUMP_INTERVAL_DAYS = 3              # интервал автоподнятия объявлений (дни)

# --- Оформление объявления (премиум-эмодзи) ---
# ВАЖНО: подставьте реальные ID кастомных (премиум) эмодзи вашего набора.
# Пока стоят заглушки — Telegram покажет базовые эмодзи из alt-текста.
PREMIUM_EMOJI = {
    "building": "0",   # 🏢 премиум-здание
    "siren": "0",      # 🚨 мигалка (#Срочно)
    "pin": "0",        # 📍 локация
    "door": "0",       # 🚪 дверь (комнаты)
    "tools": "0",      # 🛠 ремонт
    "lightning": "0",  # ⚡️ молния (коммуникации)
    "money": "0",      # 💰 деньги (цена)
    "phone": "0",      # 📞 телефон
}

# Контакты агентства (номер, username) — отображаются в спойлере
AGENCY_CONTACTS = [
    ("+998916993133", "Aziko_3133"),
    ("+998930866466", "Bek_6466"),
]

# Ссылки в подвале объявления
CHANNEL_URL = "https://t.me/fargona_UYJOY0"
BOT_PUBLISH_URL = "https://t.me/fargona_realtor_bot?start=add"


class Settings:
    def __init__(self) -> None:
        # Telegram
        self.bot_token: str = os.environ["BOT_TOKEN"]
        self.channel_id: str = os.getenv("CHANNEL_ID", "")
        self.admin_ids: list[int] = self._parse_admin_ids(os.getenv("ADMIN_TELEGRAM_ID", ""))

        # Инфраструктура
        self.database_url: str = os.environ["DATABASE_URL"]
        self.redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

        # Anthropic
        self.anthropic_api_key: str = os.environ["ANTHROPIC_API_KEY"]
        self.ai_model: str = os.getenv("AI_MODEL", "claude-opus-4-8")

        # Константы (дублируем на объекте настроек для удобного доступа)
        self.timezone: str = TIMEZONE
        self.bump_interval_days: int = BUMP_INTERVAL_DAYS

    @staticmethod
    def _parse_admin_ids(raw: str) -> list[int]:
        return [int(x) for x in raw.replace(" ", "").split(",") if x.isdigit()]

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids


@lru_cache
def get_settings() -> Settings:
    return Settings()
