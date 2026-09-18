from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import asyncio
import logging
from typing import Any
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from redis.asyncio import Redis, from_url as redis_from_url

from common.config import settings
from common.database.base import Base
from common.database.session import db_manager
import common.models  # noqa: F401 - Register all models with Base.metadata
from core.context import CoreContext
from core.event_bus import InMemoryEventBus
from core.navigation.navigator import Navigator
from core.plugin_manager import PluginManager
from core.middlewares.garbage_collector import GarbageCollectorMiddleware
from core.middlewares.user_lock import UserLockMiddleware
from core.middlewares.db_session import DBSessionMiddleware

# Concrete Plugins
from plugins.auth.plugin import AuthPlugin
from plugins.minecraft.plugin import MinecraftPlugin
from plugins.helpdesk.plugin import HelpdeskPlugin
from plugins.tournaments.plugin import TournamentsPlugin
from plugins.disciplines.plugin import DisciplinesPlugin


logger = logging.getLogger("core.lifespan")


class ApplicationRuntime:
    """Singleton holding initialized runtime components for FastAPI routes."""
    def __init__(self) -> None:
        self.bot: Bot | None = None
        self.dp: Dispatcher | None = None
        self.redis: Redis | None = None
        self.core: CoreContext | None = None
        self.plugin_manager: PluginManager | None = None
        self.polling_task: asyncio.Task[Any] | None = None


runtime = ApplicationRuntime()


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.
    Coordinates lifecycle of Database, Redis, Telegram Bot, Event Bus, and Plugins.
    """
    logger.info("Initializing AITU Gaming Hub Application Core...")

    # 1. Initialize Database & Redis
    db_manager.init()
    if db_manager._engine is not None:
        async with db_manager._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas and tables verified/created.")

    redis_client = redis_from_url(settings.REDIS_URL, decode_responses=True)

    # 2. Initialize Telegram Bot & Dispatcher
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # 3. Initialize Core Subsystems
    event_bus = InMemoryEventBus()
    navigator = Navigator(bot=bot, redis=redis_client)
    plugin_manager = PluginManager()

    core = CoreContext(
        bot=bot,
        dp=dp,
        redis=redis_client,
        db_session_factory=db_manager.session_factory,
        event_bus=event_bus,
        navigator=navigator,
        settings=settings,
        logger=logger,
    )

    # 4. Attach Global Middlewares
    dp.message.outer_middleware(GarbageCollectorMiddleware())
    dp.callback_query.outer_middleware(UserLockMiddleware(redis=redis_client))
    dp.update.middleware(DBSessionMiddleware(session_factory=db_manager.session_factory))

    # 5. Register and Setup Concrete Plugins
    plugin_manager.register(AuthPlugin())
    plugin_manager.register(MinecraftPlugin())
    plugin_manager.register(HelpdeskPlugin())
    plugin_manager.register(TournamentsPlugin())
    plugin_manager.register(DisciplinesPlugin())

    await plugin_manager.setup_all(core)



    # Store in runtime container
    runtime.bot = bot
    runtime.dp = dp
    runtime.redis = redis_client
    runtime.core = core
    runtime.plugin_manager = plugin_manager

    # 6. Configure Telegram Ingress (Webhook vs Polling)
    if settings.is_webhook_enabled:
        webhook_url = f"{settings.WEBHOOK_URL.rstrip('/')}{settings.WEBHOOK_PATH}"
        logger.info(f"Setting Telegram webhook to: {webhook_url}")
        try:
            await bot.set_webhook(
                url=webhook_url,
                secret_token=settings.WEBHOOK_SECRET,
                drop_pending_updates=True,
            )
        except Exception as exc:
            logger.error(f"Failed to set webhook on startup: {exc}")
    else:
        logger.info("Webhook URL not configured. Starting Aiogram background polling for local dev...")
        runtime.polling_task = asyncio.create_task(
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        )

    logger.info("AITU Gaming Hub Core is ready to process traffic.")
    try:
        yield
    finally:
        logger.info("Initiating graceful shutdown...")

        # Stop polling if active
        if runtime.polling_task and not runtime.polling_task.done():
            runtime.polling_task.cancel()
            try:
                await runtime.polling_task
            except asyncio.CancelledError:
                pass

        # Teardown plugins
        if plugin_manager:
            await plugin_manager.teardown_all()

        # Close Telegram session
        if bot.session:
            await bot.session.close()

        # Close Redis
        if redis_client:
            await redis_client.aclose()

        # Close Database Engine
        await db_manager.close()

        logger.info("AITU Gaming Hub shutdown complete.")


def register_ingress_routes(app: FastAPI) -> None:
    """Register HTTP Ingress routes: Liveness (/healthz), Readiness (/ready), and Webhook."""

    @app.get("/healthz", summary="Liveness Probe", status_code=status.HTTP_200_OK)
    async def liveness() -> dict[str, str]:
        """Kubernetes/Orchestration Liveness probe: verifies Python asyncio loop is responsive."""
        return {"status": "alive"}

    @app.get("/ready", summary="Readiness Probe")
    async def readiness() -> JSONResponse:
        """
        Kubernetes/Orchestration Readiness probe:
        Verifies active connectivity to PostgreSQL and Redis.
        Returns 200 OK when ready to serve traffic, 503 Service Unavailable if unhealthy.
        """
        db_healthy = await db_manager.ping()

        redis_healthy = False
        if runtime.redis:
            try:
                redis_healthy = bool(await runtime.redis.ping())
            except Exception as exc:
                logger.warning(f"Redis readiness ping failed: {exc}")

        active_plugins = runtime.plugin_manager.active_plugins if runtime.plugin_manager else []

        payload = {
            "status": "ready" if (db_healthy and redis_healthy) else "unhealthy",
            "database": "healthy" if db_healthy else "unreachable",
            "redis": "healthy" if redis_healthy else "unreachable",
            "active_plugins": active_plugins,
        }

        status_code = status.HTTP_200_OK if (db_healthy and redis_healthy) else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(content=payload, status_code=status_code)

    @app.post(settings.WEBHOOK_PATH, summary="Telegram Webhook Ingress")
    async def telegram_webhook(request: Request) -> Response:
        """Ingress endpoint for Telegram updates via Webhook."""
        if not runtime.bot or not runtime.dp:
            raise HTTPException(status_code=503, detail="Core runtime not initialized")

        # Verify secret token if configured
        if settings.WEBHOOK_SECRET:
            token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if token != settings.WEBHOOK_SECRET:
                raise HTTPException(status_code=401, detail="Invalid secret token")

        data = await request.json()
        update = Update.model_validate(data, context={"bot": runtime.bot})
        await runtime.dp.feed_update(bot=runtime.bot, update=update)
        return Response(status_code=status.HTTP_200_OK)
