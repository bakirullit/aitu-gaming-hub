from dataclasses import dataclass
from aiogram.types import InlineKeyboardMarkup


@dataclass(frozen=True)
class Screen:
    """Declarative view specification for the Single Anchor Message UI Engine."""
    text: str
    reply_markup: InlineKeyboardMarkup | None = None
    parse_mode: str = "HTML"
