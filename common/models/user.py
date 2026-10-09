from sqlalchemy import BigInteger, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, synonym
from common.database.base import Base, TimestampMixin
from common.enums import STAFF_ROLE_TITLES, UserRole


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
    roles: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
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

    @property
    def all_roles(self) -> list[str]:
        """All unique roles and sub-roles belonging to this user in lowercase with underscores."""
        res: set[str] = set()
        if self.role:
            res.add(str(self.role).lower().replace(" ", "_"))
        if self.roles and isinstance(self.roles, list):
            for r in self.roles:
                if isinstance(r, str):
                    res.add(r.lower().replace(" ", "_"))
        return list(res)

    def has_role(self, *targets: str) -> bool:
        """Checks if user has any of target roles or 'staff' if holding any staff sub-role."""
        current = set(self.all_roles)
        for t in targets:
            norm = t.lower().replace(" ", "_")
            if norm in current:
                return True
            if "head_admin" in current and norm in ["discipline_admin", "staff", "admin"]:
                return True
            if norm == "staff":
                if "staff" in current or any(r in STAFF_ROLE_TITLES for r in current):
                    return True
        return False

    @property
    def is_staff(self) -> bool:
        return self.has_role("staff")

    @property
    def is_discipline_admin(self) -> bool:
        return self.has_role("discipline_admin", "head_admin")

    def get_staff_roles_display(self) -> list[str]:
        """Friendly display names for all user's staff sub-roles."""
        displayed: list[str] = []
        for r in self.all_roles:
            norm = r.replace(" ", "_")
            if norm in STAFF_ROLE_TITLES:
                title = STAFF_ROLE_TITLES[norm]
                if title not in displayed:
                    displayed.append(title)
        return displayed

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} barcode={self.barcode} role={self.role} roles={self.roles}>"
