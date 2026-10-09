from datetime import date
from sqlalchemy import BigInteger, Date, Enum as SQLEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database.base import Base, TimestampMixin
from common.enums import DisciplineType, TournamentStatus


class DisciplineAdmin(Base, TimestampMixin):
    """Binds a verified user to one or more esports disciplines as an administrator."""
    __tablename__ = "discipline_admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    discipline: Mapped[DisciplineType] = mapped_column(
        SQLEnum(DisciplineType, name="discipline_type_enum"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("telegram_id", "discipline", name="uq_admin_discipline"),
    )

    user: Mapped["User"] = relationship("User", backref="discipline_roles")  # type: ignore # noqa: F821

    def __repr__(self) -> str:
        return f"<DisciplineAdmin telegram_id={self.telegram_id} discipline={self.discipline}>"


class TournamentBooking(Base, TimestampMixin):
    """Tournament booking application processed through the Anchor Wizard."""
    __tablename__ = "tournament_bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    creator_steam_id: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
        nullable=True,
    )
    discipline: Mapped[DisciplineType] = mapped_column(
        SQLEnum(DisciplineType, name="discipline_type_enum"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(128), nullable=False)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    event_format: Mapped[str] = mapped_column(String(32), nullable=False)  # "online_single_elim_2x2"
    rulebook_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Telegram file_id
    rulebook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    status: Mapped[TournamentStatus] = mapped_column(
        SQLEnum(TournamentStatus, name="tournament_status_enum"),
        default=TournamentStatus.PENDING,
        nullable=False,
    )
    approval_msg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    creator: Mapped["User | None"] = relationship("User", backref="tournament_bookings")  # type: ignore # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<TournamentBooking id={self.id} discipline={self.discipline} "
            f"date={self.booking_date} status={self.status}>"
        )
