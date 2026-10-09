import logging
from datetime import datetime, timezone
from aiogram import Bot
from fastapi import HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.chat import TelegramChat
from common.models.discipline import Discipline

logger = logging.getLogger("services.chat_service")


class ChatService:
    """Service handling Telegram chat identification, persistence, sync, and invite generation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self, active_only: bool = True) -> list[TelegramChat]:
        """Fetch all tracked Telegram chats, optionally filtered by active status."""
        stmt = select(TelegramChat)
        if active_only:
            stmt = stmt.where(TelegramChat.is_active == True)
        stmt = stmt.order_by(TelegramChat.updated_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, chat_id: int) -> TelegramChat | None:
        """Fetch chat record by its unique Telegram chat_id."""
        stmt = select(TelegramChat).where(TelegramChat.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_chat(
        self,
        chat_id: int,
        title: str,
        chat_type: str,
        username: str | None = None,
        is_active: bool = True,
        can_invite_users: bool = False,
        member_count: int | None = None,
    ) -> TelegramChat:
        """
        Creates or updates a Telegram chat record in the database.
        Maintains member count and invite permissions.
        """
        stmt = select(TelegramChat).where(TelegramChat.chat_id == chat_id)
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if chat:
            chat.title = title
            chat.username = username
            chat.chat_type = chat_type
            chat.is_active = is_active
            chat.can_invite_users = can_invite_users
            if member_count is not None:
                chat.member_count = member_count
            chat.updated_at = now
        else:
            chat = TelegramChat(
                chat_id=chat_id,
                title=title,
                username=username,
                chat_type=chat_type,
                is_active=is_active,
                can_invite_users=can_invite_users,
                member_count=member_count,
                created_at=now,
                updated_at=now,
            )
            self.session.add(chat)

        await self.session.commit()
        await self.session.refresh(chat)
        logger.info(
            f"Telegram chat {chat_id} ('{title}') upserted. active={is_active}, can_invite={can_invite_users}"
        )
        return chat

    async def handle_status_change(
        self,
        chat_id: int,
        title: str,
        chat_type: str,
        username: str | None,
        status_name: str,
        can_invite_users: bool = False,
    ) -> TelegramChat:
        """
        Handles ChatMemberUpdated status transitions:
        - kicked / left -> is_active = False
        - member / administrator / creator -> is_active = True
        """
        is_active = status_name not in ["kicked", "left"]
        return await self.upsert_chat(
            chat_id=chat_id,
            title=title,
            chat_type=chat_type,
            username=username,
            is_active=is_active,
            can_invite_users=can_invite_users if is_active else False,
        )

    async def migrate_chat_id(self, old_chat_id: int, new_chat_id: int) -> TelegramChat | None:
        """
        Handles group to supergroup migration atomically:
        Updates chat_id and sets chat_type to 'supergroup'.
        Also updates any linked disciplines pointing to the old chat_id.
        """
        stmt_old = select(TelegramChat).where(TelegramChat.chat_id == old_chat_id)
        old_chat = (await self.session.execute(stmt_old)).scalar_one_or_none()

        stmt_new = select(TelegramChat).where(TelegramChat.chat_id == new_chat_id)
        new_chat = (await self.session.execute(stmt_new)).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        target_chat: TelegramChat

        if old_chat and not new_chat:
            # Re-create / migrate old record with new primary key
            target_chat = TelegramChat(
                chat_id=new_chat_id,
                title=old_chat.title,
                username=old_chat.username,
                chat_type="supergroup",
                is_active=old_chat.is_active,
                can_invite_users=old_chat.can_invite_users,
                member_count=old_chat.member_count,
                created_at=old_chat.created_at,
                updated_at=now,
            )
            await self.session.delete(old_chat)
            self.session.add(target_chat)
        elif new_chat:
            target_chat = new_chat
            target_chat.chat_type = "supergroup"
            target_chat.updated_at = now
            if old_chat:
                await self.session.delete(old_chat)
        else:
            target_chat = TelegramChat(
                chat_id=new_chat_id,
                title="Supergroup",
                chat_type="supergroup",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            self.session.add(target_chat)

        # Update any disciplines linked to old_chat_id
        await self.session.execute(
            update(Discipline)
            .where(Discipline.chat_id == old_chat_id)
            .values(chat_id=new_chat_id)
        )

        await self.session.commit()
        await self.session.refresh(target_chat)
        logger.info(f"Migrated chat {old_chat_id} -> {new_chat_id} (supergroup)")
        return target_chat

    async def sync_chat_metadata(self, bot: Bot, chat_id: int) -> TelegramChat:
        """
        Syncs chat title, username, type, member count, and bot permissions via Telegram API.
        """
        try:
            tg_chat = await bot.get_chat(chat_id)
        except Exception as exc:
            logger.error(f"Failed to get_chat for {chat_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Telegram API get_chat failed: {str(exc)}",
            )

        title = tg_chat.title or tg_chat.full_name or "Untitled Chat"
        username = tg_chat.username
        chat_type = tg_chat.type

        member_count: int | None = None
        try:
            member_count = await bot.get_chat_member_count(chat_id)
        except Exception as exc:
            logger.debug(f"Could not retrieve member count for {chat_id}: {exc}")

        can_invite = False
        is_active = True
        try:
            bot_user = await bot.get_me()
            bot_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot_user.id)
            status_val = getattr(bot_member, "status", "unknown")
            is_active = status_val not in ["kicked", "left"]
            can_invite = bool(getattr(bot_member, "can_invite_users", False))
        except Exception as exc:
            logger.debug(f"Could not retrieve bot member status for {chat_id}: {exc}")

        return await self.upsert_chat(
            chat_id=chat_id,
            title=title,
            chat_type=chat_type,
            username=username,
            is_active=is_active,
            can_invite_users=can_invite,
            member_count=member_count,
        )

    async def create_invite_link(
        self,
        bot: Bot,
        chat_id: int,
        name: str | None = None,
        expire_date: datetime | int | None = None,
        member_limit: int | None = None,
    ) -> str:
        """
        Creates an invite link using bot.create_chat_invite_link.
        Requires can_invite_users right.
        """
        chat = await self.get_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found in database")

        if not chat.is_active:
            raise HTTPException(status_code=400, detail="Cannot create invite link: Bot is not active in this chat")

        try:
            invite = await bot.create_chat_invite_link(
                chat_id=chat_id,
                name=name,
                expire_date=expire_date,
                member_limit=member_limit,
            )
            return invite.invite_link
        except Exception as exc:
            logger.error(f"Failed to create invite link for {chat_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Telegram API error: {str(exc)}",
            )
