import logging
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.enums import STAFF_ROLE_TITLES, StaffRole
from common.models.discipline import Discipline
from common.models.user import User
from common.utils.telegram_auth import validate_telegram_init_data
from services.user_service import UserService
from web.api.dependencies import get_current_user, get_db_session, get_user_service

logger = logging.getLogger("web.api.v1.lootbox")

lootbox_router = APIRouter(prefix="/v1/lootbox", tags=["Lootbox"])

security_optional = HTTPBearer(auto_error=False)


async def resolve_tma_or_bearer_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """
    Resolves user either from Bearer JWT or cryptographically validated Telegram WebApp initData.
    """
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"])
            telegram_id_str = payload.get("sub")
            if telegram_id_str:
                user = await user_service.get_by_telegram_id(int(telegram_id_str))
                if user:
                    return user
        except Exception as exc:
            logger.debug(f"Bearer token decode failed: {exc}")

    if x_telegram_init_data:
        try:
            parsed = validate_telegram_init_data(x_telegram_init_data, settings.BOT_TOKEN)
            tg_user = parsed.get("user")
            if tg_user and isinstance(tg_user, dict):
                tg_id = tg_user.get("id")
                if tg_id:
                    user = await user_service.get_by_telegram_id(int(tg_id))
                    if user:
                        return user
        except Exception as exc:
            logger.debug(f"validate_telegram_init_data failed: {exc}")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Требуется авторизация (Bearer токен или Telegram WebApp)",
    )


@lootbox_router.get("/status")
async def get_lootbox_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """Returns current user's mystery box / staff role status."""
    # Check if there is any pending role to claim on status check
    await user_service.claim_pending_role_if_exists(current_user)

    has_role = bool(current_user.staff_role and current_user.staff_role != StaffRole.NONE)
    role_key = (
        current_user.staff_role.value
        if hasattr(current_user.staff_role, "value")
        else str(current_user.staff_role)
    ).lower() if has_role else ""
    role_title = STAFF_ROLE_TITLES.get(role_key, role_key.title()) if has_role else None
    
    discipline_name = None
    if has_role and current_user.discipline_id:
        from common.models.discipline import Discipline
        disc_res = await session.execute(select(Discipline.name).where(Discipline.slug == current_user.discipline_id))
        discipline_name = disc_res.scalar_one_or_none() or current_user.discipline_id

    return {
        "has_role": has_role,
        "is_revealed": current_user.is_role_revealed,
        "first_name": current_user.first_name or "Participant",
        "staff_role": role_key if (has_role and current_user.is_role_revealed) else None,
        "role_title": role_title if (has_role and current_user.is_role_revealed) else None,
        "discipline": discipline_name if (has_role and current_user.is_role_revealed) else None,
    }


@lootbox_router.post("/open")
async def open_lootbox(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """Reveals the user's staff role and marks the lootbox as opened."""
    # Ensure any pending role is claimed
    await user_service.claim_pending_role_if_exists(current_user)

    if not current_user.staff_role or current_user.staff_role == StaffRole.NONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вам пока не назначена роль стаффа в AITU Gaming Hub.",
        )

    user, role_title, discipline_name = await user_service.reveal_role(current_user.telegram_id)

    role_key = (
        user.staff_role.value if hasattr(user.staff_role, "value") else str(user.staff_role)
    ).lower()

    return {
        "status": "success",
        "staff_role": role_key,
        "role_title": role_title,
        "discipline": discipline_name,
        "revealed_at": user.role_revealed_at.isoformat() if user.role_revealed_at else None,
    }
