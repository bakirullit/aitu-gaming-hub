import logging
from aiogram import Router

from core.context import CoreContext
from plugins.auth.rbac import (
    build_user_profile_data,
    clean_contact_markup,
    get_user_home_screen,
)
from plugins.auth.routers import (
    setup_menu_router,
    setup_onboarding_router,
    setup_profile_router,
)
from plugins.auth.states import AuthStates

logger = logging.getLogger("plugins.auth.router")

router = Router(name="auth_router")


def setup_auth_routes(core: CoreContext) -> Router:
    """
    Modular coordinator router for Auth plugin.
    Decomposed into specialized sub-routers:
      - Menu: Navigation, /start, private chat fallback
      - Onboarding: Registration flow, roles, OTP, Valve OpenID
      - Profile: User profile, Steam linking, student upgrade, account deletion
    """
    auth_root = Router(name="auth_router")
    auth_root.include_router(setup_menu_router(core))
    auth_root.include_router(setup_onboarding_router(core))
    auth_root.include_router(setup_profile_router(core))
    return auth_root


__all__ = [
    "AuthStates",
    "build_user_profile_data",
    "clean_contact_markup",
    "get_user_home_screen",
    "router",
    "setup_auth_routes",
]
