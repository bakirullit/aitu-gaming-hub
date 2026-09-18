import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import UserRole
from common.models.discipline import DisciplineTier
from common.models.user import User
from common.dtos.web import (
    DisciplineResponse,
    DisciplineCreateRequest,
    DisciplineUpdateRequest,
)
from core.lifespan import runtime
from services.discipline_service import DisciplineService
from web.api.dependencies import get_current_admin, get_db_session

logger = logging.getLogger("web.api.disciplines")

disciplines_router = APIRouter(prefix="/disciplines", tags=["Disciplines"])


def _ensure_head_admin(admin: User) -> None:
    if admin.role != UserRole.HEAD_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Head Admins can manage disciplines and curators",
        )


@disciplines_router.get("", response_model=list[DisciplineResponse])
async def get_disciplines(
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> list[DisciplineResponse]:
    """Return all disciplines with joined curator details."""
    disciplines = await DisciplineService.get_all(session=session, active_only=False)
    return [DisciplineResponse.model_validate(d) for d in disciplines]


@disciplines_router.post("", response_model=DisciplineResponse, status_code=status.HTTP_201_CREATED)
async def create_discipline(
    payload: DisciplineCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> DisciplineResponse:
    """Create a new discipline and optionally assign an initial curator."""
    _ensure_head_admin(admin)

    try:
        tier_enum = DisciplineTier(payload.tier.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{payload.tier}'. Must be 'major' or 'medium'.",
        )

    try:
        discipline = await DisciplineService.create(
            slug=payload.slug,
            name=payload.name,
            tier=tier_enum,
            description=payload.description,
            chat_url=payload.chat_url,
            admin_id=payload.admin_id,
            session=session,
            redis=runtime.redis,
        )
        return DisciplineResponse.model_validate(discipline)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@disciplines_router.patch("/{slug}", response_model=DisciplineResponse)
async def update_discipline(
    slug: str,
    payload: DisciplineUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> DisciplineResponse:
    """Update discipline details or reassign curator via DisciplineService."""
    _ensure_head_admin(admin)

    update_fields = {}
    if payload.name is not None:
        update_fields["name"] = payload.name
    if payload.tier is not None:
        try:
            update_fields["tier"] = DisciplineTier(payload.tier.lower())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tier")
    if payload.description is not None:
        update_fields["description"] = payload.description
    if payload.chat_url is not None:
        update_fields["chat_url"] = payload.chat_url
    if payload.is_active is not None:
        update_fields["is_active"] = payload.is_active
    if payload.admin_id is not None or "admin_id" in payload.model_fields_set:
        update_fields["admin_id"] = payload.admin_id

    try:
        discipline = await DisciplineService.update(
            slug=slug,
            session=session,
            redis=runtime.redis,
            **update_fields,
        )
        return DisciplineResponse.model_validate(discipline)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@disciplines_router.delete("/{slug}")
async def delete_discipline(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> dict[str, str]:
    """Safe removal or deactivation of discipline and curator detachment."""
    _ensure_head_admin(admin)

    try:
        await DisciplineService.delete_or_deactivate(
            slug=slug,
            session=session,
            redis=runtime.redis,
        )
        return {"status": "ok", "message": f"Discipline '{slug}' deactivated"}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
