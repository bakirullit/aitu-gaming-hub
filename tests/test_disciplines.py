import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from common.database.base import Base
from common.enums import DisciplineType, UserRole
from common.models.user import User
from common.models.discipline import Discipline, DisciplineTier
from common.models.tournament import DisciplineAdmin
from services.discipline_service import DisciplineService
from plugins.disciplines.screens import (
    get_disciplines_catalog_screen,
    get_discipline_detail_screen,
    PAGE_SIZE,
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
async def test_assign_admin_promotion_and_atomic_sync(in_memory_db):
    """Test assigning a STUDENT promotes them to DISCIPLINE_ADMIN and syncs discipline_admins."""
    mock_redis = MagicMock()
    mock_redis.delete = AsyncMock(return_value=1)

    async with in_memory_db() as session:
        # Create student user
        student = User(
            telegram_id=5001,
            username="student_lead",
            first_name="Almas",
            role=UserRole.STUDENT,
            is_verified=True,
        )
        # Create discipline
        cs2 = Discipline(
            slug="cs2",
            name="Counter-Strike 2",
            tier=DisciplineTier.MAJOR,
            description="Official CS2 community",
            chat_url="https://t.me/aitu_cs2",
            admin_id=None,
            is_active=True,
        )
        session.add_all([student, cs2])
        await session.commit()

        # Assign student as CS2 curator
        updated_disc = await DisciplineService.assign_admin(
            discipline_slug="cs2",
            new_admin_id=5001,
            session=session,
            redis=mock_redis,
        )

        assert updated_disc.admin_id == 5001

        # Check user role promoted to DISCIPLINE_ADMIN
        u_res = await session.execute(select(User).where(User.telegram_id == 5001))
        promoted_user = u_res.scalar_one()
        assert promoted_user.role == UserRole.DISCIPLINE_ADMIN

        # Check atomic sync with discipline_admins table
        da_res = await session.execute(
            select(DisciplineAdmin).where(DisciplineAdmin.telegram_id == 5001)
        )
        da_record = da_res.scalar_one_or_none()
        assert da_record is not None
        assert da_record.discipline == DisciplineType.CS2

        # Check Redis invalidation called with navigation keys (preserving anchor message ID)
        mock_redis.delete.assert_awaited()
        deleted_keys = mock_redis.delete.call_args[0]
        assert "anchor:5001:stack" in deleted_keys
        assert "lock:user:5001" in deleted_keys
        assert "anchor:5001:message_id" not in deleted_keys



@pytest.mark.asyncio
async def test_assign_admin_demotion_to_student(in_memory_db):
    """Test unassigning a DISCIPLINE_ADMIN who curates 0 remaining disciplines demotes them to STUDENT."""
    mock_redis = MagicMock()
    mock_redis.delete = AsyncMock(return_value=1)

    async with in_memory_db() as session:
        curator = User(
            telegram_id=5002,
            username="curator_john",
            first_name="John",
            role=UserRole.DISCIPLINE_ADMIN,
            is_verified=True,
        )
        dota = Discipline(
            slug="dota2",
            name="Dota 2",
            tier=DisciplineTier.MAJOR,
            description="Dota 2 community",
            chat_url="https://t.me/aitu_dota",
            admin_id=5002,
            is_active=True,
        )
        da = DisciplineAdmin(telegram_id=5002, discipline=DisciplineType.DOTA2)
        session.add_all([curator, dota, da])
        await session.commit()

        # Unassign curator from dota2
        await DisciplineService.assign_admin(
            discipline_slug="dota2",
            new_admin_id=None,
            session=session,
            redis=mock_redis,
        )

        # Check user role demoted to STUDENT
        u_res = await session.execute(select(User).where(User.telegram_id == 5002))
        demoted_user = u_res.scalar_one()
        assert demoted_user.role == UserRole.STUDENT

        # Check discipline_admins record removed
        da_res = await session.execute(
            select(DisciplineAdmin).where(DisciplineAdmin.telegram_id == 5002)
        )
        assert da_res.scalar_one_or_none() is None

        # Check Redis invalidation
        mock_redis.delete.assert_awaited()


@pytest.mark.asyncio
async def test_multi_discipline_retention_role(in_memory_db):
    """Test curator of 2 disciplines is NOT demoted when removed from only 1 discipline."""
    mock_redis = MagicMock()
    mock_redis.delete = AsyncMock(return_value=1)

    async with in_memory_db() as session:
        curator = User(
            telegram_id=5003,
            username="multi_curator",
            first_name="Sanzhar",
            role=UserRole.DISCIPLINE_ADMIN,
            is_verified=True,
        )
        cs2 = Discipline(
            slug="cs2",
            name="CS2",
            tier=DisciplineTier.MAJOR,
            description="CS2",
            chat_url="https://t.me/cs2",
            admin_id=5003,
            is_active=True,
        )
        valorant = Discipline(
            slug="valorant",
            name="Valorant",
            tier=DisciplineTier.MEDIUM,
            description="Valorant",
            chat_url="https://t.me/val",
            admin_id=5003,
            is_active=True,
        )
        session.add_all([curator, cs2, valorant])
        await session.commit()

        # Unassign from valorant, but still curating cs2
        await DisciplineService.assign_admin(
            discipline_slug="valorant",
            new_admin_id=None,
            session=session,
            redis=mock_redis,
        )

        u_res = await session.execute(select(User).where(User.telegram_id == 5003))
        user = u_res.scalar_one()
        # MUST REMAIN DISCIPLINE_ADMIN because cs2 is still active!
        assert user.role == UserRole.DISCIPLINE_ADMIN


@pytest.mark.asyncio
async def test_head_admin_protection_guard(in_memory_db):
    """CRITICAL REQUIREMENT: HEAD_ADMIN role must NEVER be demoted under any circumstances."""
    mock_redis = MagicMock()
    mock_redis.delete = AsyncMock(return_value=1)

    async with in_memory_db() as session:
        head_admin = User(
            telegram_id=5004,
            username="boss_admin",
            first_name="Boss",
            role=UserRole.HEAD_ADMIN,
            is_verified=True,
        )
        fifa = Discipline(
            slug="fifa",
            name="FIFA",
            tier=DisciplineTier.MEDIUM,
            description="FIFA",
            chat_url="https://t.me/fifa",
            admin_id=5004,
            is_active=True,
        )
        session.add_all([head_admin, fifa])
        await session.commit()

        # Unassign head admin from fifa (0 remaining disciplines)
        await DisciplineService.assign_admin(
            discipline_slug="fifa",
            new_admin_id=None,
            session=session,
            redis=mock_redis,
        )

        u_res = await session.execute(select(User).where(User.telegram_id == 5004))
        user = u_res.scalar_one()
        # Must strictly preserve HEAD_ADMIN role!
        assert user.role == UserRole.HEAD_ADMIN


def test_bot_catalog_pagination_and_non_jumping_controls():
    """Verify native non-shifting inline keyboard controls for pagination."""
    # Create 14 mock disciplines (3 pages with PAGE_SIZE = 6: 6, 6, 2)
    disciplines = [
        Discipline(
            slug=f"game_{i}",
            name=f"Game {i:02d}",
            tier=DisciplineTier.MAJOR if i < 3 else DisciplineTier.MEDIUM,
            description=f"Description {i}",
            chat_url=f"https://t.me/game_{i}",
            is_active=True,
        )
        for i in range(1, 15)
    ]

    # Test Page 1 of 3: Left arrow must be inactive ('disc:noop'), right arrow active
    screen_p1 = get_disciplines_catalog_screen(disciplines=disciplines, page=1, page_size=6)
    assert "Страница: <b>1 из 3</b>" in screen_p1.text
    rows = screen_p1.reply_markup.inline_keyboard
    # Pagination row is second to last
    pag_row_p1 = rows[-2]
    assert len(pag_row_p1) == 3
    assert pag_row_p1[0].callback_data == "disc:noop"  # Inactive left
    assert "· 1/3 ·" in pag_row_p1[1].text
    assert pag_row_p1[1].callback_data == "disc:noop"  # Center badge
    assert pag_row_p1[2].callback_data == "disc:page:2"  # Active right

    # Test Page 2 of 3: Both arrows active
    screen_p2 = get_disciplines_catalog_screen(disciplines=disciplines, page=2, page_size=6)
    pag_row_p2 = screen_p2.reply_markup.inline_keyboard[-2]
    assert pag_row_p2[0].callback_data == "disc:page:1"
    assert "· 2/3 ·" in pag_row_p2[1].text
    assert pag_row_p2[2].callback_data == "disc:page:3"

    # Test Page 3 of 3: Right arrow must be inactive ('disc:noop')
    screen_p3 = get_disciplines_catalog_screen(disciplines=disciplines, page=3, page_size=6)
    pag_row_p3 = screen_p3.reply_markup.inline_keyboard[-2]
    assert pag_row_p3[0].callback_data == "disc:page:2"
    assert "· 3/3 ·" in pag_row_p3[1].text
    assert pag_row_p3[2].callback_data == "disc:noop"  # Inactive right


def test_discipline_detail_card_with_context_actions():
    """Verify detail card displays curator, chat URL, and context actions."""
    curator = User(
        telegram_id=999,
        username="steve_craft",
        first_name="Steve",
        role=UserRole.DISCIPLINE_ADMIN,
    )
    mc_disc = Discipline(
        slug="minecraft",
        name="Minecraft Campus",
        tier=DisciplineTier.MAJOR,
        description="Official survival and creative server of AITU.",
        chat_url="https://t.me/aitu_minecraft",
        admin_id=999,
        admin=curator,
        is_active=True,
    )

    screen = get_discipline_detail_screen(discipline=mc_disc, return_page=2)
    assert "Minecraft Campus" in screen.text
    assert "@steve_craft" in screen.text
    assert "Official survival" in screen.text

    buttons = [btn for row in screen.reply_markup.inline_keyboard for btn in row]
    # Verify Telegram chat URL button
    chat_btn = next((b for b in buttons if "Чат дисциплины" in b.text), None)
    assert chat_btn is not None
    assert chat_btn.url == "https://t.me/aitu_minecraft"

    # Verify context button for Minecraft
    mc_btn = next((b for b in buttons if "Управление вайтлистом" in b.text), None)
    assert mc_btn is not None
    assert mc_btn.callback_data == "nav:minecraft"

    # Verify exact origin return button
    back_btn = next((b for b in buttons if "Назад к списку" in b.text), None)
    assert back_btn is not None
    assert back_btn.callback_data == "disc:page:2"


@pytest.mark.asyncio
async def test_disciplines_api_crud_endpoints(in_memory_db):
    """Verify Web API endpoints for disciplines: GET, POST, PATCH, DELETE with auth."""
    from httpx import AsyncClient, ASGITransport
    from main import app
    from web.api.dependencies import get_current_admin, get_db_session

    head_admin_user = User(
        telegram_id=8888,
        username="lead_head",
        first_name="Lead",
        role=UserRole.HEAD_ADMIN,
        is_verified=True,
    )

    async def override_get_current_admin():
        return head_admin_user

    async def override_get_db_session():
        async with in_memory_db() as session:
            yield session

    app.dependency_overrides[get_current_admin] = override_get_current_admin
    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Create discipline
            create_resp = await ac.post(
                "/api/admin/disciplines",
                json={
                    "slug": "pubg",
                    "name": "PUBG Mobile",
                    "tier": "major",
                    "description": "Battle royale battles at AITU",
                    "chat_url": "https://t.me/pubg_aitu",
                },
            )
            assert create_resp.status_code == 201
            data = create_resp.json()
            assert data["slug"] == "pubg"
            assert data["tier"] == "major"
            assert data["is_active"] is True

            # 2. Get disciplines list
            list_resp = await ac.get("/api/admin/disciplines")
            assert list_resp.status_code == 200
            items = list_resp.json()
            assert any(d["slug"] == "pubg" for d in items)

            # 3. Patch discipline
            patch_resp = await ac.patch(
                "/api/admin/disciplines/pubg",
                json={
                    "name": "PUBG Mobile Champions",
                    "tier": "medium",
                },
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["name"] == "PUBG Mobile Champions"
            assert patch_resp.json()["tier"] == "medium"

            # 4. Delete (deactivate) discipline
            del_resp = await ac.delete("/api/admin/disciplines/pubg")
            assert del_resp.status_code == 200
            assert del_resp.json()["status"] == "ok"
    finally:
        app.dependency_overrides.clear()

