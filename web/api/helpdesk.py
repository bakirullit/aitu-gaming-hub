import logging
from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import TicketStatus
from common.models.ticket import HelpdeskTicket
from common.models.user import User
from core.lifespan import runtime
from web.api.dependencies import get_current_admin, get_db_session

logger = logging.getLogger("web.api.helpdesk")

helpdesk_admin_router = APIRouter(prefix="/helpdesk", tags=["Admin Helpdesk"])


class TicketUserSummary(BaseModel):
    telegram_id: int
    username: str | None = None
    full_name: str | None = None
    barcode: str | None = None
    academic_group: str | None = None
    role: str = "guest"


class TicketItemResponse(BaseModel):
    id: int
    user_id: int
    subject: str
    message_text: str
    status: str
    admin_message_id: int | None = None
    created_at: datetime
    updated_at: datetime
    user: TicketUserSummary | None = None


class PaginatedTicketsResponse(BaseModel):
    items: list[TicketItemResponse]
    total: int
    limit: int
    offset: int
    open_count: int
    in_progress_count: int
    resolved_count: int


class TicketReplyRequest(BaseModel):
    reply: str = Field(..., min_length=1, max_length=4000)
    new_status: Optional[str] = Field(default="resolved")


class TicketStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="open, in_progress, resolved, closed")


@helpdesk_admin_router.get("/tickets", response_model=PaginatedTicketsResponse)
async def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    query: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
):
    """Lists helpdesk tickets with filtering, pagination, and user details."""
    stmt = (
        select(HelpdeskTicket, User)
        .outerjoin(User, User.telegram_id == HelpdeskTicket.user_id)
    )

    if status_filter:
        norm_status = status_filter.lower().strip()
        matching_status = next(
            (ts for ts in TicketStatus if ts.value.lower() == norm_status or ts.name.lower() == norm_status),
            None,
        )
        if matching_status:
            stmt = stmt.where(HelpdeskTicket.status == matching_status)

    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                HelpdeskTicket.subject.ilike(search_pattern),
                HelpdeskTicket.message_text.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.barcode.ilike(search_pattern),
            )
        )

    # Count total matching
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    # Aggregate overall status counts
    open_count = (
        await session.execute(
            select(func.count(HelpdeskTicket.id)).where(HelpdeskTicket.status == TicketStatus.OPEN)
        )
    ).scalar_one() or 0

    in_progress_count = (
        await session.execute(
            select(func.count(HelpdeskTicket.id)).where(HelpdeskTicket.status == TicketStatus.IN_PROGRESS)
        )
    ).scalar_one() or 0

    resolved_count = (
        await session.execute(
            select(func.count(HelpdeskTicket.id)).where(
                HelpdeskTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
            )
        )
    ).scalar_one() or 0

    # Sort newest first
    stmt = stmt.order_by(HelpdeskTicket.created_at.desc()).limit(limit).offset(offset)
    results = (await session.execute(stmt)).all()

    items: list[TicketItemResponse] = []
    for ticket, user in results:
        user_summary = None
        if user:
            full = f"{user.first_name or ''} {user.last_name or ''}".strip() or None
            user_summary = TicketUserSummary(
                telegram_id=user.telegram_id,
                username=user.username,
                full_name=full,
                barcode=user.barcode,
                academic_group=user.academic_group,
                role=str(user.role),
            )
        items.append(
            TicketItemResponse(
                id=ticket.id,
                user_id=ticket.user_id,
                subject=ticket.subject,
                message_text=ticket.message_text,
                status=ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
                admin_message_id=ticket.admin_message_id,
                created_at=ticket.created_at,
                updated_at=ticket.updated_at,
                user=user_summary,
            )
        )

    return PaginatedTicketsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        open_count=open_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
    )


@helpdesk_admin_router.get("/tickets/{ticket_id}", response_model=TicketItemResponse)
async def get_ticket(
    ticket_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
):
    stmt = (
        select(HelpdeskTicket, User)
        .outerjoin(User, User.telegram_id == HelpdeskTicket.user_id)
        .where(HelpdeskTicket.id == ticket_id)
    )
    res = (await session.execute(stmt)).first()
    if not res:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket, user = res
    user_summary = None
    if user:
        full = f"{user.first_name or ''} {user.last_name or ''}".strip() or None
        user_summary = TicketUserSummary(
            telegram_id=user.telegram_id,
            username=user.username,
            full_name=full,
            barcode=user.barcode,
            academic_group=user.academic_group,
            role=str(user.role),
        )

    return TicketItemResponse(
        id=ticket.id,
        user_id=ticket.user_id,
        subject=ticket.subject,
        message_text=ticket.message_text,
        status=ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
        admin_message_id=ticket.admin_message_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        user=user_summary,
    )


@helpdesk_admin_router.post("/tickets/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: int,
    payload: TicketReplyRequest,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
):
    stmt = select(HelpdeskTicket).where(HelpdeskTicket.id == ticket_id)
    ticket = (await session.execute(stmt)).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Update status if requested
    if payload.new_status:
        norm = payload.new_status.lower().strip()
        matching_status = next(
            (ts for ts in TicketStatus if ts.value.lower() == norm or ts.name.lower() == norm),
            None,
        )
        if matching_status:
            ticket.status = matching_status

    await session.commit()
    await session.refresh(ticket)

    # Dispatch reply to user in Telegram if bot is running
    notified = False
    if runtime.bot:
        try:
            msg_text = (
                f"🎫 <b>Ответ службы поддержки AITU Gaming</b>\n\n"
                f"<b>Тикет #{ticket.id}:</b> <i>{ticket.subject}</i>\n\n"
                f"<b>Ответ:</b>\n{payload.reply}\n\n"
                f"Статус тикета: <b>{ticket.status.value.upper()}</b>"
            )
            await runtime.bot.send_message(chat_id=ticket.user_id, text=msg_text)
            notified = True
        except Exception as exc:
            logger.warning(f"Could not deliver ticket reply to user {ticket.user_id}: {exc}")

    return {
        "status": "ok",
        "ticket_id": ticket.id,
        "new_status": ticket.status.value,
        "telegram_notified": notified,
    }


@helpdesk_admin_router.patch("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
):
    stmt = select(HelpdeskTicket).where(HelpdeskTicket.id == ticket_id)
    ticket = (await session.execute(stmt)).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    norm = payload.status.lower().strip()
    matching_status = next(
        (ts for ts in TicketStatus if ts.value.lower() == norm or ts.name.lower() == norm),
        None,
    )
    if not matching_status:
        raise HTTPException(status_code=400, detail=f"Invalid status '{payload.status}'")

    ticket.status = matching_status
    await session.commit()
    await session.refresh(ticket)

    return {
        "status": "ok",
        "ticket_id": ticket.id,
        "new_status": ticket.status.value,
    }
