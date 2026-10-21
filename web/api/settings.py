import json
import logging
from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.models.user import User
from core.lifespan import runtime
from web.api.dependencies import get_current_admin, get_db_session

logger = logging.getLogger("web.api.settings")

settings_admin_router = APIRouter(prefix="/settings", tags=["Admin Settings"])

SETTINGS_REDIS_KEY = "club:platform_settings"

DEFAULT_SETTINGS = {
    "club_name": "AITU Gaming Hub",
    "bot_username": getattr(settings, "BOT_USERNAME", "aitu_gaming_bot"),
    "channel_url": "https://t.me/aitu_gaming",
    "discord_url": "https://discord.gg/aitu-gaming",
    "support_chat_url": "https://t.me/aitu_gaming_help",
    "minecraft_server_host": getattr(settings, "MINECRAFT_SERVER_IP", "mc.aitu-gaming.y-not-devs.com:25565"),
    "minecraft_version": getattr(settings, "MINECRAFT_SERVER_VERSION", "Create 1.21.1 NeoForge"),
    "otp_bypass_enabled": True,
    "maintenance_mode": False,
    "registration_open": True,
}


class SettingsUpdateRequest(BaseModel):
    club_name: str | None = None
    bot_username: str | None = None
    channel_url: str | None = None
    discord_url: str | None = None
    support_chat_url: str | None = None
    minecraft_server_host: str | None = None
    minecraft_version: str | None = None
    otp_bypass_enabled: bool | None = None
    maintenance_mode: bool | None = None
    registration_open: bool | None = None


@settings_admin_router.get("")
async def get_platform_settings(
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    current = dict(DEFAULT_SETTINGS)
    if runtime.redis:
        try:
            cached = await runtime.redis.get(SETTINGS_REDIS_KEY)
            if cached:
                current.update(json.loads(cached))
        except Exception as exc:
            logger.warning(f"Could not load settings from Redis: {exc}")

    return current


@settings_admin_router.post("")
async def update_platform_settings(
    payload: SettingsUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    current = dict(DEFAULT_SETTINGS)
    if runtime.redis:
        try:
            cached = await runtime.redis.get(SETTINGS_REDIS_KEY)
            if cached:
                current.update(json.loads(cached))
        except Exception:
            pass

    updates = payload.model_dump(exclude_unset=True)
    current.update(updates)

    if runtime.redis:
        try:
            await runtime.redis.set(SETTINGS_REDIS_KEY, json.dumps(current))
        except Exception as exc:
            logger.warning(f"Could not save settings to Redis: {exc}")

    return {
        "status": "ok",
        "settings": current,
    }
