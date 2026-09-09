import logging
from aiogram import Router
from core.context import CoreContext
from core.protocols import PluginProtocol
from plugins.helpdesk.router import setup_helpdesk_routes

logger = logging.getLogger("plugins.helpdesk.plugin")


class HelpdeskPlugin(PluginProtocol):
    """Support ticketing and admin channel reply bridge plugin."""
    name: str = "helpdesk"

    def __init__(self) -> None:
        self._router: Router | None = None

    async def setup(self, core: CoreContext) -> None:
        """Initialize plugin and mount routes."""
        logger.info("Setting up HelpdeskPlugin...")
        self._router = setup_helpdesk_routes(core)

    async def teardown(self) -> None:
        """Clean up plugin resources."""
        logger.info("Tearing down HelpdeskPlugin...")
        self._router = None

    def get_router(self) -> Router:
        """Return isolated Aiogram router for Helpdesk."""
        if self._router is None:
            raise RuntimeError("HelpdeskPlugin.setup() must be called before get_router()")
        return self._router
