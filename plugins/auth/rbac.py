import logging
from typing import Any
from aiogram.fsm.context import FSMContext
from common.dtos.screen import Screen
from common.models.user import User
from core.context import CoreContext
from plugins.auth.screens import get_authorized_menu_screen, get_club_info_screen

logger = logging.getLogger("plugins.auth.rbac")


def get_user_home_screen(user: User | None) -> Screen:
    """
    Renders the appropriate home screen based on the user's registration and RBAC roles.
    If the user has completed onboarding, renders the role-filtered authorized menu;
    otherwise renders the guest welcome/club info screen.
    """
    if user and user.full_name:
        return get_authorized_menu_screen(
            full_name=user.full_name,
            role=user.role,
            is_verified=user.is_verified,
            has_steam=bool(user.steam_id),
            roles=getattr(user, "roles", []) or [],
            is_discipline_admin=getattr(user, "is_discipline_admin", False),
            is_staff=getattr(user, "is_staff", False),
        )
    return get_club_info_screen()


def build_user_profile_data(user: User | None, fallback_from_user: Any = None) -> dict[str, Any]:
    """
    Extracts structured user profile data for rendering the profile screen,
    with fallbacks to Telegram from_user when database record attributes are missing.
    """
    first_name = (
        user.first_name
        if user and user.first_name
        else (getattr(fallback_from_user, "first_name", "") if fallback_from_user else "")
    )
    last_name = (
        user.last_name
        if user and user.last_name
        else (getattr(fallback_from_user, "last_name", "") if fallback_from_user else "")
    )
    username = (
        user.username
        if user and user.username
        else (getattr(fallback_from_user, "username", None) if fallback_from_user else None)
    )

    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": user.full_name if user else None,
        "username": username,
        "barcode": user.barcode if user else None,
        "phone_number": user.phone_number if user else None,
        "email": user.email if user else None,
        "steam_id": user.steam_id if user else None,
        "is_verified": user.is_verified if user else False,
        "role": user.role if user else "guest",
        "roles": getattr(user, "roles", []) or [] if user else [],
    }


async def clean_contact_markup(core: CoreContext, chat_id: int, state: FSMContext) -> None:
    """Helper to remove phone contact reply keyboard if active."""
    data = await state.get_data()
    msg_id = data.get("phone_reply_msg_id")
    if msg_id:
        try:
            await core.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass
        await state.update_data(phone_reply_msg_id=None)
