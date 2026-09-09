from dataclasses import dataclass
import logging
from aiogram import Bot, Dispatcher
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from common.config import Settings
from core.protocols import EventBusProtocol, NavigatorProtocol


@dataclass(frozen=True)
class CoreContext:
    """Typed runtime context injected into every plugin during setup."""
    bot: Bot
    dp: Dispatcher
    redis: Redis
    db_session_factory: async_sessionmaker[AsyncSession]
    event_bus: EventBusProtocol
    navigator: NavigatorProtocol
    settings: Settings
    logger: logging.Logger
