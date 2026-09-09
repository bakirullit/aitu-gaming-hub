from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Telegram Bot
    BOT_TOKEN: str = Field(default="mock_token_for_tests")
    WEBHOOK_URL: str | None = None
    WEBHOOK_PATH: str = "/webhook"
    WEBHOOK_SECRET: str | None = None

    # PostgreSQL Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/aitu_gaming_hub")

    # Redis Cache & Sessions
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Minecraft Server Settings (RCON)
    MINECRAFT_HOST: str = "127.0.0.1"
    MINECRAFT_RCON_PORT: int = 25575
    MINECRAFT_RCON_PASSWORD: str = ""
    MINECRAFT_RCON_TIMEOUT: float = 3.0

    # Helpdesk Settings
    HELPDESK_ADMIN_CHAT_ID: int | None = None

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_webhook_enabled(self) -> bool:
        return bool(self.WEBHOOK_URL)


settings = Settings()
