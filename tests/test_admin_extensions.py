import pytest
from datetime import date, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from main import app
from common.database.base import Base
from common.enums import DisciplineType, TournamentStatus, UserRole, TicketStatus
from common.models.user import User
from common.models.tournament import TournamentBooking
from common.models.discipline import Discipline, DisciplineTier
from common.models.ticket import HelpdeskTicket
from common.models.minecraft import MinecraftWhitelist
from web.api.dependencies import get_current_admin, get_db_session


@pytest.fixture
async def test_env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    admin_user = User(
        telegram_id=777888999,
        username="superadmin",
        first_name="Super",
        last_name="Admin",
        role=UserRole.HEAD_ADMIN,
        is_verified=True,
    )

    async with session_factory() as session:
        session.add(admin_user)
        # Add discipline
        disc = Discipline(
            slug="valorant",
            name="Valorant",
            description="Tactical shooter discipline",
            chat_url="https://t.me/aitu_valorant",
            tier=DisciplineTier.MAJOR,
            is_active=True,
        )
        session.add(disc)
        # Add a pending booking
        booking = TournamentBooking(
            id=1,
            creator_id=admin_user.telegram_id,
            discipline=DisciplineType.OTHER,
            title="Valorant Open Cup",
            booking_date=date.today() + timedelta(days=10),
            event_format="online_single_elim_5x5",
            status=TournamentStatus.PENDING,
        )
        session.add(booking)
        # Add a helpdesk ticket
        ticket = HelpdeskTicket(
            id=1,
            user_id=admin_user.telegram_id,
            status=TicketStatus.OPEN,
            subject="Help with tournament registration",
            message_text="Need help registering my team",
        )
        session.add(ticket)
        await session.commit()

    async def override_get_current_admin():
        return admin_user

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    yield session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_dashboard(test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/admin/dashboard/stats", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 200
        data = res.json()
        assert "metrics" in data
        assert "timeline" in data


@pytest.mark.asyncio
async def test_admin_tournaments_workflow(test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get moderation list
        res = await client.get("/api/admin/tournaments", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) >= 1

        # Approve booking
        res = await client.post("/api/admin/tournaments/1/approve", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 200
        assert res.json()["status"] == TournamentStatus.APPROVED.value


@pytest.mark.asyncio
async def test_admin_helpdesk_workflow(test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List tickets
        res = await client.get("/api/admin/helpdesk/tickets", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 200
        assert len(res.json()["items"]) >= 1

        # Reply to ticket
        res = await client.post(
            "/api/admin/helpdesk/tickets/1/reply",
            headers={"Authorization": "Bearer fake"},
            json={"reply": "Everything is resolved now.", "new_status": "closed"}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert res.json()["new_status"] == TicketStatus.CLOSED.value


@pytest.mark.asyncio
async def test_admin_minecraft_workflow(test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check status
        res = await client.get("/api/admin/minecraft/status", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 200
        assert "online" in res.json()

        # Add whitelist
        res = await client.post(
            "/api/admin/minecraft/whitelist",
            headers={"Authorization": "Bearer fake"},
            json={"nickname": "Steve_AITU"}
        )
        assert res.status_code == 200
        entry_id = res.json()["id"]

        # Delete whitelist
        res = await client.delete(f"/api/admin/minecraft/whitelist/{entry_id}", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_admin_settings_workflow(test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/admin/settings", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 200
        assert res.json()["registration_open"] is True

        res = await client.post(
            "/api/admin/settings",
            headers={"Authorization": "Bearer fake"},
            json={"club_name": "AITU Esports"}
        )
        assert res.status_code == 200
        assert res.json()["settings"]["club_name"] == "AITU Esports"
