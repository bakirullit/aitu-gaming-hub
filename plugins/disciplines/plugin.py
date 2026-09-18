import logging
from aiogram import Router
from core.context import CoreContext
from core.protocols import PluginProtocol
from plugins.disciplines.router import setup_disciplines_routes

logger = logging.getLogger("plugins.disciplines.plugin")


class DisciplinesPlugin(PluginProtocol):
    """Dynamic esports disciplines catalog with reactive RBAC navigation."""
    name: str = "disciplines"

    def __init__(self) -> None:
        self._router: Router | None = None

    async def setup(self, core: CoreContext) -> None:
        """Initialize plugin and mount routes."""
        logger.info("Setting up DisciplinesPlugin...")
        self._router = setup_disciplines_routes(core)

    async def teardown(self) -> None:
        """Clean up plugin resources."""
        logger.info("Tearing down DisciplinesPlugin...")
        self._router = None

    def get_router(self) -> Router:
        """Return isolated Aiogram router for Disciplines."""
        if self._router is None:
            raise RuntimeError("DisciplinesPlugin.setup() must be called before get_router()")
        return self._router
