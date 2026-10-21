import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import TicketStatus, TournamentStatus
from common.models.minecraft import MinecraftSession, MinecraftWhitelist
from common.models.ticket import HelpdeskTicket
from common.models.tournament import TournamentBooking
from common.models.user import User
from web.api.dependencies import get_current_admin, get_db_session

logger = logging.getLogger("web.api.dashboard")

dashboard_admin_router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])


@dashboard_admin_router.get("/stats")
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    today = date.today()

    # 1. Members metrics
    total_users = (await session.execute(select(func.count(User.telegram_id)))).scalar_one() or 0
    verified_students = (
        await session.execute(
            select(func.count(User.telegram_id)).where(User.is_verified == True)
        )
    ).scalar_one() or 0
    guests = (
        await session.execute(
            select(func.count(User.telegram_id)).where(User.role == "guest")
        )
    ).scalar_one() or 0
    staff = (
        await session.execute(
            select(func.count(User.telegram_id)).where(User.role.in_(["staff", "head_admin", "discipline_admin"]))
        )
    ).scalar_one() or 0

    # 2. Tournaments metrics
    total_tournaments = (await session.execute(select(func.count(TournamentBooking.id)))).scalar_one() or 0
    pending_tournaments = (
        await session.execute(
            select(func.count(TournamentBooking.id)).where(TournamentBooking.status == TournamentStatus.PENDING)
        )
    ).scalar_one() or 0
    upcoming_tournaments = (
        await session.execute(
            select(func.count(TournamentBooking.id)).where(
                TournamentBooking.booking_date >= today,
                TournamentBooking.status == TournamentStatus.APPROVED,
            )
        )
    ).scalar_one() or 0

    # 3. Helpdesk metrics
    open_tickets = (
        await session.execute(
            select(func.count(HelpdeskTicket.id)).where(HelpdeskTicket.status == TicketStatus.OPEN)
        )
    ).scalar_one() or 0
    in_progress_tickets = (
        await session.execute(
            select(func.count(HelpdeskTicket.id)).where(HelpdeskTicket.status == TicketStatus.IN_PROGRESS)
        )
    ).scalar_one() or 0

    # 4. Minecraft metrics
    mc_whitelist = (await session.execute(select(func.count(MinecraftWhitelist.id)))).scalar_one() or 0
    mc_sessions = (await session.execute(select(func.count(MinecraftSession.id)))).scalar_one() or 0

    # 5. Timeline of registrations (past 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    timeline_stmt = (
        select(
            func.date(User.created_at).label("reg_date"),
            func.count(User.telegram_id).label("count"),
        )
        .where(User.created_at >= seven_days_ago)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at).asc())
    )
    timeline_rows = (await session.execute(timeline_stmt)).all()
    timeline = [{"date": str(r.reg_date), "count": r.count} for r in timeline_rows]

    # 6. Recent activities (top 5 users, top 5 tickets, top 5 bookings)
    recent_users = (
        await session.execute(
            select(User).order_by(User.created_at.desc()).limit(5)
        )
    ).scalars().all()

    recent_tickets = (
        await session.execute(
            select(HelpdeskTicket).order_by(HelpdeskTicket.created_at.desc()).limit(5)
        )
    ).scalars().all()

    recent_bookings = (
        await session.execute(
            select(TournamentBooking).order_by(TournamentBooking.created_at.desc()).limit(5)
        )
    ).scalars().all()

    activities = []
    for u in recent_users:
        activities.append({
            "type": "user_registered",
            "title": f"Новый участник: {u.first_name or ''} {u.last_name or ''}".strip() or str(u.telegram_id),
            "detail": f"Роль: {u.role} | Баркод: {u.barcode or '—'}",
            "time": u.created_at,
        })
    for t in recent_tickets:
        activities.append({
            "type": "ticket_opened",
            "title": f"Тикет #{t.id}: {t.subject}",
            "detail": f"Статус: {t.status.value}",
            "time": t.created_at,
        })
    for b in recent_bookings:
        activities.append({
            "type": "tournament_created",
            "title": f"Турнир: {b.title}",
            "detail": f"{b.discipline.value.upper()} | Дата: {b.booking_date} | Статус: {b.status.value}",
            "time": b.created_at,
        })

    # Sort activities newest first
    activities.sort(key=lambda x: x["time"] or datetime.min, reverse=True)
    recent_activity = activities[:10]

    return {
        "metrics": {
            "total_users": total_users,
            "verified_students": verified_students,
            "guests": guests,
            "staff": staff,
            "total_tournaments": total_tournaments,
            "pending_tournaments": pending_tournaments,
            "upcoming_tournaments": upcoming_tournaments,
            "open_tickets": open_tickets,
            "in_progress_tickets": in_progress_tickets,
            "mc_whitelist": mc_whitelist,
            "mc_sessions": mc_sessions,
        },
        "timeline": timeline,
        "recent_activity": recent_activity,
    }
