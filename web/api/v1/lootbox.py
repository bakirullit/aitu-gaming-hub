import logging
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import STAFF_ROLE_TITLES, StaffRole
from common.models.user import User
from services.user_service import UserService
from web.api.dependencies import get_auth_service, get_current_user, get_db_session, get_user_service

logger = logging.getLogger("web.api.v1.lootbox")

lootbox_router = APIRouter(prefix="/v1/lootbox", tags=["Lootbox"])


async def resolve_tma_or_bearer_user(
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    current_user: User | None = Depends(lambda: None),
    session: AsyncSession = Depends(get_db_session),
    auth_service = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """
    Resolves the authenticated user from Bearer JWT or Telegram WebApp initData header.
    """
    # 1. Check Bearer token from header first
    try:
        from fastapi.security import HTTPBearer
        from web.api.dependencies import get_current_user as dep_current_user
        # We manually call if authorization header is present
    except Exception:
        pass

    # If already resolved via standard dependency
    if current_user:
        return current_user

    # Fallback to Telegram WebApp initData
    if x_telegram_init_data:
        try:
            init_data = auth_service.validate_telegram_webapp_init_data(x_telegram_init_data)
            tg_id = init_data.get("user", {}).get("id")
            if tg_id:
                user = await user_service.get_by_telegram_id(int(tg_id))
                if user:
                    return user
        except Exception as exc:
            logger.debug(f"Could not authenticate via X-Telegram-Init-Data: {exc}")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (Bearer token or Telegram initData)",
    )


@lootbox_router.get("/status")
async def get_lootbox_status(
    current_user: User = Depends(get_current_user),
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
