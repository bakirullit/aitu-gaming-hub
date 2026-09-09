from sqlalchemy import BigInteger, Enum as SQLEnum, String
from sqlalchemy.orm import Mapped, mapped_column
from common.database.base import Base, TimestampMixin
from common.enums import UserRole


class User(Base, TimestampMixin):
    """Core user record identified by Telegram ID with AITU academic verification."""
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    student_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum"),
        default=UserRole.STUDENT,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} student_id={self.student_id} role={self.role}>"
