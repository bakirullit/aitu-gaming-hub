from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class TelegramChat(Base):
    """
    Identified Telegram group, supergroup, or channel where the bot has been added.
    Tracks membership lifecycle, invite permissions, and member count.
    """
    __tablename__ = "telegram_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_type: Mapped[str] = mapped_column(String(32), nullable=False)  # group, supergroup, channel
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_invite_users: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    member_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TelegramChat chat_id={self.chat_id} title='{self.title}' type={self.chat_type} is_active={self.is_active}>"
