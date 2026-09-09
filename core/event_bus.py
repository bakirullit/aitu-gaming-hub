from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
import logging
from common.dtos.events import DomainEvent
from core.protocols import EventBusProtocol

logger = logging.getLogger("core.event_bus")

E = TypeVar("E", bound=DomainEvent)


class InMemoryEventBus(EventBusProtocol):
    """Asynchronous in-memory event bus dedicated strictly to past-tense Domain Events."""

    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[Callable[[Any], Awaitable[None]]]] = (
            defaultdict(list)
        )

    def subscribe(self, event_type: type[Any], handler: Callable[[Any], Awaitable[None]]) -> None:
        """Register a subscriber handler for a specific DomainEvent type."""
        if not issubclass(event_type, DomainEvent):
            raise TypeError(f"Cannot subscribe to non-DomainEvent type: {event_type}")

        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler '{handler.__qualname__}' to '{event_type.__name__}'")

    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to all subscribers with isolated failure boundaries."""
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.debug(f"No subscribers for domain event '{event_type.__name__}' (id={event.event_id})")
            return

        logger.info(
            f"Dispatching domain event '{event_type.__name__}' (id={event.event_id}) "
            f"to {len(handlers)} subscriber(s)"
        )

        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:
                # Circuit-breaker boundary: one subscriber failing MUST NOT affect others
                logger.error(
                    f"Error in event handler '{handler.__qualname__}' "
                    f"processing event '{event_type.__name__}': {exc}",
                    exc_info=True,
                )
