from typing import TYPE_CHECKING, Any, Awaitable, Callable, Protocol, TypeVar, runtime_checkable
from aiogram import Router
from aiogram.types import Message
from common.dtos.screen import Screen
from common.dtos.events import DomainEvent

if TYPE_CHECKING:
    from core.context import CoreContext

E = TypeVar("E", bound=DomainEvent)


@runtime_checkable
class PluginProtocol(Protocol):
    """Protocol that every AITU Gaming Hub plugin module must fulfill."""
    name: str

    async def setup(self, core: "CoreContext") -> None:
        """Register routers, subscribe to domain events, and initialize plugin state."""
        ...

    async def teardown(self) -> None:
        """Clean up background tasks, connection pools, and external resources."""
        ...

    def get_router(self) -> Router:
        """Return the isolated Aiogram router containing the plugin's routes."""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """In-memory event bus protocol dedicated strictly to past-tense domain events."""

    def subscribe(self, event_type: type[Any], handler: Callable[[Any], Awaitable[None]]) -> None:
        """Register an async handler for a specific DomainEvent type."""
        ...

    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to all registered subscribers with isolated execution."""
        ...


@runtime_checkable
class NavigatorProtocol(Protocol):
    """Anchor Wizard UI Engine protocol managing single-message rendering and history."""

    async def render(
        self,
        user_id: int,
        chat_id: int,
        screen: Screen,
        screen_id: str | None = None,
        push_to_history: bool = True,
    ) -> Message | None:
        """Render a declarative screen into the user's single persistent anchor message."""
        ...

    async def back(self, user_id: int, chat_id: int) -> bool:
        """Navigate one step back in the user's LIFO navigation stack."""
        ...

    async def reset_history(self, user_id: int) -> None:
        """Clear navigation stack history for the user."""
        ...

    async def get_anchor_id(self, user_id: int) -> int | None:
        """Get the stored anchor message ID for the user."""
        ...

    async def set_anchor_id(self, user_id: int, message_id: int) -> None:
        """Update the stored anchor message ID for the user."""
        ...
