from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from common.database.base import Base, TimestampMixin


class MinecraftWhitelist(Base, TimestampMixin):
    """Minecraft server player registration and whitelist entry."""
    __tablename__ = "minecraft_whitelist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    nickname: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<MinecraftWhitelist user_id={self.user_id} nickname='{self.nickname}'>"


class MinecraftSession(Base, TimestampMixin):
    """Active session tokens for Minecraft client integration."""
    __tablename__ = "minecraft_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    session_token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    minecraft_nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<MinecraftSession user_id={self.user_id} nick='{self.minecraft_nickname}'>"


class MinecraftFriendship(Base, TimestampMixin):
    """Friendship relationship between users on the Minecraft network."""
    __tablename__ = "minecraft_friendships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    friend_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MinecraftFriendship user_id={self.user_id} friend_id={self.friend_id}>"


class MinecraftFriendRequest(Base, TimestampMixin):
    """Pending incoming/outgoing friend requests."""
    __tablename__ = "minecraft_friend_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    receiver_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    def __repr__(self) -> str:
        return f"<MinecraftFriendRequest id={self.id} {self.sender_id}->{self.receiver_id} ({self.status})>"

