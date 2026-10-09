import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.user import User
from core.context import CoreContext
from plugins.auth.rbac import build_user_profile_data
from plugins.auth.screens import (
    get_account_deleted_screen,
    get_barcode_screen,
    get_delete_account_confirm_screen,
    get_profile_screen,
    get_steam_screen,
)
from plugins.auth.states import AuthStates
from services.steam_service import SteamService
from services.user_service import UserService

logger = logging.getLogger("plugins.auth.routers.profile")


def setup_profile_router(core: CoreContext) -> Router:
    """Configures user profile, Steam linking, student upgrade, and account deletion routes."""
    router = Router(name="auth_profile_router")

    # =========================================================================
    # View Profile
    # =========================================================================

    @router.callback_query(F.data == "auth:profile")
    async def cb_profile(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        user_data = build_user_profile_data(user, callback.from_user)
        screen = get_profile_screen(user_data)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:profile",
            push_to_history=True,
        )
        await callback.answer()

    # =========================================================================
    # Link Steam from Profile
    # =========================================================================

    @router.callback_query(F.data == "auth:profile:link_steam")
    async def cb_profile_link_steam(callback: CallbackQuery, state: FSMContext) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        await state.set_state(AuthStates.waiting_steam)

        steam_service = SteamService(settings_obj=core.settings)
        login_state = await steam_service.create_login_state(
            telegram_id=user_id,
            redis=core.redis,
            extra_data={"is_profile_link": True},
        )
        steam_bridge_url = steam_service.build_bridge_url(login_state)
        screen = get_steam_screen(steam_auth_url=steam_bridge_url, is_registration=False, use_web_app=True)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:steam",
            push_to_history=True,
        )
        await callback.answer()

    # =========================================================================
    # Upgrade to student from Profile
    # =========================================================================

    @router.callback_query(F.data == "auth:profile:upgrade_student")
    async def cb_profile_upgrade_student(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        await state.update_data(
            full_name=user.full_name if user else "Студент",
            phone=user.phone_number if user else "",
            gmail=user.email if user else "",
            role="student",
        )
        await state.set_state(AuthStates.waiting_barcode)

        screen = get_barcode_screen(full_name=user.full_name if user else "Студент")
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:barcode",
            push_to_history=True,
        )
        await callback.answer()

    # =========================================================================
    # Delete account from profile (confirmation prompt)
    # =========================================================================

    @router.callback_query(F.data == "auth:profile:delete_account")
    async def cb_profile_delete_account(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        steam_id = user.steam_id if user else None

        screen = get_delete_account_confirm_screen(steam_id=steam_id)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:delete_confirm",
            push_to_history=True,
        )
        await callback.answer()

    # =========================================================================
    # Confirm permanent account deletion
    # =========================================================================

    @router.callback_query(F.data == "auth:profile:delete_account:confirm")
    async def cb_profile_delete_account_confirm(
        callback: CallbackQuery, session: AsyncSession, state: FSMContext
    ) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        user_service = UserService(session=session)
        result = await user_service.delete_user_account(telegram_id=user_id)
        steam_id = result.get("steam_id") if result else None

        # Clean FSM state and Redis keys for this user
        await state.clear()
        try:
            fsm_pattern = f"fsm:*:{user_id}:{user_id}:*"
            keys = await core.redis.keys(fsm_pattern)
            if keys:
                await core.redis.delete(*keys)
        except Exception:
            pass

        # Reset navigator history stack
        try:
            await core.navigator.reset_history(user_id)
        except Exception:
            pass

        screen = get_account_deleted_screen(steam_id=steam_id)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:deleted",
            push_to_history=False,
        )
        await callback.answer("Аккаунт успешно удален", show_alert=True)

    return router
