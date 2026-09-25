import pytest
from datetime import date, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from main import app
from common.database.base import Base
from common.database.session import db_manager
from common.enums import DisciplineType, TournamentStatus, UserRole
from common.models.user import User
from common.models.tournament import TournamentBooking


from web.api.tournaments import get_db_session

@pytest.fixture
async def test_db_setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Populate test data
    async with session_factory() as session:
        user = User(
            telegram_id=9999,
            username="tourn_organizer",
            first_name="Organ",
            last_name="Izer",
            email="org@aitu.edu.kz",
            role=UserRole.DISCIPLINE_ADMIN,
            is_verified=True,
        )
        session.add(user)
        await session.commit()

        # Add 2 tournaments: 1 approved CS2 upcoming, 1 pending DOTA2
        t1 = TournamentBooking(
            creator_id=9999,
            discipline=DisciplineType.CS2,
            title="AITU CS2 Major Cup 2026",
            booking_date=date.today() + timedelta(days=5),
            event_format="online_single_elim_5x5",
            status=TournamentStatus.APPROVED,
            rulebook_url="https://aitu.edu.kz/rules/cs2.pdf",
        )
        t2 = TournamentBooking(
            creator_id=9999,
            discipline=DisciplineType.DOTA2,
            title="Dota 2 Campus Clash",
            booking_date=date.today() + timedelta(days=12),
            event_format="lan_double_elim_5x5",
            status=TournamentStatus.PENDING,
        )
        session.add_all([t1, t2])
        await session.commit()

    yield session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_public_tournaments_list_without_auth(test_db_setup):
    """Verify tournament list is accessible publicly without any auth token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tournaments")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "stats" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Check first item fields
    item = data["items"][0]
    assert item["title"] == "AITU CS2 Major Cup 2026"
    assert item["discipline"] == "CS2"
    assert "bot_registration_url" in item
    assert "tourn_" in item["bot_registration_url"]
    assert "format_label" in item
    assert item["is_past"] is False
    assert item["creator_name"] == "Organ Izer"


@pytest.mark.asyncio
async def test_public_tournaments_filter_by_discipline(test_db_setup):
    """Verify filtering by discipline works correctly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tournaments?discipline=DOTA2")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Dota 2 Campus Clash"


@pytest.mark.asyncio
async def test_public_tournaments_filter_by_status(test_db_setup):
    """Verify filtering by status works correctly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tournaments?status=APPROVED")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_public_tournaments_get_single(test_db_setup):
    """Verify single tournament detail endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        list_res = await ac.get("/api/tournaments")
        first_id = list_res.json()["items"][0]["id"]

        detail_res = await ac.get(f"/api/tournaments/{first_id}")

    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == first_id
