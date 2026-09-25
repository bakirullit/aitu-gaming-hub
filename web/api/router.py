from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from common.database.session import db_manager
from common.models.user import User
from common.enums import UserRole
from common.dtos.web import UserResponse, PaginatedUsersResponse, RoleUpdateRequest
from web.api.dependencies import get_current_admin, get_db_session
from web.api.auth import auth_router
from web.api.disciplines import disciplines_router
from web.api.tournaments import tournaments_router
from core.lifespan import runtime

# Admin-only router (/api/admin/*)
web_router = APIRouter(prefix="/api/admin")
web_router.include_router(auth_router)
web_router.include_router(disciplines_router)

# Public router (/api/*) - accessible without auth
public_router = APIRouter(prefix="/api")
public_router.include_router(tournaments_router)



users_router = APIRouter(prefix="/users", tags=["Users"])

@users_router.get("", response_model=PaginatedUsersResponse)
async def get_users(
    query: Optional[str] = Query(None, description="Search by barcode, name, or group"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    stmt = select(User)
    
    if query:
        search_term = f"%{query}%"
        stmt = stmt.where(
            or_(
                User.barcode.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.academic_group.ilike(search_term),
                User.username.ilike(search_term)
            )
        )
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Get paginated data
    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    users = result.scalars().all()
    
    return PaginatedUsersResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        limit=limit,
        offset=offset
    )

@users_router.patch("/{telegram_id}/role", response_model=UserResponse)
async def update_role(
    telegram_id: int,
    payload: RoleUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    if telegram_id == admin.telegram_id and payload.role != admin.role:
        # Check if they are the only HEAD_ADMIN before allowing self-demotion
        if admin.role == UserRole.HEAD_ADMIN and payload.role != UserRole.HEAD_ADMIN:
            stmt_count = select(func.count()).where(User.role == UserRole.HEAD_ADMIN)
            head_admins_count = (await session.execute(stmt_count)).scalar_one()
            if head_admins_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot demote the only HEAD_ADMIN")
    
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.role = payload.role
    await session.commit()
    await session.refresh(user)

    # Invalidate navigation stack and interaction locks, preserving persistent anchor message ID
    stack_key = f"anchor:user:{telegram_id}:stack"
    stack_key_alt = f"anchor:{telegram_id}:stack"
    lock_key = f"lock:user:{telegram_id}"
    await runtime.redis.delete(stack_key, stack_key_alt, lock_key)

    # Immediately re-render the user's anchor message in-place to reflect updated menu options
    if runtime.core and runtime.core.navigator:
        anchor_id = await runtime.core.navigator.get_anchor_id(telegram_id)
        if anchor_id:
            try:
                from plugins.auth.screens import get_welcome_screen
                full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or (user.username and f"@{user.username}") or "Студент"
                welcome_screen = get_welcome_screen(is_verified=user.is_verified, full_name=full_name)
                await runtime.core.navigator.render(
                    user_id=telegram_id,
                    chat_id=telegram_id,
                    screen=welcome_screen,
                    screen_id="home",
                    push_to_history=False,
                )
            except Exception:
                pass

    return UserResponse.model_validate(user)

@users_router.delete("/{telegram_id}")
async def delete_user(
    telegram_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    if telegram_id == admin.telegram_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await session.delete(user)
    await session.commit()

    # Cache Invalidation
    anchor_key = f"anchor:user:{telegram_id}:message_id"
    stack_key = f"anchor:user:{telegram_id}:stack"
    lock_key = f"lock:user:{telegram_id}"
    await runtime.redis.delete(anchor_key, stack_key, lock_key)
    
    return {"status": "ok", "message": "User deleted"}

web_router.include_router(users_router)
