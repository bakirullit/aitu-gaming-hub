import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from common.database.base import Base
from common.enums import UserRole
from common.models.user import User
from common.models.chat import TelegramChat
from common.models.discipline import Discipline, DisciplineTier
from services.chat_service import ChatService
from core.routers.chat_events import (
    handle_my_chat_member,
    handle_supergroup_migration_to,
    handle_supergroup_migration_from,
)


@pytest.fixture
async def in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_chat_service_upsert_and_status(in_memory_db):
    async with in_memory_db() as session:
        service = ChatService(session=session)

        # 1. Upsert new chat
        chat = await service.upsert_chat(
            chat_id=-100111222,
            title="Dota 2 Hub",
            chat_type="supergroup",
            username="aitu_dota2",
            is_active=True,
            can_invite_users=True,
            member_count=42,
        )
        assert chat.chat_id == -100111222
        assert chat.title == "Dota 2 Hub"
        assert chat.is_active is True
        assert chat.can_invite_users is True
        assert chat.member_count == 42

        # 2. Status change to kicked
        updated = await service.handle_status_change(
            chat_id=-100111222,
            title="Dota 2 Hub",
            chat_type="supergroup",
            username="aitu_dota2",
            status_name="kicked",
            can_invite_users=False,
        )
        assert updated.is_active is False
        assert updated.can_invite_users is False

        # 3. Status change to administrator
        readded = await service.handle_status_change(
            chat_id=-100111222,
            title="Dota 2 Hub Renamed",
            chat_type="supergroup",
            username="aitu_dota2",
            status_name="administrator",
            can_invite_users=True,
        )
        assert readded.is_active is True
        assert readded.can_invite_users is True
        assert readded.title == "Dota 2 Hub Renamed"


@pytest.mark.asyncio
async def test_chat_service_migration(in_memory_db):
    async with in_memory_db() as session:
        service = ChatService(session=session)

        # Create old group
        await service.upsert_chat(
            chat_id=-555000,
            title="Old CS Group",
            chat_type="group",
            is_active=True,
            can_invite_users=False,
        )

        # Create discipline pointing to old group
        disc = Discipline(
            slug="cs2",
            name="Counter-Strike 2",
            tier=DisciplineTier.MAJOR,
            description="CS2 Discipline",
            chat_url="https://t.me/c/555000",
            chat_id=-555000,
            is_active=True,
        )
        session.add(disc)
        await session.commit()

        # Migrate to supergroup
        migrated = await service.migrate_chat_id(old_chat_id=-555000, new_chat_id=-100555000)
        assert migrated.chat_id == -100555000
        assert migrated.chat_type == "supergroup"

        # Check old chat removed
        old_chat = await service.get_by_id(-555000)
        assert old_chat is None

        # Check discipline updated
        await session.refresh(disc)
        assert disc.chat_id == -100555000


@pytest.mark.asyncio
async def test_chat_events_router_my_chat_member(in_memory_db):
    async with in_memory_db() as session:
        # Mock ChatMemberUpdated event for adding bot as admin
        mock_event = MagicMock()
        mock_event.chat.id = -100999888
        mock_event.chat.type = "supergroup"
        mock_event.chat.title = "Valorant Official"
        mock_event.chat.username = "aitu_val"
        mock_event.new_chat_member.status = "administrator"
        mock_event.new_chat_member.can_invite_users = True

        await handle_my_chat_member(event=mock_event, session=session)

        service = ChatService(session=session)
        chat = await service.get_by_id(-100999888)
        assert chat is not None
        assert chat.title == "Valorant Official"
        assert chat.is_active is True
        assert chat.can_invite_users is True

        # Now bot gets kicked
        mock_kick_event = MagicMock()
        mock_kick_event.chat.id = -100999888
        mock_kick_event.chat.type = "supergroup"
        mock_kick_event.chat.title = "Valorant Official"
        mock_kick_event.chat.username = "aitu_val"
        mock_kick_event.new_chat_member.status = "kicked"
        mock_kick_event.new_chat_member.can_invite_users = False

        await handle_my_chat_member(event=mock_kick_event, session=session)
        chat = await service.get_by_id(-100999888)
        assert chat.is_active is False
        assert chat.can_invite_users is False


@pytest.mark.asyncio
async def test_chat_events_router_migrations(in_memory_db):
    async with in_memory_db() as session:
        service = ChatService(session=session)
        await service.upsert_chat(chat_id=-12345, title="Group Before Migration", chat_type="group")

        # Migrate to
        msg_to = MagicMock()
        msg_to.chat.id = -12345
        msg_to.migrate_to_chat_id = -10012345
        await handle_supergroup_migration_to(msg_to, session=session)

        chat = await service.get_by_id(-10012345)
        assert chat is not None
        assert chat.chat_type == "supergroup"

        # Migrate from
        msg_from = MagicMock()
        msg_from.chat.id = -10099999
        msg_from.migrate_from_chat_id = -10012345
        await handle_supergroup_migration_from(msg_from, session=session)

        migrated_again = await service.get_by_id(-10099999)
        assert migrated_again is not None
        assert migrated_again.chat_type == "supergroup"


@pytest.mark.asyncio
async def test_chats_api_endpoints(in_memory_db):
    from httpx import AsyncClient, ASGITransport
    from main import app
    from web.api.dependencies import get_current_admin, get_db_session
    from core.lifespan import runtime

    admin_user = User(
        telegram_id=7777,
        username="admin_lead",
        first_name="Admin",
        role=UserRole.HEAD_ADMIN,
        is_verified=True,
    )

    async def override_get_current_admin():
        return admin_user

    async def override_get_db_session():
        async with in_memory_db() as session:
            yield session

    app.dependency_overrides[get_current_admin] = override_get_current_admin
    app.dependency_overrides[get_db_session] = override_get_db_session

    # Seed chats
    async with in_memory_db() as session:
        service = ChatService(session=session)
        await service.upsert_chat(
            chat_id=-100111,
            title="Active Chat",
            chat_type="supergroup",
            is_active=True,
            can_invite_users=True,
            member_count=50,
        )
        await service.upsert_chat(
            chat_id=-100222,
            title="Inactive Chat",
            chat_type="group",
            is_active=False,
            can_invite_users=False,
            member_count=10,
        )

    # Setup mock bot in runtime
    mock_bot = AsyncMock()
    mock_tg_chat = MagicMock()
    mock_tg_chat.title = "Active Chat Synced"
    mock_tg_chat.username = "active_synced"
    mock_tg_chat.type = "supergroup"
    mock_bot.get_chat.return_value = mock_tg_chat
    mock_bot.get_chat_member_count.return_value = 55
    mock_bot_user = MagicMock(id=999)
    mock_bot.get_me.return_value = mock_bot_user
    mock_bot_member = MagicMock()
    mock_bot_member.status = "administrator"
    mock_bot_member.can_invite_users = True
    mock_bot.get_chat_member.return_value = mock_bot_member

    mock_invite = MagicMock()
    mock_invite.invite_link = "https://t.me/+joinchat123"
    mock_bot.create_chat_invite_link.return_value = mock_invite

    runtime.bot = mock_bot

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. GET /api/admin/chats (active_only=true)
            resp = await ac.get("/api/admin/chats?active_only=true")
            assert resp.status_code == 200
            chats = resp.json()
            assert len(chats) == 1
            assert chats[0]["chat_id"] == -100111

            # 2. GET /api/admin/chats (active_only=false)
            resp_all = await ac.get("/api/admin/chats?active_only=false")
            assert resp_all.status_code == 200
            chats_all = resp_all.json()
            assert len(chats_all) == 2

            # 3. POST /api/admin/chats/{chat_id}/sync
            sync_resp = await ac.post("/api/admin/chats/-100111/sync")
            assert sync_resp.status_code == 200
            sync_data = sync_resp.json()
            assert sync_data["title"] == "Active Chat Synced"
            assert sync_data["username"] == "active_synced"
            assert sync_data["member_count"] == 55
            assert sync_data["can_invite_users"] is True

            # 4. POST /api/admin/chats/{chat_id}/invite-link
            link_resp = await ac.post(
                "/api/admin/chats/-100111/invite-link",
                json={"name": "Test Invite", "member_limit": 10},
            )
            assert link_resp.status_code == 200
            assert link_resp.json()["invite_link"] == "https://t.me/+joinchat123"

            # 5. POST invite-link on inactive chat should fail 400
            err_resp = await ac.post("/api/admin/chats/-100222/invite-link")
            assert err_resp.status_code == 400
    finally:
        app.dependency_overrides.clear()
        runtime.bot = None
