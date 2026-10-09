from plugins.auth.routers.menu import setup_menu_router
from plugins.auth.routers.onboarding import setup_onboarding_router
from plugins.auth.routers.profile import setup_profile_router

__all__ = [
    "setup_menu_router",
    "setup_onboarding_router",
    "setup_profile_router",
]
