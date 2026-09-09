import pytest
from common.dtos.events import DomainEvent, UserVerifiedEvent, TicketCreatedEvent
from common.enums import UserRole
from core.event_bus import InMemoryEventBus


@pytest.mark.asyncio
async def test_event_bus_dispatches_to_matching_subscribers() -> None:
    bus = InMemoryEventBus()
    received_events: list[UserVerifiedEvent] = []

    async def on_verified(event: UserVerifiedEvent) -> None:
        received_events.append(event)

    bus.subscribe(UserVerifiedEvent, on_verified)

    event = UserVerifiedEvent(
        telegram_id=12345678,
        student_id="210103001",
        barcode="123456789012",
        full_name="Alikhan Nurzhan",
        role=UserRole.STUDENT,
    )
    await bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0].student_id == "210103001"
    assert received_events[0].telegram_id == 12345678


@pytest.mark.asyncio
async def test_event_bus_circuit_breaker_isolates_failures() -> None:
    """If one subscriber raises an exception, other subscribers must still execute."""
    bus = InMemoryEventBus()
    executed_healthy: list[str] = []

    async def failing_subscriber(event: UserVerifiedEvent) -> None:
        raise RuntimeError("External network failed in subscriber!")

    async def healthy_subscriber(event: UserVerifiedEvent) -> None:
        executed_healthy.append(event.student_id)

    bus.subscribe(UserVerifiedEvent, failing_subscriber)
    bus.subscribe(UserVerifiedEvent, healthy_subscriber)

    event = UserVerifiedEvent(
        telegram_id=99999,
        student_id="220107055",
        barcode="987654321098",
        full_name="Dias Beket",
    )
    # Should not raise exception
    await bus.publish(event)

    assert len(executed_healthy) == 1
    assert executed_healthy[0] == "220107055"


@pytest.mark.asyncio
async def test_event_bus_rejects_non_domain_event_types() -> None:
    bus = InMemoryEventBus()

    class NonDomainEvent:
        pass

    with pytest.raises(TypeError):
        bus.subscribe(NonDomainEvent, lambda e: None)  # type: ignore
