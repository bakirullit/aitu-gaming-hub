"""
Minecraft Discipline Hub and State Machine Module.
Exposes StatesGroup and re-exports Minecraft discipline sub-modules for clean integration.
"""

from aiogram.fsm.state import State, StatesGroup
from plugins.minecraft.router import (
    MinecraftProfileSG,
    ChangeMinecraftNick,
    setup_minecraft_routes,
    router as minecraft_router,
)
from plugins.minecraft.screens import (
    get_minecraft_home_screen,
    get_minecraft_servers_screen,
    get_minecraft_profile_screen,
    get_minecraft_friends_hub_screen,
    get_minecraft_channel_screen,
)

__all__ = [
    "MinecraftProfileSG",
    "ChangeMinecraftNick",
    "setup_minecraft_routes",
    "minecraft_router",
    "get_minecraft_home_screen",
    "get_minecraft_servers_screen",
    "get_minecraft_profile_screen",
    "get_minecraft_friends_hub_screen",
    "get_minecraft_channel_screen",
]
