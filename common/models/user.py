from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, synonym
from common.database.base import Base, TimestampMixin
from common.enums import UserRole


class User(Base, TimestampMixin):
    """Core user record identified by Telegram ID with AITU academic verification."""
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    academic_group: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[str] = mapped_column(
        String(32),
        default="guest",
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    minecraft_nickname: Mapped[str | None] = mapped_column(String(32), nullable=True)
    steam_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    student_barcode = synonym("barcode")
    gmail = synonym("email")

    @property
    def id(self) -> int:
        return self.telegram_id

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} barcode={self.barcode} role={self.role}>"
