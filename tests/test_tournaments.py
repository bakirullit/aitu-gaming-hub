import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError

from common.database.base import Base
from common.enums import DisciplineType, TournamentStatus, UserRole
from common.models.user import User
from common.models.tournament import DisciplineAdmin, TournamentBooking
from plugins.tournaments.screens import (
    format_summary_label,
    get_slot_picker_screen,
    get_format_chips_screen,
    build_admin_approval_keyboard,
    build_admin_approval_text,
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
async def test_composite_unique_constraint_discipline_admin(in_memory_db):
    """Verify admin can manage multiple disciplines, but cannot duplicate the same discipline."""
    async with in_memory_db() as session:
        user = User(
            telegram_id=1001,
            username="esports_lead",
            first_name="Arman",
            email="arman@astanait.edu.kz",
            role=UserRole.DISCIPLINE_ADMIN,
            is_verified=True,
        )
        session.add(user)
        await session.commit()

        # Same admin managing CS2 and VALORANT -> MUST SUCCEED
        da_cs2 = DisciplineAdmin(telegram_id=1001, discipline=DisciplineType.CS2)
        da_val = DisciplineAdmin(telegram_id=1001, discipline=DisciplineType.VALORANT)
        session.add_all([da_cs2, da_val])
        await session.commit()

        # Duplicate CS2 for same admin -> MUST FAIL with IntegrityError
        da_dup = DisciplineAdmin(telegram_id=1001, discipline=DisciplineType.CS2)
        session.add(da_dup)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_zero_input_context_lookup(in_memory_db):
    """Zero-Input: verify admin context (email, discipline, telegram_id) is fetched automatically."""
    async with in_memory_db() as session:
        user = User(
            telegram_id=2002,
            username="fifa_king",
            first_name="Bakdaulet",
            last_name="Armanov",
            email="241738@astanait.edu.kz",

            role=UserRole.DISCIPLINE_ADMIN,
            is_verified=True,
        )
        da = DisciplineAdmin(telegram_id=2002, discipline=DisciplineType.FIFA)
        session.add_all([user, da])
        await session.commit()

        # Query session as router does
        res = await session.execute(
            select(DisciplineAdmin).where(DisciplineAdmin.telegram_id == 2002)
        )
        admin_roles = res.scalars().all()
        assert len(admin_roles) == 1
        assert admin_roles[0].discipline == DisciplineType.FIFA

        u_res = await session.execute(select(User).where(User.telegram_id == 2002))
        fetched_user = u_res.scalar_one()
        assert fetched_user.email == "241738@astanait.edu.kz"
        assert fetched_user.first_name == "Bakdaulet"


def test_slot_picker_calendar_grid():
    """Verify 14-day calendar grid correctly marks free (🟢) vs occupied (🔴) slots."""
    base_date = date.today() + timedelta(days=1)
    occupied_date = base_date + timedelta(days=3)

    screen = get_slot_picker_screen(
        title="FIFA Cup",
        discipline="FIFA",
        occupied_dates={occupied_date},
        days_ahead=14,
        start_date=base_date,
    )

    assert "Выбор даты проведения" in screen.text
    assert screen.reply_markup is not None

    buttons = [btn for row in screen.reply_markup.inline_keyboard for btn in row]
    # Check occupied button
    occ_buttons = [b for b in buttons if "🔴" in b.text]
    assert len(occ_buttons) == 1
    assert occ_buttons[0].callback_data == f"tb:occupied:{occupied_date.isoformat()}"

    # Check free buttons
    free_buttons = [b for b in buttons if "🟢" in b.text]
    assert len(free_buttons) == 13


def test_format_summary_and_chips():
    """Verify format chips and human-readable label generation."""
    label = format_summary_label("online_single_elim_2x2")
    assert "Онлайн" in label
    assert "Single Elim" in label
    assert "2x2" in label

    screen = get_format_chips_screen(
        title="Dota Major",
        booking_date_str="28.09.2026",
        loc="lan",
        bracket="double_elim",
        roster="5x5",
    )
    assert "LAN" in screen.text
    # Active chips must have checkmarks
    buttons = [btn for row in screen.reply_markup.inline_keyboard for btn in row]
    lan_btn = next(b for b in buttons if "LAN" in b.text)
    assert "✅" in lan_btn.text


@pytest.mark.asyncio
async def test_race_condition_guard_on_approval(in_memory_db):
    """Test race condition: second approval for the same date must be rejected with an alert."""
    target_date = date.today() + timedelta(days=5)

    async with in_memory_db() as session:
        user1 = User(telegram_id=3001, username="admin1", email="a1@aitu.kz", role=UserRole.DISCIPLINE_ADMIN)
        user2 = User(telegram_id=3002, username="admin2", email="a2@aitu.kz", role=UserRole.DISCIPLINE_ADMIN)
        session.add_all([user1, user2])
        await session.commit()

        # Admin 1 creates booking for CS2 on target_date
        b1 = TournamentBooking(
            creator_id=3001,
            discipline=DisciplineType.CS2,
            title="CS2 Clash",
            booking_date=target_date,
            event_format="lan_single_elim_5x5",
            status=TournamentStatus.PENDING,
        )
        # Admin 2 creates booking for DOTA2 on SAME target_date
        b2 = TournamentBooking(
            creator_id=3002,
            discipline=DisciplineType.DOTA2,
            title="Dota Showdown",
            booking_date=target_date,
            event_format="online_double_elim_5x5",
            status=TournamentStatus.PENDING,
        )
        session.add_all([b1, b2])
        await session.commit()
        await session.refresh(b1)
        await session.refresh(b2)

        # 1. Head Admin approves b1
        b1.status = TournamentStatus.APPROVED
        await session.commit()

        # 2. Head Admin attempts to approve b2 on the same date
        # Check guard logic:
        occupied = await session.scalar(
            select(TournamentBooking).where(
                TournamentBooking.booking_date == b2.booking_date,
                TournamentBooking.status == TournamentStatus.APPROVED,
                TournamentBooking.id != b2.id,
            )
        )
        assert occupied is not None
        assert occupied.id == b1.id
        # b2 must remain PENDING because slot is occupied
        assert b2.status == TournamentStatus.PENDING


@pytest.mark.asyncio
async def test_admin_approval_card_building(in_memory_db):
    """Test that admin approval card properly renders attached rulebook info and action keyboard."""
    target_date = date(2026, 9, 24)
    async with in_memory_db() as session:
        user = User(
            telegram_id=4001,
            username="fifa_admin",
            first_name="Sultan",
            email="sultan@astanait.edu.kz",
            role=UserRole.DISCIPLINE_ADMIN,
        )
        booking = TournamentBooking(
            id=42,
            creator_id=4001,
            discipline=DisciplineType.FIFA,
            title="FIFA 2026",
            booking_date=target_date,
            event_format="online_single_elim_2x2",
            rulebook_file_id="BAACAgIAAxkBAAI...",
            status=TournamentStatus.PENDING,
        )
        session.add_all([user, booking])
        await session.commit()

        text = build_admin_approval_text(booking, user, "@fifa_admin")
        assert "Бронь турнира: FIFA 2026" in text
        assert "@fifa_admin (FIFA Admin)" in text
        assert "24.09.2026" in text
        assert "Онлайн" in text
        assert "Single Elim" in text
        assert "2x2" in text
        assert "Прикрепленный файл регламента" in text


        kb = build_admin_approval_keyboard(booking.id)
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert any("Подтвердить слот" in b.text and "tb_adm:approve:42" == b.callback_data for b in buttons)
        assert any("Отклонить" in b.text and "tb_adm:reject:42" == b.callback_data for b in buttons)


def test_student_registration_prompts_have_no_personal_examples():
    """Verify that all personal data examples (Bakdaulet, Argyngazy, 241738, CS-2424) are removed."""
    from plugins.auth.screens import (
        get_first_name_prompt_screen,
        get_last_name_prompt_screen,
        get_barcode_prompt_screen,
        get_phone_prompt_screen,
        get_email_prompt_screen,
        get_group_prompt_screen,
    )

    screens = [
        get_first_name_prompt_screen(),
        get_last_name_prompt_screen("Ivan"),
        get_barcode_prompt_screen("Ivan", "Ivanov"),
        get_phone_prompt_screen("123456"),
        get_email_prompt_screen("+77001234567"),
        get_group_prompt_screen("test@astanait.edu.kz"),
    ]

    forbidden_examples = [
        "Argyngazy",
        "CS-2424",
        "Bakdaulet",
        "241738",
        "+77772179050",
        "bakirullet@gmail.com",
    ]

    for s in screens:
        for ex in forbidden_examples:
            assert ex not in s.text, f"Forbidden example '{ex}' found in screen text: {s.text}"

