"""Конфигурация приложения и глобальные константы."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

# --- Константы приложения ---
TIMEZONE = "Asia/Tashkent"          # часовой пояс планировщика и напоминаний
BUMP_INTERVAL_DAYS = 3              # интервал автоподнятия объявлений (дни)


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
