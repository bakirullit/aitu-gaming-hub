import logging
from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.user import User
from core.context import CoreContext
from plugins.auth.rbac import clean_contact_markup, get_user_home_screen

logger = logging.getLogger("plugins.auth.routers.menu")


def setup_menu_router(core: CoreContext) -> Router:
    """Configures menu navigation and start command routes."""
    router = Router(name="auth_menu_router")

    async def render_home(user_id: int, chat_id: int, payload: dict) -> any:
        async with core.db_session_factory() as session:
            stmt = select(User).where(User.telegram_id == user_id)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            return get_user_home_screen(user)

    core.navigator.register_screen_renderer("home", render_home)  # type: ignore

    # =========================================================================
    # /start handler
    # =========================================================================

    @router.message(CommandStart())
    async def cmd_start(
        message: Message,
        session: AsyncSession,
        state: FSMContext,
        command: CommandObject | None = None,
    ) -> None:
        await state.clear()
        user_id = message.from_user.id
        chat_id = message.chat.id

        # Clean old anchor if exists
        anchor_id = await core.navigator.get_anchor_id(user_id)
        if anchor_id:
            try:
                await core.bot.delete_message(chat_id, anchor_id)
            except Exception:
                pass
            await core.redis.delete(f"anchor:user:{user_id}:message_id")

        await core.navigator.reset_history(user_id)

        # Check user in DB
        stmt = select(User).where(User.telegram_id == user_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        screen = get_user_home_screen(user)
        screen_id = "home" if (user and user.full_name) else "club_info"

        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id=screen_id,
            push_to_history=True,
        )

    # =========================================================================
    # nav:home callback handler
    # =========================================================================

    @router.callback_query(F.data == "nav:home")
    async def cb_home(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        await clean_contact_markup(core, chat_id, state)
        await state.clear()

        stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        screen = get_user_home_screen(user)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="home",
            push_to_history=True,
        )
        await callback.answer()

    # =========================================================================
    # Fallback handler
    # =========================================================================

    @router.message(F.chat.type == "private", default_state)
    async def fallback_handler(message: Message, session: AsyncSession, state: FSMContext) -> None:
        """
        Fallback for when a user deletes the anchor message and sends random text outside of any flow.
        GarbageCollector deletes the text, but this handler recreates the anchor.
        """
        current_state = await state.get_state()
        if current_state is not None:
            return
        await cmd_start(message, session, state)

    return router
