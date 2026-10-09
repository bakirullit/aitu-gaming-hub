import json
import logging
import re
import secrets
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.models.minecraft import (
    MinecraftFriendRequest,
    MinecraftFriendship,
    MinecraftSession,
    MinecraftWhitelist,
)
from common.models.user import User
from core.context import CoreContext
from plugins.minecraft.rcon_client import RCONError, execute_rcon_with_budget
from plugins.minecraft.screens import (
    get_minecraft_add_friend_prompt_screen,
    get_minecraft_channel_screen,
    get_minecraft_code_screen,
    get_minecraft_friend_requests_screen,
    get_minecraft_friends_hub_screen,
    get_minecraft_friends_list_screen,
    get_minecraft_home_screen,
    get_minecraft_profile_screen,
    get_minecraft_prompt_nickname_screen,
    get_minecraft_servers_screen,
    get_nickname_prompt_screen,
    get_rcon_error_screen,
    get_rules_screen,
    get_whitelist_success_screen,
)

logger = logging.getLogger("plugins.minecraft.router")

router = Router(name="minecraft_router")


class MinecraftProfileSG(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_friend_tag = State()


# Aliases for backward compatibility and specification conformance
ChangeMinecraftNick = MinecraftProfileSG.waiting_for_nickname


class MinecraftStates(StatesGroup):
    waiting_nickname = MinecraftProfileSG.waiting_for_nickname


def setup_minecraft_routes(core: CoreContext) -> Router:
    """Configures and binds core dependencies to the Minecraft Discipline Hub router."""

    async def _get_user_and_nick(user_id: int, session: AsyncSession) -> tuple[User | None, str | None]:
        user_stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(user_stmt)).scalar_one_or_none()

        wl_stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == user_id)
        wl = (await session.execute(wl_stmt)).scalar_one_or_none()
        nick = wl.nickname if (wl and wl.is_active) else (user.minecraft_nickname if user else None)
        return user, nick

    async def render_minecraft_home(user_id: int, chat_id: int, payload: dict) -> any:
        async with core.db_session_factory() as session:
            _, linked_nick = await _get_user_and_nick(user_id, session)
            return get_minecraft_home_screen(
                linked_nick=linked_nick,
                online=settings.MINECRAFT_DEFAULT_ONLINE,
                max_players=settings.MINECRAFT_MAX_PLAYERS,
                server_ip=settings.MINECRAFT_SERVER_IP,
            )

    core.navigator.register_screen_renderer("minecraft:home", render_minecraft_home)  # type: ignore

    # --------------------------------------------------------------------------
    # 1. Main Hub Entry Point (nav:minecraft, /minecraft)
    # --------------------------------------------------------------------------
    @router.callback_query(F.data.in_(["nav:minecraft", "mc:home"]))
    async def cb_minecraft_home(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        user, linked_nick = await _get_user_and_nick(user_id, session)
        if not user or not user.is_verified:
            await callback.answer(
                "⚠️ Сначала пройдите верификацию студента AITU в главном меню!",
                show_alert=True,
            )
            return

        screen = get_minecraft_home_screen(
            linked_nick=linked_nick,
            online=settings.MINECRAFT_DEFAULT_ONLINE,
            max_players=settings.MINECRAFT_MAX_PLAYERS,
            server_ip=settings.MINECRAFT_SERVER_IP,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:home",
            push_to_history=True,
        )
        await callback.answer()

    @router.message(Command("minecraft"))
    async def cmd_minecraft_home(message: Message, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = message.from_user.id
        chat_id = message.chat.id

        user, linked_nick = await _get_user_and_nick(user_id, session)
        if not user or not user.is_verified:
            await message.answer(
                "⚠️ Для доступа к Minecraft дисциплине пройдите верификацию студента AITU через главное меню."
            )
            return

        screen = get_minecraft_home_screen(
            linked_nick=linked_nick,
            online=settings.MINECRAFT_DEFAULT_ONLINE,
            max_players=settings.MINECRAFT_MAX_PLAYERS,
            server_ip=settings.MINECRAFT_SERVER_IP,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:home",
            push_to_history=True,
        )

    # --------------------------------------------------------------------------
    # 2. Submodule A: 🌐 Сервера (cb_mc_servers)
    # --------------------------------------------------------------------------
    @router.callback_query(F.data.in_(["cb_mc_servers", "mc:servers", "mc:status"]))
    async def cb_mc_servers(callback: CallbackQuery) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        online = settings.MINECRAFT_DEFAULT_ONLINE
        max_players = settings.MINECRAFT_MAX_PLAYERS

        # Try live query via RCON if configured
        if settings.MINECRAFT_RCON_PASSWORD:
            try:
                rcon_resp = await execute_rcon_with_budget(
                    host=settings.MINECRAFT_HOST,
                    port=settings.MINECRAFT_RCON_PORT,
                    password=settings.MINECRAFT_RCON_PASSWORD,
                    command="list",
                    total_timeout=settings.MINECRAFT_RCON_TIMEOUT,
                )
                match = re.search(r"(\d+)\s+of\s+a\s+max\s+of\s+(\d+)", rcon_resp, re.IGNORECASE)
                if match:
                    online = int(match.group(1))
                    max_players = int(match.group(2))
            except Exception as exc:
                logger.debug(f"Could not fetch live server player list via RCON: {exc}")

        screen = get_minecraft_servers_screen(
            server_name=settings.MINECRAFT_SERVER_NAME,
            version=settings.MINECRAFT_SERVER_VERSION,
            online=online,
            max_players=max_players,
            address=settings.MINECRAFT_SERVER_IP,
            motd=settings.MINECRAFT_SERVER_MOTD,
            modpack_url=settings.MINECRAFT_MODPACK_URL,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:servers",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "mc:copy_ip")
    async def cb_mc_copy_ip(callback: CallbackQuery) -> None:
        await callback.answer(
            f"📋 IP адрес сервера:\n{settings.MINECRAFT_SERVER_IP}",
            show_alert=True,
        )

    # --------------------------------------------------------------------------
    # 3. Submodule B: 👤 Профиль игрока (cb_mc_profile)
    # --------------------------------------------------------------------------
    @router.callback_query(F.data.in_(["cb_mc_profile", "mc:profile"]))
    async def cb_mc_profile(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        user, linked_nick = await _get_user_and_nick(user_id, session)

        # Check active session in DB or Redis
        sess_stmt = select(MinecraftSession).where(
            MinecraftSession.user_id == user_id,
            MinecraftSession.is_active == True,
        )
        active_session_row = (await session.execute(sess_stmt)).first()
        redis_session = None
        if core.redis:
            try:
                redis_session = await core.redis.get(f"mc:user_session:{user_id}")
            except Exception as e:
                logger.debug(f"Redis get session error: {e}")

        has_active_session = bool(active_session_row or redis_session)

        is_staff = user.is_staff if user else False
        is_disc_admin = user.is_discipline_admin if user else False
        is_head_admin = user.has_role("head_admin") if user else False

        from common.models.discipline import Discipline
        disc_stmt = select(Discipline).where(Discipline.slug == "minecraft")
        mc_disc = (await session.execute(disc_stmt)).scalar_one_or_none()
        is_mc_curator = bool(mc_disc and mc_disc.admin_id == user_id)

        can_manage_whitelist = is_staff and (is_head_admin or is_mc_curator or is_disc_admin)

        screen = get_minecraft_profile_screen(
            nickname=linked_nick,
            username=user.username if user else callback.from_user.username,
            telegram_id=user_id,
            has_active_session=has_active_session,
            can_manage_whitelist=can_manage_whitelist,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:profile",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data.in_(["mc:change_nick", "mc:whitelist", "mc:whitelist_admin"]))
    async def cb_mc_change_nick_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        user_stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(user_stmt)).scalar_one_or_none()

        is_staff = user.is_staff if user else False
        is_disc_admin = user.is_discipline_admin if user else False
        is_head_admin = user.has_role("head_admin") if user else False

        from common.models.discipline import Discipline
        disc_stmt = select(Discipline).where(Discipline.slug == "minecraft")
        mc_disc = (await session.execute(disc_stmt)).scalar_one_or_none()
        is_mc_curator = bool(mc_disc and mc_disc.admin_id == user_id)

        can_manage_whitelist = is_staff and (is_head_admin or is_mc_curator or is_disc_admin)
        if not can_manage_whitelist:
            await callback.answer(
                "⚠️ Управление вайтлистом доступно только администратору дисциплины Minecraft со статусом Staff.",
                show_alert=True,
            )
            return

        await state.set_state(MinecraftProfileSG.waiting_for_nickname)
        screen = get_nickname_prompt_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:prompt_nick",
            push_to_history=True,
        )
        await callback.answer()

    @router.message(MinecraftProfileSG.waiting_for_nickname)
    async def process_nickname_change(message: Message, state: FSMContext, session: AsyncSession) -> None:
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

        # Update User model
        user_stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if user:
            user.minecraft_nickname = nickname

        # Upsert MinecraftWhitelist
        wl_stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == user_id)
        wl = (await session.execute(wl_stmt)).scalar_one_or_none()
        old_nick = wl.nickname if wl else None
        if wl:
            wl.nickname = nickname
            wl.is_active = True
        else:
            wl = MinecraftWhitelist(
                user_id=user_id,
                nickname=nickname,
                is_active=True,
            )
            session.add(wl)

        # Update active MinecraftSession entries
        sess_stmt = select(MinecraftSession).where(MinecraftSession.user_id == user_id)
        sessions = (await session.execute(sess_stmt)).scalars().all()
        for s in sessions:
            s.minecraft_nickname = nickname

        await session.commit()

        screen = get_whitelist_success_screen(
            nickname=nickname,
            rcon_response="Успешно синхронизировано в базе данных",
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:whitelist_success",
            push_to_history=True,
        )

    @router.callback_query(F.data == "mc:gen_code")
    async def cb_mc_gen_code(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        user, linked_nick = await _get_user_and_nick(user_id, session)
        if not linked_nick:
            await callback.answer(
                "⚠️ Сначала установите игровой никнейм Minecraft в профиле!",
                show_alert=True,
            )
            return

        clean_tag = (user.username if user and user.username else str(user_id)).strip().lstrip("@").lower()

        # Generate secure 6-digit numeric PIN
        pin = f"{secrets.randbelow(900000) + 100000:06d}"

        # Store in Redis with 3-minute TTL (matches REST API /api/auth/request-code key)
        if core.redis:
            redis_key = f"auth:pin:{clean_tag}"
            pin_data = {
                "pin": pin,
                "mc_nick": linked_nick,
                "user_id": user_id,
            }
            try:
                await core.redis.set(redis_key, json.dumps(pin_data), ex=180)
            except Exception as e:
                logger.warning(f"Failed to set auth PIN in Redis: {e}")

        screen = get_minecraft_code_screen(pin=pin, nickname=linked_nick)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:code",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "mc:unlink")
    async def cb_mc_unlink(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        user, linked_nick = await _get_user_and_nick(user_id, session)
        if not linked_nick:
            await callback.answer("⚠️ Аккаунт еще не привязан.", show_alert=True)
            return

        old_nick = linked_nick

        # Clear User nickname
        if user:
            user.minecraft_nickname = None

        # Deactivate whitelist entry
        wl_stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == user_id)
        wl = (await session.execute(wl_stmt)).scalar_one_or_none()
        if wl:
            wl.is_active = False

        # Deactivate all sessions
        sess_stmt = select(MinecraftSession).where(MinecraftSession.user_id == user_id)
        sessions = (await session.execute(sess_stmt)).scalars().all()
        for s in sessions:
            s.is_active = False

        await session.commit()

        # Invalidate Redis caches
        if core.redis:
            try:
                clean_tag = (user.username if user and user.username else str(user_id)).strip().lstrip("@").lower()
                await core.redis.delete(f"auth:pin:{clean_tag}", f"mc:user_session:{user_id}")
            except Exception as e:
                logger.warning(f"Failed to delete redis session for user {user_id}: {e}")

        await callback.answer("🔓 Аккаунт Minecraft успешно отвязан.", show_alert=True)

        screen = get_minecraft_profile_screen(
            nickname=None,
            username=user.username if user else callback.from_user.username,
            telegram_id=user_id,
            has_active_session=False,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:profile",
            push_to_history=False,
        )

    # --------------------------------------------------------------------------
    # 4. Submodule C: 👥 Друзья (cb_mc_friends)
    # --------------------------------------------------------------------------
    @router.callback_query(F.data.in_(["cb_mc_friends", "mc:friends"]))
    async def cb_mc_friends(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        # Total friends count
        f_count_stmt = select(func.count(MinecraftFriendship.id)).where(MinecraftFriendship.user_id == user_id)
        total_friends = (await session.execute(f_count_stmt)).scalar() or 0

        # Pending requests count
        req_count_stmt = select(func.count(MinecraftFriendRequest.id)).where(
            MinecraftFriendRequest.receiver_id == user_id,
            MinecraftFriendRequest.status == "pending",
        )
        pending_count = (await session.execute(req_count_stmt)).scalar() or 0

        # Check online friends via Redis or mock count
        online_friends = 0
        if total_friends > 0:
            # Query friends to check active sessions
            f_stmt = select(MinecraftFriendship).where(MinecraftFriendship.user_id == user_id)
            friendships = (await session.execute(f_stmt)).scalars().all()
            for f in friendships:
                if core.redis:
                    try:
                        if await core.redis.exists(f"mc:user_session:{f.friend_id}"):
                            online_friends += 1
                    except Exception:
                        pass

        screen = get_minecraft_friends_hub_screen(
            total_friends=total_friends,
            online_friends=online_friends,
            pending_requests_count=pending_count,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:friends",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("mc:friends_list"))
    async def cb_mc_friends_list(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        parts = callback.data.split(":")
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1

        f_stmt = select(MinecraftFriendship).where(MinecraftFriendship.user_id == user_id)
        friendships = (await session.execute(f_stmt)).scalars().all()

        friends_data: list[dict] = []
        for f in friendships:
            f_user_stmt = select(User).where(User.telegram_id == f.friend_id)
            f_user = (await session.execute(f_user_stmt)).scalar_one_or_none()

            wl_stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == f.friend_id)
            wl = (await session.execute(wl_stmt)).scalar_one_or_none()

            nick = wl.nickname if (wl and wl.is_active) else (
                f_user.minecraft_nickname if f_user and f_user.minecraft_nickname else (
                    f_user.username if f_user and f_user.username else f"User_{f.friend_id}"
                )
            )
            tag = f"@{f_user.username}" if f_user and f_user.username else f"ID: {f.friend_id}"

            is_online = False
            if core.redis:
                try:
                    is_online = bool(await core.redis.exists(f"mc:user_session:{f.friend_id}"))
                except Exception:
                    pass

            friends_data.append({
                "nickname": nick,
                "telegram_tag": tag,
                "is_online": is_online,
            })

        screen = get_minecraft_friends_list_screen(friends=friends_data, page=page, page_size=5)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:friends_list",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "mc:add_friend")
    async def cb_mc_add_friend_prompt(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(MinecraftProfileSG.waiting_for_friend_tag)
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        screen = get_minecraft_add_friend_prompt_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:prompt_add_friend",
            push_to_history=True,
        )
        await callback.answer()

    @router.message(MinecraftProfileSG.waiting_for_friend_tag)
    async def process_add_friend(message: Message, state: FSMContext, session: AsyncSession) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        query = (message.text or "").strip()
        clean_query = query.lstrip("@").lower()

        if not clean_query:
            await message.answer("⚠️ Пожалуйста, введите корректный @username или Minecraft никнейм:")
            return

        # 1. Search in users table
        target_stmt = select(User).where(
            or_(
                func.lower(User.username) == clean_query,
                func.lower(User.barcode) == clean_query,
                func.lower(User.email) == clean_query,
                func.lower(User.minecraft_nickname) == clean_query,
            )
        )
        target_user = (await session.execute(target_stmt)).scalar_one_or_none()

        # 2. Search in minecraft_whitelist
        if not target_user:
            wl_stmt = select(MinecraftWhitelist).where(func.lower(MinecraftWhitelist.nickname) == clean_query)
            wl_entry = (await session.execute(wl_stmt)).scalar_one_or_none()
            if wl_entry:
                u_stmt = select(User).where(User.telegram_id == wl_entry.user_id)
                target_user = (await session.execute(u_stmt)).scalar_one_or_none()

        if not target_user:
            await message.answer(
                f"❌ Пользователь «{query}» не найден в системе AITU Gaming Hub.\n"
                "Убедитесь, что друг запустил бота и привязал аккаунт, либо попробуйте снова:"
            )
            return

        if target_user.telegram_id == user_id:
            await message.answer("⚠️ Вы не можете отправить заявку в друзья самому себе!")
            return

        # Check existing friendship
        existing_friend_stmt = select(MinecraftFriendship).where(
            MinecraftFriendship.user_id == user_id,
            MinecraftFriendship.friend_id == target_user.telegram_id,
        )
        existing_friend = (await session.execute(existing_friend_stmt)).scalar_one_or_none()
        if existing_friend:
            await state.clear()
            await message.answer("ℹ️ Вы уже являетесь друзьями с этим игроком!")
            return

        # Check existing pending request
        existing_req_stmt = select(MinecraftFriendRequest).where(
            MinecraftFriendRequest.sender_id == user_id,
            MinecraftFriendRequest.receiver_id == target_user.telegram_id,
            MinecraftFriendRequest.status == "pending",
        )
        existing_req = (await session.execute(existing_req_stmt)).scalar_one_or_none()
        if existing_req:
            await state.clear()
            await message.answer("ℹ️ Заявка в друзья этому игроку уже была отправлена ранее и ожидает подтверждения.")
            return

        # Add new request
        new_req = MinecraftFriendRequest(
            sender_id=user_id,
            receiver_id=target_user.telegram_id,
            status="pending",
        )
        session.add(new_req)
        await session.commit()
        await state.clear()

        # Notify recipient via bot if possible
        try:
            sender_tag = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
            await core.bot.send_message(
                chat_id=target_user.telegram_id,
                text=f"📬 <b>Новая заявка в друзья Minecraft!</b>\n\nИгрок {sender_tag} хочет добавить вас в друзья на сервере AITU SMP.\nОткройте <code>/minecraft</code> → 👥 Друзья → 📥 Заявки, чтобы принять.",
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.debug(f"Could not notify friend request recipient {target_user.telegram_id}: {exc}")

        target_name = f"@{target_user.username}" if target_user.username else target_user.first_name
        await message.answer(f"🎉 Заявка в друзья успешно отправлена игроку <b>{target_name}</b>!")

        # Rerender friends hub
        f_count_stmt = select(func.count(MinecraftFriendship.id)).where(MinecraftFriendship.user_id == user_id)
        total_friends = (await session.execute(f_count_stmt)).scalar() or 0
        req_count_stmt = select(func.count(MinecraftFriendRequest.id)).where(
            MinecraftFriendRequest.receiver_id == user_id,
            MinecraftFriendRequest.status == "pending",
        )
        pending_count = (await session.execute(req_count_stmt)).scalar() or 0

        screen = get_minecraft_friends_hub_screen(
            total_friends=total_friends,
            online_friends=0,
            pending_requests_count=pending_count,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:friends",
            push_to_history=False,
        )

    @router.callback_query(F.data == "mc:friend_requests")
    async def cb_mc_friend_requests(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        req_stmt = select(MinecraftFriendRequest).where(
            MinecraftFriendRequest.receiver_id == user_id,
            MinecraftFriendRequest.status == "pending",
        )
        requests = (await session.execute(req_stmt)).scalars().all()

        requests_data: list[dict] = []
        for r in requests:
            s_user_stmt = select(User).where(User.telegram_id == r.sender_id)
            s_user = (await session.execute(s_user_stmt)).scalar_one_or_none()

            wl_stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == r.sender_id)
            wl = (await session.execute(wl_stmt)).scalar_one_or_none()

            nick = wl.nickname if (wl and wl.is_active) else (
                s_user.minecraft_nickname if s_user and s_user.minecraft_nickname else (
                    s_user.username if s_user and s_user.username else f"User_{r.sender_id}"
                )
            )
            tag = f"@{s_user.username}" if s_user and s_user.username else f"ID: {r.sender_id}"

            requests_data.append({
                "id": r.id,
                "from_nickname": nick,
                "from_tag": tag,
            })

        screen = get_minecraft_friend_requests_screen(requests=requests_data)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:requests",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("mc:accept_req:"))
    async def cb_mc_accept_request(callback: CallbackQuery, session: AsyncSession) -> None:
        req_id_str = callback.data.split(":")[2]
        if not req_id_str.isdigit():
            await callback.answer("Ошибка запроса.", show_alert=True)
            return

        req_id = int(req_id_str)
        user_id = callback.from_user.id

        stmt = select(MinecraftFriendRequest).where(
            MinecraftFriendRequest.id == req_id,
            MinecraftFriendRequest.receiver_id == user_id,
            MinecraftFriendRequest.status == "pending",
        )
        req = (await session.execute(stmt)).scalar_one_or_none()
        if not req:
            await callback.answer("Заявка уже обработана или не найдена.", show_alert=True)
            return

        req.status = "accepted"

        # Bidirectional friendship
        f1_stmt = select(MinecraftFriendship).where(
            MinecraftFriendship.user_id == user_id,
            MinecraftFriendship.friend_id == req.sender_id,
        )
        if not (await session.execute(f1_stmt)).scalar_one_or_none():
            session.add(MinecraftFriendship(user_id=user_id, friend_id=req.sender_id))

        f2_stmt = select(MinecraftFriendship).where(
            MinecraftFriendship.user_id == req.sender_id,
            MinecraftFriendship.friend_id == user_id,
        )
        if not (await session.execute(f2_stmt)).scalar_one_or_none():
            session.add(MinecraftFriendship(user_id=req.sender_id, friend_id=user_id))

        await session.commit()
        await callback.answer("✅ Заявка в друзья принята!", show_alert=True)

        # Refresh requests view
        await cb_mc_friend_requests(callback=callback, session=session)

    @router.callback_query(F.data.startswith("mc:decline_req:"))
    async def cb_mc_decline_request(callback: CallbackQuery, session: AsyncSession) -> None:
        req_id_str = callback.data.split(":")[2]
        if not req_id_str.isdigit():
            await callback.answer("Ошибка запроса.", show_alert=True)
            return

        req_id = int(req_id_str)
        user_id = callback.from_user.id

        stmt = select(MinecraftFriendRequest).where(
            MinecraftFriendRequest.id == req_id,
            MinecraftFriendRequest.receiver_id == user_id,
            MinecraftFriendRequest.status == "pending",
        )
        req = (await session.execute(stmt)).scalar_one_or_none()
        if not req:
            await callback.answer("Заявка уже обработана или не найдена.", show_alert=True)
            return

        req.status = "declined"
        await session.commit()
        await callback.answer("❌ Заявка отклонена.", show_alert=True)

        # Refresh requests view
        await cb_mc_friend_requests(callback=callback, session=session)

    # --------------------------------------------------------------------------
    # 5. Submodule D: 📢 Канал дисциплины (cb_mc_channel)
    # --------------------------------------------------------------------------
    @router.callback_query(F.data.in_(["cb_mc_channel", "mc:channel"]))
    async def cb_mc_channel(callback: CallbackQuery) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        screen = get_minecraft_channel_screen(
            channel_url=settings.MINECRAFT_CHANNEL_URL,
            chat_url=settings.MINECRAFT_CHAT_URL,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="minecraft:channel",
            push_to_history=True,
        )
        await callback.answer()

    # --------------------------------------------------------------------------
    # 6. Legacy & Informational Callbacks
    # --------------------------------------------------------------------------
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

    @router.callback_query(F.data == "mc:noop")
    async def cb_minecraft_noop(callback: CallbackQuery) -> None:
        await callback.answer()

    return router
