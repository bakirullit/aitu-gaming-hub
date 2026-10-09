import json
import pytest
from common.texts import get_text, load_texts, reload_texts
from plugins.auth.screens import (
    get_club_info_screen,
    get_choose_role_screen,
    get_staff_closed_screen,
    get_full_name_screen,
    get_phone_screen,
    get_authorized_menu_screen,
    get_profile_screen,
    get_delete_account_confirm_screen,
    get_account_deleted_screen,
)
from plugins.helpdesk.screens import (
    get_helpdesk_home_screen,
    get_ticket_subject_prompt_screen,
)
from plugins.disciplines.screens import get_disciplines_catalog_screen
from plugins.minecraft.screens import get_minecraft_home_screen
from plugins.tournaments.screens import get_access_denied_screen


def test_load_texts():
    texts = load_texts()
    assert isinstance(texts, dict)
    assert "auth" in texts
    assert "helpdesk" in texts
    assert "disciplines" in texts
    assert "minecraft" in texts
    assert "tournaments" in texts


def test_get_text_basic():
    title = get_text("auth.club_info.buttons.start_reg")
    assert title == "📝 Пройти регистрацию"


def test_get_text_formatting():
    msg = get_text("auth.phone.text", full_name="Нурсултан Назарбаев")
    assert "Нурсултан Назарбаев" in msg
    assert "ФИО:" in msg


def test_get_text_fallback():
    res = get_text("non.existent.key", default="Default Value")
    assert res == "Default Value"

    res_no_default = get_text("another.non.existent.key")
    assert res_no_default == "[another.non.existent.key]"


def test_get_text_safe_formatting_errors():
    # If placeholder is missing or mismatched, it should safely handle
    raw = get_text("auth.phone.text")
    assert "{full_name}" in raw or "ФИО:" in raw


def test_screens_render_with_texts():
    # Auth screens
    club = get_club_info_screen()
    assert "AITU Gaming Hub" in club.text

    role = get_choose_role_screen()
    assert "Выберите ваш статус" in role.text

    staff = get_staff_closed_screen()
    assert "Регистрация Staff закрыта" in staff.text

    menu = get_authorized_menu_screen(full_name="Тест Игрок", role="student", is_verified=True)
    assert "Тест Игрок" in menu.text
    assert "Студент AITU 🎓" in menu.text

    profile = get_profile_screen({
        "full_name": "Тест Студент",
        "username": "student_test",
        "role": "student",
        "steam_id": "76561198000000000",
    })
    assert "Тест Студент" in profile.text
    assert "76561198000000000" in profile.text

    confirm = get_delete_account_confirm_screen(steam_id="76561198000000000")
    assert "76561198000000000" in confirm.text

    del_screen = get_account_deleted_screen(steam_id="76561198000000000")
    assert "76561198000000000" in del_screen.text

    # Helpdesk
    hd = get_helpdesk_home_screen(open_tickets_count=2)
    assert "2" in hd.text

    # Disciplines
    disc = get_disciplines_catalog_screen([], page=1)
    assert "Каталог дисциплин" in disc.text

    # Minecraft
    mc = get_minecraft_home_screen(linked_nick="Player1")
    assert "Player1" in mc.text

    # Tournaments
    td = get_access_denied_screen()
    assert "Доступ ограничен" in td.text
