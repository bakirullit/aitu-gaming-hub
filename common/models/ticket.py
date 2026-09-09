from sqlalchemy import BigInteger, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from common.database.base import Base, TimestampMixin
from common.enums import TicketStatus


class HelpdeskTicket(Base, TimestampMixin):
    """Support ticket tracked between student Anchor Wizard and admin channel."""
    __tablename__ = "helpdesk_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    admin_message_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    subject: Mapped[str] = mapped_column(String(128), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus, name="ticket_status_enum"),
        default=TicketStatus.OPEN,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<HelpdeskTicket id={self.id} user_id={self.user_id} status={self.status}>"
