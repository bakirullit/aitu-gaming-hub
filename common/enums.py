from enum import StrEnum


class UserRole(StrEnum):
    """Role-Based Access Control hierarchy."""
    STUDENT = "STUDENT"
    DISCIPLINE_ADMIN = "DISCIPLINE_ADMIN"
    HEAD_ADMIN = "HEAD_ADMIN"


class StaffRole(StrEnum):
    """Sub-roles under the general Staff umbrella."""
    DISCIPLINE_ADMIN = "discipline_admin"
    MANAGER = "manager"
    SMM = "smm"
    PRESIDENT = "president"
    VICE_PRESIDENT = "vice_president"
    DISCORD_ADMIN = "discord_admin"
    HEAD_ADMIN = "head_admin"
    HEAD_SMM = "head_smm"
    TRADE_ADMIN = "trade_admin"
    STREAMER = "streamer"
    COMMENTATOR = "commentator"
    COMMENTATER = "commentator"  # Backward compatibility alias


STAFF_ROLE_TITLES: dict[str, str] = {
    "discipline_admin": "Discipline Admin ⚔️",
    "manager": "Manager 📋",
    "smm": "SMM 📱",
    "president": "President 👑",
    "vice_president": "Vice President 🎖️",
    "vice president": "Vice President 🎖️",
    "discord_admin": "Discord Admin 💬",
    "head_admin": "Head Admin 🛡️",
    "head_smm": "Head SMM 📢",
    "trade_admin": "Trade Admin 💼",
    "streamer": "Streamer 🎥",
    "commentator": "Commentator 🎙️",
    "commentater": "Commentator 🎙️",
}


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

