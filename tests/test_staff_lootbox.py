import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from common.database.base import Base
from common.enums import StaffRole, STAFF_ROLE_TITLES
from common.models.discipline import Discipline, DisciplineTier
from common.models.pending_staff import PendingStaffMember
from common.models.user import User
from plugins.auth.screens import get_profile_screen
from services.user_service import UserService


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_enums_and_titles():
    assert StaffRole.DESIGNER == "designer"
    assert StaffRole.NONE == "none"
    assert "designer" in STAFF_ROLE_TITLES
    assert "none" in STAFF_ROLE_TITLES


@pytest.mark.asyncio
async def test_precreate_and_claim_flow(async_session: AsyncSession):
    # 1. Create a test discipline
    disc = Discipline(
        slug="cs2",
        name="Counter-Strike 2",
        tier=DisciplineTier.MAJOR,
        description="Valve tactical shooter",
        chat_url="https://t.me/aitu_cs2",
        is_active=True,
    )
    async_session.add(disc)
    await async_session.commit()

    service = UserService(async_session)

    # 2. Precreate staff member
    pending = await service.precreate_staff_member(
        first_name="Алихан",
        last_name="Сериков",
        staff_role=StaffRole.DESIGNER,
        academic_group="SE-2611",
        barcode="231145",
        email="alikhan@gmail.com",
        corp_email="231145@astanait.edu.kz",
        phone_number="+77071112233",
        username="alikhan_design",
        discipline_id="cs2",
    )
    assert pending.id is not None
    assert pending.staff_role == StaffRole.DESIGNER

    # 3. Simulate user arriving in bot
    user = User(
        telegram_id=999888,
        username="alikhan_design",
        full_name="Алихан Сериков",
        first_name="Алихан",
        last_name="Сериков",
        email="231145@astanait.edu.kz",
        barcode="231145",
        academic_group="SE-2611",
        role="student",
        is_verified=True,
    )
    async_session.add(user)
    await async_session.commit()

    # 4. Claim pending role
    claimed = await service.claim_pending_role_if_exists(user)
    assert claimed is True
    assert user.staff_role == StaffRole.DESIGNER
    assert user.discipline_id == "cs2"
    assert user.is_role_revealed is False

    # Pending record must be removed
    pending_check = await async_session.get(PendingStaffMember, pending.id)
    assert pending_check is None

    # 5. Profile screen should show the Lootbox button
    profile_data = {
        "full_name": user.full_name,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "role": user.role,
        "staff_role": user.staff_role,
        "is_role_revealed": user.is_role_revealed,
        "discipline_name": "Counter-Strike 2",
    }
    screen_sealed = get_profile_screen(profile_data)
    assert "Вам назначена роль" in screen_sealed.text
    assert any("Открыть Лутбокс" in btn.text for row in screen_sealed.reply_markup.inline_keyboard for btn in row)

    # 6. Reveal role (Open Lootbox)
    user, role_title, disc_name = await service.reveal_role(user.telegram_id)
    assert user.is_role_revealed is True
    assert user.role_revealed_at is not None
    assert "Designer" in role_title

    # 7. Profile screen should now show role badge and view role card button
    profile_data["is_role_revealed"] = True
    screen_opened = get_profile_screen(profile_data)
    assert "Должность:" in screen_opened.text
    assert any("Моя карточка роли" in btn.text for row in screen_opened.reply_markup.inline_keyboard for btn in row)


@pytest.mark.asyncio
async def test_lootbox_and_admin_api_endpoints():
    from httpx import AsyncClient, ASGITransport
    from main import app
    from web.api.dependencies import get_current_admin, get_current_user, get_db_session

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    test_admin = User(
        telegram_id=111222,
        username="head_admin",
        full_name="Admin Adminov",
        first_name="Admin",
        role="head_admin",
        is_verified=True,
    )
    test_user = User(
        telegram_id=333444,
        username="lucky_staff",
        full_name="Lucky Student",
        first_name="Lucky",
        role="student",
        staff_role=StaffRole.MANAGER,
        is_role_revealed=False,
        is_verified=True,
    )

    async with session_maker() as session:
        session.add(test_admin)
        session.add(test_user)
        disc = Discipline(
            slug="dota2",
            name="Dota 2",
            tier=DisciplineTier.MAJOR,
            description="Valve MOBA",
            chat_url="https://t.me/aitu_dota",
            is_active=True,
        )
        session.add(disc)
        await session.commit()

    async def override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_admin] = lambda: test_admin
    app.dependency_overrides[get_current_user] = lambda: test_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Check lootbox status
        res_status = await client.get("/api/v1/lootbox/status")
        assert res_status.status_code == 200
        data = res_status.json()
        assert data["has_role"] is True
        assert data["is_revealed"] is False
        assert data["first_name"] == "Lucky"

        # 2. Open lootbox
        res_open = await client.post("/api/v1/lootbox/open")
        assert res_open.status_code == 200
        open_data = res_open.json()
        assert open_data["status"] == "success"
        assert open_data["staff_role"] == "manager"
        assert "Manager" in open_data["role_title"]

        # 3. Precreate pending staff via Admin API
        payload = {
            "first_name": "Дамир",
            "last_name": "Касымов",
            "staff_role": "commentator",
            "academic_group": "CS-2401",
            "username": "damir_caster",
            "discipline_id": "dota2",
        }
        res_create = await client.post("/api/admin/staff/pending", json=payload)
        assert res_create.status_code == 201

        # 4. List pending staff
        res_list = await client.get("/api/admin/staff/pending")
        assert res_list.status_code == 200
        pending_items = res_list.json()
        assert len(pending_items) >= 1
        assert any(p["username"] == "damir_caster" for p in pending_items)

        # 5. Import CSV
        csv_content = (
            "Имя,Фамилия,Группа,Barcode,Телефон,Почта,Никнейм,Роль,Дисциплина\n"
            "Ернар,Асетов,IT-2511,241001,+77051234567,241001@astanait.edu.kz,ernar_smm,smm,dota2\n"
        )
        files = {"file": ("staff.csv", csv_content.encode("utf-8"), "text/csv")}
        res_import = await client.post("/api/admin/staff/pending/import-csv", files=files)
        assert res_import.status_code == 200
        assert res_import.json()["created"] == 1

        # 6. Import TSV with Windows CRLF / CR endings without header
        tsv_crlf = (
            "Mereikhan\tSholanbayev\tIT-2511\t251562\t+77012888882\tmr.dragunov.99.dragun@gmail.com\t@V0Lc4No112\tDiscipline_Admin\r\n"
            "Erasyl\tSaut\tSE-2611\t260496\t+77000010488\t260496@astanait.edu.kz\t@kidfac3\tDiscipline_Admin\r"
        )
        files_tsv = {"file": ("staff.tsv", tsv_crlf.encode("utf-8"), "text/tab-separated-values")}
        res_tsv = await client.post("/api/admin/staff/pending/import-csv", files=files_tsv)
        assert res_tsv.status_code == 200
        assert res_tsv.json()["created"] == 2

        # 7. Import raw copy-paste text endpoint
        raw_text = (
            "Amir\tManat\tDPA-2602\t261434\t+77071708043\tamir.manat7x.z@gmail.com\t@Amirkahz\t SMM\n"
            "Shyngys\tAbildin\tBDA-2605\t260033\t+77770015743\tabildin.shyngys17@gmail.com\t@mak_vimper\tCommentator\n"
        )
        res_text = await client.post("/api/admin/staff/pending/import-text", json={"raw_text": raw_text})
        assert res_text.status_code == 200
        assert res_text.json()["created"] == 2

    app.dependency_overrides.clear()
    await engine.dispose()
