from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from common.enums import UserRole


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all inter-plugin past-tense domain events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class UserVerifiedEvent(DomainEvent):
    """Fired when an AITU student passes verification with student ID & barcode."""
    telegram_id: int = 0
    student_id: str = ""
    barcode: str = ""
    full_name: str = ""
    role: UserRole = UserRole.STUDENT


@dataclass(frozen=True)
class TicketCreatedEvent(DomainEvent):
    """Fired when a user submits a support ticket through the Anchor Wizard."""
    ticket_id: int = 0
    user_id: int = 0
    subject: str = ""
    message_text: str = ""


@dataclass(frozen=True)
class TicketRepliedEvent(DomainEvent):
    """Fired when an admin replies to a support ticket from the admin channel."""
    ticket_id: int = 0
    user_id: int = 0
    admin_id: int = 0
    reply_text: str = ""
