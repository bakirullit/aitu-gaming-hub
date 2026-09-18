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


class DisciplineType(StrEnum):
    """Esports disciplines recognized in AITU Gaming Hub."""
    CS2 = "CS2"
    DOTA2 = "DOTA2"
    VALORANT = "VALORANT"
    FIFA = "FIFA"
    PUBG = "PUBG"
    MLBB = "MLBB"
    OTHER = "OTHER"


class TournamentStatus(StrEnum):
    """Lifecycle statuses for tournament booking slots."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

