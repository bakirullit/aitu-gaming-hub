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
    BOT_USERNAME: str = Field(default="aitu_gaming_bot")
    WEBHOOK_URL: str | None = None
    WEBHOOK_PATH: str = "/webhook"
    WEBHOOK_SECRET: str | None = None

    # PostgreSQL Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/aitu_gaming_hub")

    # Redis Cache & Sessions
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Minecraft Server Settings (RCON & Public Server Info)
    MINECRAFT_HOST: str = "127.0.0.1"
    MINECRAFT_RCON_PORT: int = 25575
    MINECRAFT_RCON_PASSWORD: str = ""
    MINECRAFT_RCON_TIMEOUT: float = 3.0
    MINECRAFT_SERVER_IP: str = "mc.aitu-gaming.y-not-devs.com:25565"
    MINECRAFT_SERVER_NAME: str = "AITU SMP [Create 1.21.1 NeoForge]"
    MINECRAFT_SERVER_VERSION: str = "Create 1.21.1 NeoForge"
    MINECRAFT_SERVER_MOTD: str = "Welcome to AITU Gaming Network!"
    MINECRAFT_MAX_PLAYERS: int = 50
    MINECRAFT_DEFAULT_ONLINE: int = 14
    MINECRAFT_MODPACK_URL: str = "https://github.com/aitu-gaming-hub/minecraft-client/releases"
    MINECRAFT_CHANNEL_URL: str = "https://t.me/aitu_minecraft"
    MINECRAFT_CHAT_URL: str = "https://t.me/aitu_minecraft_chat"

    # Helpdesk & Tournament Settings
    HELPDESK_ADMIN_CHAT_ID: int | None = None
    TOURNAMENT_ADMIN_CHAT_ID: int | None = None

    # Web Admin Auth
    JWT_SECRET: str = Field(default="dev_secret_key_change_in_production")
    JWT_EXPIRE_HOURS: int = 12

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_webhook_enabled(self) -> bool:
        return bool(self.WEBHOOK_URL)


settings = Settings()
