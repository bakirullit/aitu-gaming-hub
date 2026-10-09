import pytest
from common.enums import StaffRole, STAFF_ROLE_TITLES, UserRole
from common.models.user import User
from plugins.auth.screens import get_authorized_menu_screen, get_profile_screen


def test_user_roles_methods():
    # 1. Guest user
    guest = User(telegram_id=1, role="guest", roles=[])
    assert not guest.is_staff
    assert not guest.is_discipline_admin
    assert guest.has_role("guest")
    assert not guest.has_role("discipline_admin")

    # 2. Staff user with multiple sub-roles
    staff_member = User(
        telegram_id=2,
        role="staff",
        roles=["discipline_admin", "commentater", "streamer"],
    )
    assert staff_member.is_staff
    assert staff_member.is_discipline_admin
    assert staff_member.has_role("discipline_admin")
    assert staff_member.has_role("commentater")
    assert staff_member.has_role("streamer")
    assert not staff_member.has_role("president")

    titles = staff_member.get_staff_roles_display()
    assert "Discipline Admin ⚔️" in titles
    assert "Commentator 🎙️" in titles
    assert "Streamer 🎥" in titles

    # 3. Head admin user has administrative and discipline_admin privileges
    head_admin = User(
        telegram_id=3,
        role="head_admin",
        roles=["president"],
    )
    assert head_admin.is_staff
    assert head_admin.is_discipline_admin
    assert head_admin.has_role("head_admin")
    assert head_admin.has_role("discipline_admin")
    assert head_admin.has_role("president")


def test_menu_layout_by_role():
    # 1. Guest: only disciplines, profile, helpdesk (NO tournaments, NO minecraft)
    guest_menu = get_authorized_menu_screen(
        full_name="Guest User",
        role="guest",
        is_verified=False,
    )
    guest_buttons = [b.text for row in guest_menu.reply_markup.inline_keyboard for b in row]
    assert any("Каталог дисциплин" in t for t in guest_buttons)
    assert any("Мой профиль" in t for t in guest_buttons)
    assert any("Служба поддержки" in t for t in guest_buttons)
    assert not any("Бронирование турниров" in t or "Турниры и киберспорт" in t for t in guest_buttons)
    assert not any("Minecraft" in t for t in guest_buttons)

    # 2. Student: disciplines, minecraft, profile, helpdesk (NO tournament booking!)
    student_menu = get_authorized_menu_screen(
        full_name="Student User",
        role="student",
        is_verified=True,
    )
    student_buttons = [b.text for row in student_menu.reply_markup.inline_keyboard for b in row]
    assert any("Minecraft" in t for t in student_buttons)
    assert not any("Бронирование турниров" in t for t in student_buttons)

    # 3. Staff non-discipline_admin (e.g. SMM or Manager): no tournament booking!
    smm_menu = get_authorized_menu_screen(
        full_name="SMM Specialist",
        role="staff",
        roles=["smm"],
        is_staff=True,
        is_discipline_admin=False,
    )
    smm_buttons = [b.text for row in smm_menu.reply_markup.inline_keyboard for b in row]
    assert "Staff (SMM 📱) 🛡️" in smm_menu.text
    assert any("Minecraft" in t for t in smm_buttons)
    assert not any("Бронирование турниров" in t for t in smm_buttons)

    # 4. Discipline Admin: HAS tournament booking button!
    disc_admin_menu = get_authorized_menu_screen(
        full_name="CS2 Admin",
        role="staff",
        roles=["discipline_admin"],
        is_staff=True,
        is_discipline_admin=True,
    )
    disc_admin_buttons = [b.text for row in disc_admin_menu.reply_markup.inline_keyboard for b in row]
    assert "Discipline Admin" in disc_admin_menu.text
    assert any("Бронирование турниров" in t for t in disc_admin_buttons)


def test_profile_displays_multiple_staff_roles():
    profile = get_profile_screen({
        "full_name": "Multi Role Staff",
        "username": "multi_staff",
        "role": "staff",
        "roles": ["discipline_admin", "commentater", "streamer"],
        "steam_id": "76561198000000000",
    })
    assert "Discipline Admin ⚔️" in profile.text
    assert "Commentator 🎙️" in profile.text
    assert "Streamer 🎥" in profile.text
    assert "Staff AITU Gaming" in profile.text

    # Also test correct spelling commentator
    profile_corr = get_profile_screen({
        "full_name": "Multi Role Staff",
        "username": "multi_staff",
        "role": "staff",
        "roles": ["commentator"],
    })
    assert "Commentator 🎙️" in profile_corr.text


def test_auth_subrouters_decomposition():
    from unittest.mock import MagicMock
    from plugins.auth.router import setup_auth_routes, AuthStates
    from plugins.auth.rbac import get_user_home_screen, build_user_profile_data
    from plugins.auth.routers import setup_menu_router, setup_onboarding_router, setup_profile_router

    mock_core = MagicMock()
    mock_core.navigator = MagicMock()
    mock_core.settings = MagicMock()

    auth_root = setup_auth_routes(mock_core)
    assert len(auth_root.sub_routers) == 3

    # Check states
    assert hasattr(AuthStates, "choose_role")
    assert hasattr(AuthStates, "waiting_full_name")
    assert hasattr(AuthStates, "waiting_otp")

    # Check rbac screen builder
    guest_screen = get_user_home_screen(None)
    assert "AITU Gaming Hub" in guest_screen.text

    profile_dict = build_user_profile_data(None, fallback_from_user=MagicMock(first_name="Test", last_name="User", username="testuser"))
    assert profile_dict["first_name"] == "Test"
    assert profile_dict["username"] == "testuser"
