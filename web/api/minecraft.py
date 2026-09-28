import json
import logging
import re
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.dtos.minecraft import (
    MinecraftFriendActionPayload,
    MinecraftFriendItem,
    MinecraftFriendRequestItem,
    MinecraftFriendRequestsResponse,
    MinecraftFriendSendRequestPayload,
    MinecraftFriendsListResponse,
    MinecraftRequestCodePayload,
    MinecraftRequestCodeResponse,
    MinecraftServerInfoResponse,
    MinecraftStatusResponse,
    MinecraftVerifyPayload,
    MinecraftVerifyResponse,
)
from common.models.minecraft import (
    MinecraftFriendRequest,
    MinecraftFriendship,
    MinecraftSession,
    MinecraftWhitelist,
)
from common.models.user import User
from core.lifespan import runtime
from plugins.minecraft.rcon_client import execute_rcon_with_budget
from web.api.dependencies import get_db_session

logger = logging.getLogger("web.api.minecraft")

# In-memory fallback cache when Redis is unavailable (e.g. offline unit testing)
_fallback_cache: dict[str, tuple[str, float]] = {}


async def _cache_set(key: str, value: str, ex: int = 300) -> None:
    _fallback_cache[key] = (value, time.time() + ex)
    if runtime.redis:
        try:
            await runtime.redis.set(key, value, ex=ex)
        except Exception as exc:
            logger.warning(f"Redis set failed for {key}: {exc}")


async def _cache_get(key: str) -> Optional[str]:
    if runtime.redis:
        try:
            val = await runtime.redis.get(key)
            if isinstance(val, (str, bytes)):
                return val.decode() if isinstance(val, bytes) else val
        except Exception as exc:
            logger.warning(f"Redis get failed for {key}: {exc}")
    entry = _fallback_cache.get(key)
    if entry:
        val, expiry = entry
        if time.time() <= expiry:
            return val
        _fallback_cache.pop(key, None)
    return None


async def _cache_delete(*keys: str) -> None:
    for k in keys:
        _fallback_cache.pop(k, None)
    if runtime.redis:
        try:
            await runtime.redis.delete(*keys)
        except Exception as exc:
            logger.warning(f"Redis delete failed for {keys}: {exc}")



async def get_optional_mc_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> tuple[Optional[User], Optional[str]]:
    """Extract authenticated Minecraft user and player nickname from Bearer token."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, None

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None, None

    # Check cache / Redis
    sess_str = await _cache_get(f"mc:session:{token}")
    if sess_str:
        try:
            sess_data = json.loads(sess_str)
            user_id = sess_data.get("user_id")
            if user_id:
                stmt = select(User).where(User.telegram_id == user_id)
                user = (await session.execute(stmt)).scalar_one_or_none()
                if user:
                    return user, sess_data.get("minecraft_nickname")
        except Exception as exc:
            logger.warning(f"Error deserializing session cache for {token}: {exc}")

    # Check database
    try:
        stmt = select(MinecraftSession).where(
            MinecraftSession.session_token == token,
            MinecraftSession.is_active == True,
        )
        res = await session.execute(stmt)
        mc_sess = res.scalar_one_or_none()
        if mc_sess:
            user_stmt = select(User).where(User.telegram_id == mc_sess.user_id)
            user = (await session.execute(user_stmt)).scalar_one_or_none()
            if user:
                return user, mc_sess.minecraft_nickname
    except Exception as exc:
        logger.warning(f"Error querying session from DB: {exc}")

    return None, None


class SlashRouter(APIRouter):
    """APIRouter that handles requests with or without trailing slash without strict redirect issues."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("redirect_slashes", False)
        super().__init__(*args, **kwargs)

    def api_route(self, path: str, **kwargs):
        def decorator(func):
            super(SlashRouter, self).api_route(path, **kwargs)(func)
            alt_path = path.rstrip("/") + "/" if not path.endswith("/") else path.rstrip("/")
            if alt_path != path:
                alt_kwargs = dict(kwargs)
                alt_kwargs["include_in_schema"] = False
                super(SlashRouter, self).api_route(alt_path, **alt_kwargs)(func)
            return func
        return decorator


# Subrouters with redirect_slashes=False to prevent 307 redirects for HTTP clients
mc_auth_router = SlashRouter(prefix="/auth", tags=["Minecraft Client Auth"])
mc_server_router = SlashRouter(prefix="/server", tags=["Minecraft Server Info"])
mc_friends_router = SlashRouter(prefix="/friends", tags=["Minecraft Friends"])



# --------------------------------------------------------------------------
# 1. Auth Endpoints (/api/auth)
# --------------------------------------------------------------------------
@mc_auth_router.post("/request-code", response_model=MinecraftRequestCodeResponse)
async def request_code(
    payload: MinecraftRequestCodePayload,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Request 6-digit verification PIN for Minecraft authentication.
    Normalizes tag, finds user by telegram username, caches PIN in Redis for 5 minutes,
    and dispatches code to user's Telegram chat.
    """
    clean_tag = (payload.telegram_tag or payload.tag or "").strip().lstrip("@").lower()
    if not clean_tag:
        raise HTTPException(
            status_code=404,
            detail="User not registered in @aitu_gaming_bot. Please start the bot first.",
        )

    stmt = select(User).where(func.lower(User.username) == clean_tag)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not registered in @aitu_gaming_bot. Please start the bot first.",
        )

    # Generate secure 6-digit numeric PIN
    pin = f"{secrets.randbelow(900000) + 100000:06d}"

    # Store in Redis with 5-minute TTL
    redis_key = f"auth:pin:{clean_tag}"
    nick = (payload.minecraft_nickname or payload.mc_nick or "Player").strip()
    pin_data = {
        "pin": pin,
        "mc_nick": nick,
        "user_id": user.telegram_id,
    }
    await _cache_set(redis_key, json.dumps(pin_data), ex=300)

    # Dispatch to Telegram chat via Bot
    if runtime.bot:
        try:
            await runtime.bot.send_message(
                chat_id=user.telegram_id,
                text=f"🔑 Your AITU Minecraft verification code: <b>{pin}</b>. Valid for 5 minutes.",
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning(f"Could not send Telegram PIN message to {user.telegram_id}: {exc}")

    return MinecraftRequestCodeResponse(
        status="code_sent",
        message="Verification code sent to Telegram",
    )


@mc_auth_router.post("/verify", response_model=MinecraftVerifyResponse)
async def verify_code(
    payload: MinecraftVerifyPayload,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Verify 6-digit PIN, generate persistent session token, save session in DB & Redis,
    link Minecraft nickname, and invalidate the PIN.
    """
    clean_tag = (payload.telegram_tag or payload.tag or "").strip().lstrip("@").lower()
    code_val = str(payload.code if payload.code is not None else (payload.pin or "")).strip()

    if not clean_tag or not code_val:
        raise HTTPException(status_code=400, detail="Invalid request parameters: tag and code/pin required")

    redis_key = f"auth:pin:{clean_tag}"

    cached_str = await _cache_get(redis_key)
    if not cached_str:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    try:
        cached_data = json.loads(cached_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    if str(cached_data.get("pin")).strip() != code_val:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    # Find User
    user_id = cached_data.get("user_id")
    user = None
    if user_id:
        user_stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(user_stmt)).scalar_one_or_none()

    if not user:
        stmt = select(User).where(func.lower(User.username) == clean_tag)
        user = (await session.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate persistent cryptographically secure session token
    session_token = uuid.uuid4().hex
    raw_nick = (payload.minecraft_nickname or payload.mc_nick or "").strip()
    mc_nick = raw_nick or cached_data.get("mc_nick", "Player")

    # Save session in DB
    mc_session = MinecraftSession(
        user_id=user.telegram_id,
        session_token=session_token,
        minecraft_nickname=mc_nick,
        is_active=True,
    )
    session.add(mc_session)

    # Upsert MinecraftWhitelist entry
    wl_stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == user.telegram_id)
    wl_entry = (await session.execute(wl_stmt)).scalar_one_or_none()
    if wl_entry:
        wl_entry.nickname = mc_nick
        wl_entry.is_active = True
    else:
        wl_entry = MinecraftWhitelist(
            user_id=user.telegram_id,
            nickname=mc_nick,
            is_active=True,
        )
        session.add(wl_entry)

    await session.commit()

    # Save session in Redis
    session_payload = {
        "session_token": session_token,
        "user_id": user.telegram_id,
        "username": user.username or clean_tag,
        "minecraft_nickname": mc_nick,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await _cache_set(f"mc:session:{session_token}", json.dumps(session_payload), ex=86400 * 30)
    await _cache_set(f"mc:user_session:{user.telegram_id}", session_token, ex=86400 * 30)

    # Delete used PIN from Redis
    await _cache_delete(redis_key)

    formatted_tag = f"@{user.username}" if user.username else f"@{clean_tag}"
    return MinecraftVerifyResponse(
        status="success",
        session_token=session_token,
        token=session_token,
        telegram_id=user.telegram_id,
        username=user.username or clean_tag,
        telegram_tag=formatted_tag,
        tag=formatted_tag,
    )


# --------------------------------------------------------------------------
# 2. Server Info Endpoint (/api/server)
# --------------------------------------------------------------------------
@mc_server_router.get("/info", response_model=MinecraftServerInfoResponse)
async def get_server_info():
    """
    Returns server status and connection information.
    Queries RCON when reachable or falls back gracefully to configured defaults.
    """
    online = settings.MINECRAFT_DEFAULT_ONLINE
    max_players = settings.MINECRAFT_MAX_PLAYERS

    if settings.MINECRAFT_RCON_PASSWORD:
        try:
            rcon_resp = await execute_rcon_with_budget(
                host=settings.MINECRAFT_HOST,
                port=settings.MINECRAFT_RCON_PORT,
                password=settings.MINECRAFT_RCON_PASSWORD,
                command="list",
                total_timeout=min(settings.MINECRAFT_RCON_TIMEOUT, 1.5),
                attempts=1,
            )
            match = re.search(r"There are (\d+) of a max of (\d+) players online", rcon_resp)
            if match:
                online = int(match.group(1))
                max_players = int(match.group(2))
        except Exception as exc:
            logger.debug(f"Could not fetch live RCON server status: {exc}")

    return MinecraftServerInfoResponse(
        ip=settings.MINECRAFT_SERVER_IP,
        name=settings.MINECRAFT_SERVER_NAME,
        online=online,
        max_players=max_players,
        motd=settings.MINECRAFT_SERVER_MOTD,
    )


# --------------------------------------------------------------------------
# 3. Friends Endpoints (/api/friends)
# --------------------------------------------------------------------------
@mc_friends_router.get("/list", response_model=MinecraftFriendsListResponse)
async def get_friends_list(
    auth_data: tuple[Optional[User], Optional[str]] = Depends(get_optional_mc_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get friends list for authenticated player.
    Returns foundation mock data if unauthenticated or when no friendships exist.
    """
    user, _ = auth_data

    foundation_mock = [
        MinecraftFriendItem(
            nickname="Student123",
            telegram_tag="@student",
            status="online",
            activity="Playing on AITU SMP",
        )
    ]

    if not user:
        return MinecraftFriendsListResponse(friends=foundation_mock)

    # Query friendships
    stmt = select(MinecraftFriendship).where(MinecraftFriendship.user_id == user.telegram_id)
    res = await session.execute(stmt)
    friendships = res.scalars().all()

    if not friendships:
        return MinecraftFriendsListResponse(friends=foundation_mock)

    friend_items: list[MinecraftFriendItem] = []
    for f in friendships:
        f_user_stmt = select(User).where(User.telegram_id == f.friend_id)
        f_user = (await session.execute(f_user_stmt)).scalar_one_or_none()

        wl_stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == f.friend_id)
        wl = (await session.execute(wl_stmt)).scalar_one_or_none()

        nick = wl.nickname if wl else (f_user.username if f_user and f_user.username else f"User_{f.friend_id}")
        tag = f"@{f_user.username}" if f_user and f_user.username else f"@{nick}"

        friend_items.append(
            MinecraftFriendItem(
                nickname=nick,
                telegram_tag=tag,
                status="online",
                activity="Playing on AITU SMP",
            )
        )

    return MinecraftFriendsListResponse(friends=friend_items)


@mc_friends_router.get("/requests", response_model=MinecraftFriendRequestsResponse)
async def get_friend_requests(
    auth_data: tuple[Optional[User], Optional[str]] = Depends(get_optional_mc_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get pending incoming friend requests.
    Returns empty list if unauthenticated or no requests pending.
    """
    user, _ = auth_data
    if not user:
        return MinecraftFriendRequestsResponse(requests=[])

    stmt = select(MinecraftFriendRequest).where(
        MinecraftFriendRequest.receiver_id == user.telegram_id,
        MinecraftFriendRequest.status == "pending",
    )
    res = await session.execute(stmt)
    requests = res.scalars().all()

    items: list[MinecraftFriendRequestItem] = []
    for req in requests:
        s_user_stmt = select(User).where(User.telegram_id == req.sender_id)
        s_user = (await session.execute(s_user_stmt)).scalar_one_or_none()

        wl_stmt = select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == req.sender_id)
        wl = (await session.execute(wl_stmt)).scalar_one_or_none()

        nick = wl.nickname if wl else (s_user.username if s_user and s_user.username else f"User_{req.sender_id}")
        tag = f"@{s_user.username}" if s_user and s_user.username else f"@{nick}"

        items.append(
            MinecraftFriendRequestItem(
                request_id=req.id,
                id=req.id,
                from_nickname=nick,
                from_tag=tag,
                status=req.status,
            )
        )

    return MinecraftFriendRequestsResponse(requests=items)


@mc_friends_router.post("/request", response_model=MinecraftStatusResponse)
async def send_friend_request(
    payload: MinecraftFriendSendRequestPayload,
    auth_data: tuple[Optional[User], Optional[str]] = Depends(get_optional_mc_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Send friend request by @tag, email, or nickname.
    Returns {"status": "request_sent"}.
    """
    user, _ = auth_data
    clean_query = payload.query.strip().lstrip("@").lower()

    if user and clean_query:
        target_stmt = select(User).where(
            or_(
                func.lower(User.username) == clean_query,
                func.lower(User.email) == clean_query,
                func.lower(User.barcode) == clean_query,
            )
        )
        target_user = (await session.execute(target_stmt)).scalar_one_or_none()

        if not target_user:
            wl_stmt = select(MinecraftWhitelist).where(func.lower(MinecraftWhitelist.nickname) == clean_query)
            wl_target = (await session.execute(wl_stmt)).scalar_one_or_none()
            if wl_target:
                target_user = (
                    await session.execute(select(User).where(User.telegram_id == wl_target.user_id))
                ).scalar_one_or_none()

        if target_user and target_user.telegram_id != user.telegram_id:
            # Check existing pending request
            existing_stmt = select(MinecraftFriendRequest).where(
                MinecraftFriendRequest.sender_id == user.telegram_id,
                MinecraftFriendRequest.receiver_id == target_user.telegram_id,
                MinecraftFriendRequest.status == "pending",
            )
            existing = (await session.execute(existing_stmt)).scalar_one_or_none()
            if not existing:
                new_req = MinecraftFriendRequest(
                    sender_id=user.telegram_id,
                    receiver_id=target_user.telegram_id,
                    status="pending",
                )
                session.add(new_req)
                await session.commit()

    return MinecraftStatusResponse(status="request_sent")


@mc_friends_router.post("/accept", response_model=MinecraftStatusResponse)
async def accept_friend_request(
    payload: MinecraftFriendActionPayload,
    auth_data: tuple[Optional[User], Optional[str]] = Depends(get_optional_mc_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Accept pending friend request by request_id or target_tag.
    Returns {"status": "accepted"}.
    """
    user, _ = auth_data
    if user:
        req = None
        if payload.request_id is not None:
            stmt = select(MinecraftFriendRequest).where(
                MinecraftFriendRequest.id == payload.request_id,
                MinecraftFriendRequest.receiver_id == user.telegram_id,
                MinecraftFriendRequest.status == "pending",
            )
            req = (await session.execute(stmt)).scalar_one_or_none()

        elif payload.target_tag:
            clean_tag = payload.target_tag.strip().lstrip("@").lower()
            sender_stmt = select(User).where(func.lower(User.username) == clean_tag)
            sender_user = (await session.execute(sender_stmt)).scalar_one_or_none()
            if sender_user:
                stmt = select(MinecraftFriendRequest).where(
                    MinecraftFriendRequest.sender_id == sender_user.telegram_id,
                    MinecraftFriendRequest.receiver_id == user.telegram_id,
                    MinecraftFriendRequest.status == "pending",
                )
                req = (await session.execute(stmt)).scalar_one_or_none()

        if req:
            req.status = "accepted"
            # Bidirectional friendship
            f1_stmt = select(MinecraftFriendship).where(
                MinecraftFriendship.user_id == user.telegram_id,
                MinecraftFriendship.friend_id == req.sender_id,
            )
            f1 = (await session.execute(f1_stmt)).scalar_one_or_none()
            if not f1:
                session.add(MinecraftFriendship(user_id=user.telegram_id, friend_id=req.sender_id))

            f2_stmt = select(MinecraftFriendship).where(
                MinecraftFriendship.user_id == req.sender_id,
                MinecraftFriendship.friend_id == user.telegram_id,
            )
            f2 = (await session.execute(f2_stmt)).scalar_one_or_none()
            if not f2:
                session.add(MinecraftFriendship(user_id=req.sender_id, friend_id=user.telegram_id))

            await session.commit()

    return MinecraftStatusResponse(status="accepted")


@mc_friends_router.post("/decline", response_model=MinecraftStatusResponse)
async def decline_friend_request(
    payload: MinecraftFriendActionPayload,
    auth_data: tuple[Optional[User], Optional[str]] = Depends(get_optional_mc_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Decline pending friend request by request_id or target_tag.
    Returns {"status": "declined"}.
    """
    user, _ = auth_data
    if user:
        req = None
        if payload.request_id is not None:
            stmt = select(MinecraftFriendRequest).where(
                MinecraftFriendRequest.id == payload.request_id,
                MinecraftFriendRequest.receiver_id == user.telegram_id,
                MinecraftFriendRequest.status == "pending",
            )
            req = (await session.execute(stmt)).scalar_one_or_none()

        elif payload.target_tag:
            clean_tag = payload.target_tag.strip().lstrip("@").lower()
            sender_stmt = select(User).where(func.lower(User.username) == clean_tag)
            sender_user = (await session.execute(sender_stmt)).scalar_one_or_none()
            if sender_user:
                stmt = select(MinecraftFriendRequest).where(
                    MinecraftFriendRequest.sender_id == sender_user.telegram_id,
                    MinecraftFriendRequest.receiver_id == user.telegram_id,
                    MinecraftFriendRequest.status == "pending",
                )
                req = (await session.execute(stmt)).scalar_one_or_none()

        if req:
            req.status = "declined"
            await session.commit()

    return MinecraftStatusResponse(status="declined")


# Parent router: prefix="/api" with redirect_slashes=False
minecraft_router = SlashRouter(prefix="/api", redirect_slashes=False)
minecraft_router.include_router(mc_auth_router)
minecraft_router.include_router(mc_server_router)
minecraft_router.include_router(mc_friends_router)

