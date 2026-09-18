import logging
from aiogram import Router
from core.context import CoreContext
from core.protocols import PluginProtocol
from plugins.tournaments.router import setup_tournaments_routes

logger = logging.getLogger("plugins.tournaments.plugin")


class TournamentsPlugin(PluginProtocol):
    """Esports tournament booking Anchor Wizard and management gateway plugin."""
    name: str = "tournaments"

    def __init__(self) -> None:
        self._router: Router | None = None

    async def setup(self, core: CoreContext) -> None:
        """Initialize plugin and mount routes."""
        logger.info("Setting up TournamentsPlugin...")
        self._router = setup_tournaments_routes(core)

    async def teardown(self) -> None:
        """Clean up plugin resources."""
        logger.info("Tearing down TournamentsPlugin...")
        self._router = None

    def get_router(self) -> Router:
        """Return isolated Aiogram router for Tournaments."""
        if self._router is None:
            raise RuntimeError("TournamentsPlugin.setup() must be called before get_router()")
        return self._router
