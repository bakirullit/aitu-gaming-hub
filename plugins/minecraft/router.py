import re
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.user import User
from common.models.minecraft import MinecraftWhitelist
from core.context import CoreContext
from plugins.minecraft.rcon_client import execute_rcon_with_budget, RCONError
from plugins.minecraft.screens import (
    get_minecraft_home_screen,
    get_minecraft_status_screen,
    get_nickname_prompt_screen,
    get_whitelist_success_screen,
    get_rcon_error_screen,
    get_rules_screen,
)

logger = logging.getLogger("plugins.minecraft.router")

router = Router(name="minecraft_router")


class MinecraftStates(StatesGroup):
    waiting_nickname = State()


def setup_minecraft_routes(core: CoreContext) -> Router:
    """Configures and binds core dependencies to the Minecraft router."""

    async def render_minecraft_home(user_id: int, chat_id: int, payload: dict) -> any:
        async with core.db_session_factory() as session:
            stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == user_id)
            res = await session.execute(stmt)
            entry = res.scalar_one_or_none()
            linked_nick = entry.nickname if entry else None
            return get_minecraft_home_screen(linked_nick=linked_nick)

    core.navigator.register_screen_renderer("minecraft:home", render_minecraft_home)  # type: ignore

    @router.callback_query(F.data == "nav:minecraft")
    async def cb_minecraft_home(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        # Verify user is student
        user_stmt = select(User).where(User.telegram_id == user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user or not user.is_verified:
            await callback.answer(
                "⚠️ Сначала пройдите верификацию студента AITU в главном меню!",
                show_alert=True,
            )
            return

        # Check existing linked nickname
        stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == user_id)
        res = await session.execute(stmt)
        entry = res.scalar_one_or_none()
        linked_nick = entry.nickname if entry else None

        screen = get_minecraft_home_screen(linked_nick=linked_nick)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:home",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "mc:status")
    async def cb_minecraft_status(callback: CallbackQuery) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        try:
            rcon_resp = await execute_rcon_with_budget(
                host=core.settings.MINECRAFT_HOST,
                port=core.settings.MINECRAFT_RCON_PORT,
                password=core.settings.MINECRAFT_RCON_PASSWORD,
                command="list",
                total_timeout=core.settings.MINECRAFT_RCON_TIMEOUT,
            )
            screen = get_minecraft_status_screen(status_text=f"🟢 Онлайн:\n<code>{rcon_resp}</code>")
        except RCONError as exc:
            logger.warning(f"RCON status request failed for user {user_id}: {exc}")
            screen = get_rcon_error_screen(error_detail=str(exc))

        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:status",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "mc:rules")
    async def cb_minecraft_rules(callback: CallbackQuery) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        screen = get_rules_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:rules",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "mc:whitelist")
    async def cb_whitelist_prompt(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(MinecraftStates.waiting_nickname)
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        screen = get_nickname_prompt_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:prompt_nick",
            push_to_history=True,
        )
        await callback.answer()

    @router.message(MinecraftStates.waiting_nickname)
    async def process_nickname(message: Message, state: FSMContext, session: AsyncSession) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        nickname = (message.text or "").strip()

        # Minecraft Java nickname regex: 3-16 alphanumeric or underscore
        if not re.fullmatch(r"^[a-zA-Z0-9_]{3,16}$", nickname):
            screen = get_nickname_prompt_screen()
            error_screen = screen.__class__(
                text=(
                    "❌ <b>Недопустимый никнейм Minecraft!</b>\n\n"
                    "Никнейм должен содержать от 3 до 16 символов (только латиница, цифры и _).\n"
                    "Пример: <code>Alex_2024</code>\n\n"
                    "Попробуйте еще раз:"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(
                user_id=user_id,
                chat_id=chat_id,
                screen=error_screen,
                push_to_history=False,
            )
            return

        await state.clear()

        # Send command to RCON with Deadline Time Budgeting
        rcon_response = ""
        try:
            rcon_response = await execute_rcon_with_budget(
                host=core.settings.MINECRAFT_HOST,
                port=core.settings.MINECRAFT_RCON_PORT,
                password=core.settings.MINECRAFT_RCON_PASSWORD,
                command=f"whitelist add {nickname}",
                total_timeout=core.settings.MINECRAFT_RCON_TIMEOUT,
            )
        except RCONError as exc:
            logger.error(f"RCON whitelist command failed for '{nickname}': {exc}")
            screen = get_rcon_error_screen(error_detail=str(exc))
            await core.navigator.render(
                user_id=user_id,
                chat_id=chat_id,
                screen=screen,
                push_to_history=False,
            )
            return

        # Upsert into database
        stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == user_id)
        res = await session.execute(stmt)
        entry = res.scalar_one_or_none()

        if entry:
            entry.nickname = nickname
            entry.is_active = True
        else:
            entry = MinecraftWhitelist(
                user_id=user_id,
                nickname=nickname,
                is_active=True,
            )
            session.add(entry)

        await session.commit()

        # Render success screen
        screen = get_whitelist_success_screen(nickname=nickname, rcon_response=rcon_response)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:whitelist_success",
            push_to_history=True,
        )

    return router
