import jwt
from fastapi import Depends, HTTPException, status
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

    if user.role not in [UserRole.HEAD_ADMIN, UserRole.DISCIPLINE_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return user


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

