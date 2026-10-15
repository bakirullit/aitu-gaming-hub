import secrets
import asyncio
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.database.session import db_manager
from common.models.user import User
from common.enums import UserRole

from common.dtos.web import (
    OTPRequest,
    OTPVerify,
    TelegramWebAppAuthRequest,
    TokenResponse,
    UserResponse,
)
from common.utils.telegram_auth import validate_telegram_init_data
from web.api.dependencies import get_db_session


# We import runtime to access bot and redis instances injected at lifespan
from core.lifespan import runtime

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

async def _delete_otp_message_delayed(chat_id: int, message_id: int, key: str):
    """Deletes the OTP message after 180 seconds if it hasn't been verified."""
    await asyncio.sleep(180)
    if await runtime.redis.exists(key):
        try:
            await runtime.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
        await runtime.redis.delete(key)

@auth_router.post("/otp/request")
async def request_otp(
    payload: OTPRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Generates an OTP, saves it in Redis, and sends it via Telegram bot."""
    identifier = payload.identifier.strip()
    
    stmt = select(User)
    if identifier.startswith("@"):
        stmt = stmt.where(User.username == identifier[1:])
    else:
        try:
            telegram_id = int(identifier)
            stmt = stmt.where(User.telegram_id == telegram_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid identifier format")
    
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    is_admin = (
        user.is_discipline_admin
        or user.has_role("head_admin", "discipline_admin", "admin", "staff")
        or str(user.role).lower() in ["head_admin", "discipline_admin", "admin", "staff"]
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden: User is not an admin")

    # Check cooldown
    cooldown_key = f"auth:otp:cooldown:{user.telegram_id}"
    if await runtime.redis.get(cooldown_key):
        raise HTTPException(status_code=429, detail="Please wait 60s before requesting a new code")

    # Generate 6-digit secure code
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    
    # Dispatch via bot
    try:
        msg = await runtime.bot.send_message(
            chat_id=user.telegram_id,
            text=f"🔐 <b>Ваш код авторизации в Админ Панель:</b>\n\n<code>{code}</code>\n\nНикому не сообщайте этот код. Он автоматически удалится через 3 минуты.",
            parse_mode="HTML"
        )
    except Exception as e:
        # Prevent lockout if bot cannot send message
        await runtime.redis.delete(cooldown_key)
        raise HTTPException(status_code=500, detail=f"Failed to send Telegram message: {str(e)}")

    # Save to Redis
    otp_key = f"auth:otp:{user.telegram_id}"
    msg_key = f"auth:otp:msg:{user.telegram_id}"
    
    await runtime.redis.set(otp_key, code, ex=180)  # 3 minutes expiry
    await runtime.redis.set(msg_key, msg.message_id, ex=180)
    await runtime.redis.set(cooldown_key, "1", ex=60) # 1 minute cooldown

    # Background task to clean up message if not verified
    asyncio.create_task(_delete_otp_message_delayed(user.telegram_id, msg.message_id, msg_key))

    return {"status": "ok", "message": "Code sent to Telegram", "telegram_id": user.telegram_id}


@auth_router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(
    payload: OTPVerify,
    session: AsyncSession = Depends(get_db_session)
):
    """Verifies OTP from Redis and issues a JWT token."""
    otp_key = f"auth:otp:{payload.telegram_id}"
    msg_key = f"auth:otp:msg:{payload.telegram_id}"
    
    saved_code = await runtime.redis.get(otp_key)
    
    if not saved_code or saved_code != payload.code:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
        
    # Valid code: delete message immediately
    msg_id = await runtime.redis.get(msg_key)
    if msg_id:
        try:
            await runtime.bot.delete_message(chat_id=payload.telegram_id, message_id=int(msg_id))
        except Exception:
            pass
            
    # Clean up keys to prevent replay
    await runtime.redis.delete(otp_key, msg_key)
    
    stmt = select(User).where(User.telegram_id == payload.telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    is_admin = (
        user.is_discipline_admin
        or user.has_role("head_admin", "discipline_admin", "admin", "staff")
        or str(user.role).lower() in ["head_admin", "discipline_admin", "admin", "staff"]
    )
    if not user or not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Generate JWT
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    jwt_payload = {
        "sub": str(user.telegram_id),
        "role": role_val,
        "roles": user.roles or [],
        "is_admin": is_admin,
        "exp": expire,
    }
    access_token = jwt.encode(jwt_payload, settings.JWT_SECRET, algorithm="HS256")
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
        is_admin=is_admin,
    )


@auth_router.post("/telegram/webapp", response_model=TokenResponse)
async def auth_telegram_webapp(
    payload: TelegramWebAppAuthRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Seamless authentication for Telegram Web App / Mini App.
    Cryptographically validates initData using bot token via HMAC-SHA256.
    Ensures user exists in the database and returns JWT session token.
    """
    bot_token = settings.BOT_TOKEN
    try:
        validated = validate_telegram_init_data(
            init_data=payload.init_data,
            bot_token=bot_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Telegram Web App data: {str(exc)}"
        )

    tg_user = validated.get("user") or {}
    telegram_id = tg_user.get("id")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing telegram user ID in initData"
        )

    # Fetch user or create if new
    stmt = select(User).where(User.telegram_id == int(telegram_id))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    first_name = tg_user.get("first_name") or ""
    last_name = tg_user.get("last_name") or ""
    username = tg_user.get("username")
    now = datetime.now(timezone.utc)

    if not user:
        full_name = f"{first_name} {last_name}".strip() or username or "Telegram User"
        user = User(
            telegram_id=int(telegram_id),
            username=username,
            first_name=first_name or "Telegram User",
            last_name=last_name or None,
            full_name=full_name,
            role="guest",
            roles=[],
            is_verified=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
    else:
        # Update username/names if provided
        if username and user.username != username:
            user.username = username
        if first_name and not user.first_name:
            user.first_name = first_name
        if last_name and not user.last_name:
            user.last_name = last_name
        user.updated_at = now

    await session.commit()
    await session.refresh(user)

    is_admin = bool(user.is_admin)

    # Issue JWT token
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    jwt_payload = {
        "sub": str(user.telegram_id),
        "role": role_val,
        "roles": user.roles or [],
        "is_admin": is_admin,
        "exp": expire,
    }
    access_token = jwt.encode(jwt_payload, settings.JWT_SECRET, algorithm="HS256")

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
        is_admin=is_admin,
    )

