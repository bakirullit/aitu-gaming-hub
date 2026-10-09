from common.database.base import Base, TimestampMixin

__all__ = ["Base", "TimestampMixin", "TelegramChat"]


def __getattr__(name: str):
    if name == "TelegramChat":
        from common.models.chat import TelegramChat
        return TelegramChat
    raise AttributeError(f"module {__name__} has no attribute {name}")

