from enum import StrEnum


class UserRole(StrEnum):
    """Role-Based Access Control hierarchy."""
    STUDENT = "STUDENT"
    DISCIPLINE_ADMIN = "DISCIPLINE_ADMIN"
    HEAD_ADMIN = "HEAD_ADMIN"


class TicketStatus(StrEnum):
    """Lifecycle statuses for support tickets."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
