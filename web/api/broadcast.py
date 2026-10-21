import asyncio
import logging
from typing import Any, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.chat import TelegramChat
from common.models.user import User
from core.lifespan import runtime
from web.api.dependencies import get_current_admin, get_db_session

logger = logging.getLogger("web.api.broadcast")

broadcast_admin_router = APIRouter(prefix="/broadcast", tags=["Admin Broadcast"])


class BroadcastSendRequest(BaseModel):
    target: str = Field(..., description="all, students, guests, chats, or chat:<id>")
    message: str = Field(..., min_length=1, max_length=4000)
    button_text: Optional[str] = Field(None, max_length=64)
    button_url: Optional[str] = Field(None, max_length=512)


@broadcast_admin_router.get("/audiences")
async def get_broadcast_audiences(
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
):
    total_users = (await session.execute(select(func.count(User.telegram_id)))).scalar_one() or 0
    students = (
        await session.execute(select(func.count(User.telegram_id)).where(User.is_verified == True))
    ).scalar_one() or 0
    guests = (
        await session.execute(select(func.count(User.telegram_id)).where(User.role == "guest"))
    ).scalar_one() or 0
    chats = (
        await session.execute(select(func.count(TelegramChat.telegram_chat_id)).where(TelegramChat.is_active == True))
    ).scalar_one() or 0

    # Get active chats list for direct selection
    chat_rows = (
        await session.execute(
            select(TelegramChat).where(TelegramChat.is_active == True).limit(20)
        )
    ).scalars().all()

    chat_options = [{"id": c.telegram_chat_id, "title": c.title or f"Chat {c.telegram_chat_id}"} for c in chat_rows]

    return {
        "audiences": [
            {"id": "all", "label": "Все пользователи", "count": total_users},
            {"id": "students", "label": "Студенты AITU", "count": students},
            {"id": "guests", "label": "Гости платформы", "count": guests},
            {"id": "chats", "label": "Все официальные чаты", "count": chats},
        ],
        "chats": chat_options,
    }


@broadcast_admin_router.post("/send")
async def send_broadcast(
    payload: BroadcastSendRequest,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
):
    if not runtime.bot:
        raise HTTPException(status_code=503, detail="Telegram Bot runtime instance is not available")

    # Resolve target IDs
    target_ids: list[int] = []
    if payload.target == "all":
        stmt = select(User.telegram_id)
        target_ids = list((await session.execute(stmt)).scalars().all())
    elif payload.target == "students":
        stmt = select(User.telegram_id).where(User.is_verified == True)
        target_ids = list((await session.execute(stmt)).scalars().all())
    elif payload.target == "guests":
        stmt = select(User.telegram_id).where(User.role == "guest")
        target_ids = list((await session.execute(stmt)).scalars().all())
    elif payload.target == "chats":
        stmt = select(TelegramChat.telegram_chat_id).where(TelegramChat.is_active == True)
        target_ids = list((await session.execute(stmt)).scalars().all())
    elif payload.target.startswith("chat:"):
        try:
            cid = int(payload.target.split(":", 1)[1])
            target_ids = [cid]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid chat ID target")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown target '{payload.target}'")

    if not target_ids:
        return {"status": "ok", "sent_count": 0, "failed_count": 0, "total_targets": 0}

    # Build reply markup if button provided
    reply_markup = None
    if payload.button_text and payload.button_url:
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=payload.button_text.strip(), url=payload.button_url.strip())]
            ]
        )

    sent = 0
    failed = 0
    for chat_id in target_ids:
        try:
            await runtime.bot.send_message(
                chat_id=chat_id,
                text=payload.message,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            sent += 1
            await asyncio.sleep(0.04)  # Safe rate limit: ~25 msgs/sec
        except Exception as exc:
            failed += 1
            logger.debug(f"Broadcast to {chat_id} failed: {exc}")

    return {
        "status": "ok",
        "sent_count": sent,
        "failed_count": failed,
        "total_targets": len(target_ids),
    }
