import logging
from aiogram import Router
from common.dtos.events import UserVerifiedEvent
from core.context import CoreContext
from core.protocols import PluginProtocol
from plugins.minecraft.router import setup_minecraft_routes

logger = logging.getLogger("plugins.minecraft.plugin")


class MinecraftPlugin(PluginProtocol):
    """Minecraft esports & campus server integration plugin."""
    name: str = "minecraft"

    def __init__(self) -> None:
        self._router: Router | None = None

    async def _on_user_verified(self, event: UserVerifiedEvent) -> None:
        """Domain Event subscriber: fired when a student passes academic verification."""
        logger.info(
            f"MinecraftPlugin received UserVerifiedEvent for user {event.telegram_id} "
            f"(Student ID: {event.student_id}). Student is now eligible for server whitelist."
        )

    async def setup(self, core: CoreContext) -> None:
        """Initialize plugin, register event bus subscriptions, and mount routes."""
        logger.info("Setting up MinecraftPlugin...")
        core.event_bus.subscribe(UserVerifiedEvent, self._on_user_verified)
        self._router = setup_minecraft_routes(core)

    async def teardown(self) -> None:
        """Clean up plugin resources."""
        logger.info("Tearing down MinecraftPlugin...")
        self._router = None

    def get_router(self) -> Router:
        """Return isolated Aiogram router for Minecraft."""
        if self._router is None:
            raise RuntimeError("MinecraftPlugin.setup() must be called before get_router()")
        return self._router
