import logging
from aiogram import F, Router
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from services.chat_service import ChatService

logger = logging.getLogger("core.routers.chat_events")

chat_events_router = Router(name="chat_events_router")


@chat_events_router.my_chat_member(
    ~F.chat.type.in_({"private"})
)
async def handle_my_chat_member(event: ChatMemberUpdated, session: AsyncSession) -> None:
    """
    Handles addition of the bot to groups/supergroups/channels,
    status changes (administrator/member/kicked/left), and permission updates.
    """
    chat = event.chat
    if chat.type == "private":
        return

    new_member = event.new_chat_member
    status_name = getattr(new_member, "status", "member")
    can_invite = bool(getattr(new_member, "can_invite_users", False))
    title = chat.title or chat.full_name or "Untitled Chat"

    service = ChatService(session=session)
    await service.handle_status_change(
        chat_id=chat.id,
        title=title,
        chat_type=chat.type,
        username=chat.username,
        status_name=status_name,
        can_invite_users=can_invite,
    )
    logger.info(
        f"Tracked bot status change in chat {chat.id} ('{title}'): status={status_name}, can_invite={can_invite}"
    )


@chat_events_router.message(F.migrate_to_chat_id)
async def handle_supergroup_migration_to(message: Message, session: AsyncSession) -> None:
    """Handles group migration to supergroup when received on the original group."""
    old_chat_id = message.chat.id
    new_chat_id = message.migrate_to_chat_id
    if not new_chat_id:
        return

    service = ChatService(session=session)
    await service.migrate_chat_id(old_chat_id=old_chat_id, new_chat_id=new_chat_id)
    logger.info(f"Handled group migration: {old_chat_id} -> {new_chat_id}")


@chat_events_router.message(F.migrate_from_chat_id)
async def handle_supergroup_migration_from(message: Message, session: AsyncSession) -> None:
    """Handles group migration to supergroup when received on the new supergroup."""
    old_chat_id = message.migrate_from_chat_id
    new_chat_id = message.chat.id
    if not old_chat_id:
        return

    service = ChatService(session=session)
    await service.migrate_chat_id(old_chat_id=old_chat_id, new_chat_id=new_chat_id)
    logger.info(f"Handled group migration from: {old_chat_id} -> {new_chat_id}")
