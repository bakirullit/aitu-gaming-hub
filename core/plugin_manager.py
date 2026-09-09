import logging
from core.context import CoreContext
from core.protocols import PluginProtocol

logger = logging.getLogger("core.plugin_manager")


class PluginManager:
    """Narrow Plugin Manager: handles setup, router mounting, and teardown lifecycle."""

    def __init__(self) -> None:
        self._plugins: list[PluginProtocol] = []
        self._active_plugins: list[PluginProtocol] = []

    def register(self, plugin: PluginProtocol) -> None:
        """Register a plugin instance before system startup."""
        self._plugins.append(plugin)
        logger.debug(f"Registered plugin candidate: '{plugin.name}'")

    async def setup_all(self, core: CoreContext) -> None:
        """Execute setup for all registered plugins and attach their routers to Dispatcher."""
        logger.info(f"Initializing {len(self._plugins)} registered plugin(s)...")

        for plugin in self._plugins:
            try:
                await plugin.setup(core)
                router = plugin.get_router()
                core.dp.include_router(router)
                self._active_plugins.append(plugin)
                logger.info(f"Plugin '{plugin.name}' successfully mounted and active.")
            except Exception as exc:
                # Failure isolation boundary: an external service failure must not crash startup
                logger.error(
                    f"Failed to setup plugin '{plugin.name}', skipping: {exc}",
                    exc_info=True,
                )

    async def teardown_all(self) -> None:
        """Gracefully teardown all active plugins on SIGTERM or application shutdown."""
        logger.info(f"Tearing down {len(self._active_plugins)} active plugin(s)...")

        for plugin in reversed(self._active_plugins):
            try:
                await plugin.teardown()
                logger.info(f"Plugin '{plugin.name}' torn down successfully.")
            except Exception as exc:
                logger.error(
                    f"Error during teardown of plugin '{plugin.name}': {exc}",
                    exc_info=True,
                )
        self._active_plugins.clear()

    @property
    def active_plugins(self) -> list[str]:
        """List of names of currently active plugins."""
        return [p.name for p in self._active_plugins]
