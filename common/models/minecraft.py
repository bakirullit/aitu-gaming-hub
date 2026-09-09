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
