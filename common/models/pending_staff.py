from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database.base import Base
from common.enums import StaffRole


class PendingStaffMember(Base):
    """Pre-created staff member pending bot registration or identity verification."""
    __tablename__ = "pending_staff_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    academic_group: Mapped[str | None] = mapped_column(String(32), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    corp_email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    staff_role: Mapped[StaffRole] = mapped_column(
        SQLEnum(StaffRole, name="staffrole", values_callable=lambda x: [i.value for i in x], native_enum=False),
        default=StaffRole.NONE,
        nullable=False,
    )
    discipline_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("disciplines.slug", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    discipline = relationship("Discipline", foreign_keys=[discipline_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<PendingStaffMember id={self.id} name='{self.first_name} {self.last_name}' role={self.staff_role}>"
