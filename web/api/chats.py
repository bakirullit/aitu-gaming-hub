import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.dtos.web import (
    InviteLinkRequest,
    InviteLinkResponse,
    TelegramChatResponse,
)
from common.models.user import User
from core.lifespan import runtime
from services.chat_service import ChatService
from web.api.dependencies import get_current_admin, get_db_session

logger = logging.getLogger("web.api.chats")

chats_router = APIRouter(prefix="/chats", tags=["Chats"])


@chats_router.get("", response_model=list[TelegramChatResponse])
async def list_chats(
    active_only: bool = Query(True, description="Filter only currently active chats"),
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> list[TelegramChatResponse]:
    """Returns all identified Telegram chats tracked by the bot."""
    service = ChatService(session=session)
    chats = await service.get_all(active_only=active_only)
    return [TelegramChatResponse.model_validate(c) for c in chats]


@chats_router.post("/{chat_id}/sync", response_model=TelegramChatResponse)
async def sync_chat(
    chat_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> TelegramChatResponse:
    """Manually refreshes chat title, username, member count, and bot permissions from Telegram API."""
    if not runtime.bot:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram Bot runtime instance is not available",
        )
    service = ChatService(session=session)
    chat = await service.sync_chat_metadata(bot=runtime.bot, chat_id=chat_id)
    return TelegramChatResponse.model_validate(chat)


@chats_router.post("/{chat_id}/invite-link", response_model=InviteLinkResponse)
async def create_chat_invite_link(
    chat_id: int,
    payload: InviteLinkRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> InviteLinkResponse:
    """Generates a new Telegram invite link for this chat if bot has can_invite_users permission."""
    if not runtime.bot:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram Bot runtime instance is not available",
        )
    service = ChatService(session=session)
    name = payload.name if payload else None
    expire_date = payload.expire_date if payload else None
    member_limit = payload.member_limit if payload else None

    link = await service.create_invite_link(
        bot=runtime.bot,
        chat_id=chat_id,
        name=name,
        expire_date=expire_date,
        member_limit=member_limit,
    )
    return InviteLinkResponse(invite_link=link)
