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
        first_name="Alikhan",
        last_name="Nurzhan",
        barcode="123456",
        phone_number="+77771234567",
        email="alikhan@gmail.com",
        academic_group="CS-2424",
        role=UserRole.STUDENT,
    )
    await bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0].first_name == "Alikhan"
    assert received_events[0].telegram_id == 12345678


@pytest.mark.asyncio
async def test_event_bus_circuit_breaker_isolates_failures() -> None:
    """If one subscriber raises an exception, other subscribers must still execute."""
    bus = InMemoryEventBus()
    executed_healthy: list[str] = []

    async def failing_subscriber(event: UserVerifiedEvent) -> None:
        raise RuntimeError("External network failed in subscriber!")

    async def healthy_subscriber(event: UserVerifiedEvent) -> None:
        executed_healthy.append(event.barcode)

    bus.subscribe(UserVerifiedEvent, failing_subscriber)
    bus.subscribe(UserVerifiedEvent, healthy_subscriber)

    event = UserVerifiedEvent(
        telegram_id=99999,
        first_name="Dias",
        last_name="Beket",
        barcode="654321",
        phone_number="+77777654321",
        email="dias@gmail.com",
        academic_group="SE-2331",
    )
    # Should not raise exception
    await bus.publish(event)

    assert len(executed_healthy) == 1
    assert executed_healthy[0] == "654321"


@pytest.mark.asyncio
async def test_event_bus_rejects_non_domain_event_types() -> None:
    bus = InMemoryEventBus()

    class NonDomainEvent:
        pass

    with pytest.raises(TypeError):
        bus.subscribe(NonDomainEvent, lambda e: None)  # type: ignore
