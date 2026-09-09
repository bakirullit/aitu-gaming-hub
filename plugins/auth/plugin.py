import logging
from aiogram import Router
from core.context import CoreContext
from core.protocols import PluginProtocol
from plugins.auth.router import setup_auth_routes

logger = logging.getLogger("plugins.auth.plugin")


class AuthPlugin(PluginProtocol):
    """Auth & Student Identity Plugin for AITU student verification."""
    name: str = "auth"

    def __init__(self) -> None:
        self._router: Router | None = None

    async def setup(self, core: CoreContext) -> None:
        """Initialize plugin routers and dependencies."""
        logger.info("Setting up AuthPlugin...")
        self._router = setup_auth_routes(core)

    async def teardown(self) -> None:
        """Clean up plugin resources."""
        logger.info("Tearing down AuthPlugin...")
        self._router = None

    def get_router(self) -> Router:
        """Return isolated Aiogram router for Auth."""
        if self._router is None:
            raise RuntimeError("AuthPlugin.setup() must be called before get_router()")
        return self._router
