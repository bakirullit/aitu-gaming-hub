import logging
import time
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.models.ticket import HelpdeskTicket
from common.models.tournament import TournamentBooking
from common.models.user import User
from core.lifespan import runtime
from web.api.dependencies import get_current_admin, get_db_session

logger = logging.getLogger("web.api.logs")

logs_admin_router = APIRouter(prefix="/logs", tags=["Admin Logs & Health"])


@logs_admin_router.get("/health")
async def get_system_health(
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    # 1. Database check
    db_ok = False
    db_latency_ms = None
    try:
        t0 = time.perf_counter()
        await session.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_ok = True
    except Exception as exc:
        logger.error(f"DB health check failed: {exc}")

    # 2. Redis check
    redis_ok = False
    redis_latency_ms = None
    if runtime.redis:
        try:
            t0 = time.perf_counter()
            await runtime.redis.ping()
            redis_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            redis_ok = True
        except Exception as exc:
            logger.warning(f"Redis health check failed: {exc}")

    # 3. Telegram Bot check
    bot_ok = bool(runtime.bot)
    bot_username = None
    if runtime.bot and hasattr(runtime.bot, "_me") and runtime.bot._me:
        bot_username = runtime.bot._me.username or settings.BOT_USERNAME
    else:
        bot_username = settings.BOT_USERNAME

    # 4. Resend / Mail SDK check
    mail_configured = bool(settings.RESEND_API_KEY)

    # 5. Minecraft RCON check
    mc_configured = bool(settings.MINECRAFT_RCON_PASSWORD)

    return {
        "database": {
            "status": "UP" if db_ok else "DOWN",
            "latency_ms": db_latency_ms,
            "engine": "PostgreSQL 16",
        },
        "redis": {
            "status": "UP" if redis_ok else "DOWN",
            "latency_ms": redis_latency_ms,
        },
        "telegram_bot": {
            "status": "UP" if bot_ok else "OFFLINE",
            "bot_username": bot_username,
        },
        "email_service": {
            "status": "CONFIGURED" if mail_configured else "MOCK_MODE",
            "provider": "Resend API",
        },
        "minecraft_rcon": {
            "status": "CONFIGURED" if mc_configured else "DISABLED",
            "host": getattr(settings, "MINECRAFT_SERVER_IP", "127.0.0.1"),
        },
        "timestamp": datetime.now().isoformat(),
    }


@logs_admin_router.get("/audit")
async def get_audit_logs(
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    events = []

    # Recent tickets
    tickets = (
        await session.execute(
            select(HelpdeskTicket).order_by(HelpdeskTicket.created_at.desc()).limit(15)
        )
    ).scalars().all()
    for t in tickets:
        events.append({
            "source": "Helpdesk",
            "level": "INFO" if t.status.value in ["resolved", "closed"] else "WARN",
            "event": f"Тикет #{t.id} [{t.status.value.upper()}]: {t.subject}",
            "actor": f"User ID {t.user_id}",
            "timestamp": t.updated_at or t.created_at,
        })

    # Recent tournament bookings
    bookings = (
        await session.execute(
            select(TournamentBooking).order_by(TournamentBooking.created_at.desc()).limit(15)
        )
    ).scalars().all()
    for b in bookings:
        events.append({
            "source": "Tournaments",
            "level": "SUCCESS" if b.status.value == "approved" else ("WARN" if b.status.value == "pending" else "INFO"),
            "event": f"Турнир '{b.title}' [{b.status.value.upper()}] на {b.booking_date}",
            "actor": f"Creator ID {b.creator_id or b.creator_steam_id or 'Admin'}",
            "timestamp": b.updated_at or b.created_at,
        })

    # Recent staff updates
    staff = (
        await session.execute(
            select(User).where(User.staff_role != "none").order_by(User.updated_at.desc()).limit(15)
        )
    ).scalars().all()
    for s in staff:
        name = f"{s.first_name or ''} {s.last_name or ''}".strip() or s.username or str(s.telegram_id)
        box_state = "Раскрыт" if s.is_role_revealed else "Запечатан"
        events.append({
            "source": "Staff",
            "level": "INFO",
            "event": f"Staff {name}: роль {s.staff_role.value if hasattr(s.staff_role, 'value') else s.staff_role} (Бокс: {box_state})",
            "actor": f"Telegram ID {s.telegram_id}",
            "timestamp": s.updated_at or s.created_at,
        })

    events.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)

    return {
        "items": events[:30]
    }
