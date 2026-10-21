import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.database.session import db_manager
from common.models.user import User
from common.enums import UserRole

security = HTTPBearer()

async def get_db_session():
    async with db_manager.session_factory() as session:
        yield session

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """Dependency to validate JWT and ensure the user is an active admin."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        telegram_id_str = payload.get("sub")
        if telegram_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        telegram_id = int(telegram_id_str)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database to ensure they still exist and hold admin rights
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    is_admin = (
        user.is_discipline_admin
        or user.has_role("head_admin", "discipline_admin", "admin", "staff")
        or str(user.role).lower() in ["head_admin", "discipline_admin", "admin", "staff"]
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return user


security_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Dependency to validate JWT or Telegram WebApp initData and return the authenticated user."""
    # 1. Check Bearer token
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"])
            telegram_id_str = payload.get("sub")
            if telegram_id_str is not None:
                telegram_id = int(telegram_id_str)
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                if user is not None:
                    return user
        except (jwt.PyJWTError, ValueError):
            pass

    # 2. Check Telegram WebApp initData
    if x_telegram_init_data:
        try:
            from common.utils.telegram_auth import validate_telegram_init_data
            parsed = validate_telegram_init_data(x_telegram_init_data, settings.BOT_TOKEN)
            tg_user = parsed.get("user")
            if tg_user and isinstance(tg_user, dict):
                tg_id = tg_user.get("id")
                if tg_id:
                    stmt = select(User).where(User.telegram_id == int(tg_id))
                    result = await session.execute(stmt)
                    user = result.scalar_one_or_none()
                    if user is not None:
                        return user
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_redis():
    """Dependency yielding active Redis client."""
    from core.lifespan import runtime
    from redis.asyncio import from_url as redis_from_url

    if runtime.redis is not None:
        yield runtime.redis
    else:
        client = redis_from_url(settings.REDIS_URL, decode_responses=True)
        try:
            yield client
        finally:
            await client.aclose()


async def get_user_service(
    session: AsyncSession = Depends(get_db_session),
):
    from services.user_service import UserService
    return UserService(session=session)


async def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
    redis = Depends(get_redis),
):
    from services.auth_service import AuthService
    return AuthService(session=session, redis=redis, settings_obj=settings)


async def get_steam_service():
    from services.steam_service import SteamService
    return SteamService(settings_obj=settings)

