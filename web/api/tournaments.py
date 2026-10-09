from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.database.session import db_manager
from common.models.tournament import TournamentBooking
from common.models.user import User
from common.enums import DisciplineType, TournamentStatus
from common.dtos.web import (
    TournamentPublicResponse,
    PaginatedTournamentsResponse,
    TournamentStatsResponse,
)
from plugins.tournaments.screens import format_summary_label
from core.lifespan import runtime

tournaments_router = APIRouter(prefix="/tournaments", tags=["Public Tournaments"])


async def get_db_session():
    async with db_manager.session_factory() as session:
        yield session


def get_active_bot_username() -> str:
    """Return the runtime bot username if bot is running, else fallback to settings."""
    if runtime.bot and hasattr(runtime.bot, "_me") and runtime.bot._me and runtime.bot._me.username:
        return runtime.bot._me.username
    return getattr(settings, "BOT_USERNAME", "aitu_gaming_bot")


def serialize_tournament(booking: TournamentBooking, bot_username: str) -> TournamentPublicResponse:
    today = date.today()
    days_until = (booking.booking_date - today).days
    is_past = booking.booking_date < today

    creator_name = None
    if booking.creator:
        full = f"{booking.creator.first_name or ''} {booking.creator.last_name or ''}".strip()
        creator_name = full or (f"@{booking.creator.username}" if booking.creator.username else "AITU Esports")
    elif getattr(booking, "creator_steam_id", None):
        creator_name = f"Steam [{booking.creator_steam_id}]"
    else:
        creator_name = "AITU Esports"

    return TournamentPublicResponse(
        id=booking.id,
        title=booking.title,
        discipline=str(booking.discipline.value if hasattr(booking.discipline, "value") else booking.discipline),
        booking_date=booking.booking_date,
        event_format=booking.event_format,
        format_label=format_summary_label(booking.event_format),
        status=str(booking.status.value if hasattr(booking.status, "value") else booking.status),
        rulebook_url=booking.rulebook_url,
        rulebook_file_id=booking.rulebook_file_id,
        creator_name=creator_name,
        bot_registration_url=f"https://t.me/{bot_username}?start=tourn_{booking.id}",
        created_at=booking.created_at,
        days_until=days_until,
        is_past=is_past,
    )


@tournaments_router.get("", response_model=PaginatedTournamentsResponse)
async def list_public_tournaments(
    discipline: Optional[str] = Query(None, description="Filter by discipline e.g. CS2, DOTA2"),
    status: Optional[str] = Query(None, description="Filter by status: APPROVED, UPCOMING, PAST, ALL"),
    query: Optional[str] = Query(None, description="Search by tournament title or format"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Publicly accessible tournament directory.
    No authentication required. Returns all tournaments with bot registration links.
    """
    bot_username = get_active_bot_username()
    today = date.today()

    stmt = select(TournamentBooking).options(selectinload(TournamentBooking.creator))

    # Apply discipline filter
    if discipline and discipline.upper() != "ALL":
        try:
            disc_enum = DisciplineType(discipline.upper())
            stmt = stmt.where(TournamentBooking.discipline == disc_enum)
        except ValueError:
            stmt = stmt.where(TournamentBooking.discipline == discipline.upper())

    # Apply status filter
    if status:
        status_upper = status.upper()
        if status_upper == "UPCOMING":
            stmt = stmt.where(
                TournamentBooking.booking_date >= today,
                TournamentBooking.status == TournamentStatus.APPROVED,
            )
        elif status_upper == "PAST":
            stmt = stmt.where(
                or_(
                    TournamentBooking.booking_date < today,
                    TournamentBooking.status == TournamentStatus.APPROVED,
                )
            )
        elif status_upper != "ALL":
            try:
                st_enum = TournamentStatus(status_upper)
                stmt = stmt.where(TournamentBooking.status == st_enum)
            except ValueError:
                pass
    else:
        # Default behavior: show APPROVED and upcoming/recent tournaments
        pass

    # Apply search query
    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                TournamentBooking.title.ilike(search_pattern),
                TournamentBooking.event_format.ilike(search_pattern),
            )
        )

    # Calculate total count for the filtered query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Sort order: upcoming dates first, then newest created
    stmt = stmt.order_by(TournamentBooking.booking_date.asc(), TournamentBooking.id.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    bookings = result.scalars().all()

    # Aggregate overall statistics for the hero header
    stats_total_stmt = select(func.count(TournamentBooking.id))
    stats_upcoming_stmt = select(func.count(TournamentBooking.id)).where(
        TournamentBooking.booking_date >= today,
        TournamentBooking.status == TournamentStatus.APPROVED,
    )
    all_total = (await session.execute(stats_total_stmt)).scalar_one() or 0
    upcoming_total = (await session.execute(stats_upcoming_stmt)).scalar_one() or 0

    all_disciplines = [d.value for d in DisciplineType]

    stats = TournamentStatsResponse(
        total_tournaments=all_total,
        upcoming_tournaments=upcoming_total,
        active_disciplines=len(all_disciplines),
        disciplines=all_disciplines,
    )

    items = [serialize_tournament(b, bot_username) for b in bookings]

    return PaginatedTournamentsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        bot_username=bot_username,
        stats=stats,
    )


@tournaments_router.get("/{tournament_id}", response_model=TournamentPublicResponse)
async def get_public_tournament(
    tournament_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """Get single tournament details publicly."""
    bot_username = get_active_bot_username()

    stmt = (
        select(TournamentBooking)
        .options(selectinload(TournamentBooking.creator))
        .where(TournamentBooking.id == tournament_id)
    )
    result = await session.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail="Tournament not found")

    return serialize_tournament(booking, bot_username)
