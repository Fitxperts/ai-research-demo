"""Конфигурация приложения, загружаемая из переменных окружения."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str = Field(alias="BOT_TOKEN")
    publish_channel_id: int = Field(alias="PUBLISH_CHANNEL_ID")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")

    # PostgreSQL
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_host: str = Field("db", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")

    # Redis
    redis_host: str = Field("redis", alias="REDIS_HOST")
    redis_port: int = Field(6379, alias="REDIS_PORT")
    redis_db: int = Field(0, alias="REDIS_DB")

    # Anthropic
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    ai_model: str = Field("claude-opus-4-8", alias="AI_MODEL")

    # Планировщик
    bump_interval_hours: int = Field(24, alias="BUMP_INTERVAL_HOURS")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> list[int]:
        if isinstance(value, str):
            return [int(x) for x in value.replace(" ", "").split(",") if x]
        if isinstance(value, (list, tuple)):
            return [int(x) for x in value]
        return []

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
