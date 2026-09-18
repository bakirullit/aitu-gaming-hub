from datetime import datetime
import enum
from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SQLEnum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class DisciplineTier(str, enum.Enum):
    """Tier grouping for esports disciplines by community scale."""
    MAJOR = "major"    # Large (> 200 members)
    MEDIUM = "medium"  # Medium (50-200 members)


class Discipline(Base):
    """Dynamic discipline model managed via Web Admin Panel and queried by Telegram Bot."""
    __tablename__ = "disciplines"

    slug: Mapped[str] = mapped_column(String(32), primary_key=True)  # e.g. "cs2", "valorant"
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[DisciplineTier] = mapped_column(
        SQLEnum(DisciplineTier, name="discipline_tier"),
        default=DisciplineTier.MEDIUM,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    chat_url: Mapped[str] = mapped_column(String(255), nullable=False)

    # Curator assignment
    admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    admin = relationship("User", foreign_keys=[admin_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<Discipline slug={self.slug} name={self.name} tier={self.tier} admin_id={self.admin_id}>"
