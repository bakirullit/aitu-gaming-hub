import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from common.database.base import Base
from common.models.user import User
from common.models.minecraft import (
    MinecraftWhitelist,
    MinecraftSession,
    MinecraftFriendship,
    MinecraftFriendRequest,
)
from common.config import settings
from plugins.minecraft.screens import (
    get_minecraft_home_screen,
    get_minecraft_servers_screen,
    get_minecraft_profile_screen,
    get_minecraft_code_screen,
    get_minecraft_friends_hub_screen,
    get_minecraft_friends_list_screen,
    get_minecraft_friend_requests_screen,
    get_minecraft_channel_screen,
    get_nickname_prompt_screen,
    get_minecraft_add_friend_prompt_screen,
)
from plugins.disciplines.minecraft import MinecraftProfileSG, ChangeMinecraftNick


@pytest.fixture
async def in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


def test_minecraft_home_screen_navigation():
    """Verify Minecraft home screen has the exact requested 5 inline buttons."""
    screen = get_minecraft_home_screen(linked_nick="Steve", online=15, max_players=50)
    assert "Steve" in screen.text
    assert "15 / 50" in screen.text

    kb = screen.reply_markup
    assert isinstance(kb, InlineKeyboardMarkup)
    buttons = [b for row in kb.inline_keyboard for b in row]

    callbacks = [b.callback_data for b in buttons if b.callback_data]
    assert "cb_mc_servers" in callbacks
    assert "cb_mc_profile" in callbacks
    assert "cb_mc_friends" in callbacks
    assert "cb_mc_channel" in callbacks
    assert "nav:disciplines" in callbacks


def test_minecraft_servers_screen():
    """Verify servers screen displays details and required action buttons."""
    screen = get_minecraft_servers_screen(
        server_name="AITU SMP",
        version="Create 1.21.1 NeoForge",
        online=14,
        max_players=50,
        address="mc.aitu.edu.kz",
        motd="Welcome!",
        modpack_url="https://example.com/modpack",
    )
    assert "AITU SMP" in screen.text
    assert "Create 1.21.1 NeoForge" in screen.text
    assert "14 / 50" in screen.text
    assert "mc.aitu.edu.kz" in screen.text

    buttons = [b for row in screen.reply_markup.inline_keyboard for b in row]
    copy_ip_btn = next((b for b in buttons if b.callback_data == "mc:copy_ip"), None)
    assert copy_ip_btn is not None
    assert "Скопировать IP" in copy_ip_btn.text

    download_btn = next((b for b in buttons if b.url == "https://example.com/modpack"), None)
    assert download_btn is not None
    assert "Скачать модпак" in download_btn.text

    refresh_btn = next((b for b in buttons if b.callback_data == "cb_mc_servers"), None)
    assert refresh_btn is not None

    back_btn = next((b for b in buttons if b.callback_data == "nav:minecraft"), None)
    assert back_btn is not None


def test_minecraft_profile_screen():
    """Verify player profile card displays link status, nickname, tg id, and actions."""
    # 1. Unlinked profile
    unlinked_screen = get_minecraft_profile_screen(
        nickname=None,
        username="steve_tg",
        telegram_id=12345,
        has_active_session=False,
    )
    assert "Не привязан" in unlinked_screen.text
    assert "Не установлен" in unlinked_screen.text
    assert "12345" in unlinked_screen.text
    assert "Не активен" in unlinked_screen.text

    # 2. Linked profile with active session
    linked_screen = get_minecraft_profile_screen(
        nickname="SteveCraft",
        username="steve_tg",
        telegram_id=12345,
        has_active_session=True,
    )
    assert "Привязан" in linked_screen.text
    assert "SteveCraft" in linked_screen.text
    assert "Активная сессия" in linked_screen.text

    buttons = [b for row in linked_screen.reply_markup.inline_keyboard for b in row]
    callbacks = [b.callback_data for b in buttons if b.callback_data]
    assert "mc:change_nick" in callbacks
    assert "mc:gen_code" in callbacks
    assert "mc:unlink" in callbacks
    assert "nav:minecraft" in callbacks


def test_minecraft_code_screen():
    """Verify generated code screen contains PIN, nickname and back button."""
    screen = get_minecraft_code_screen(pin="123456", nickname="SteveCraft")
    assert "123456" in screen.text
    assert "SteveCraft" in screen.text
    assert "5 минут" in screen.text

    buttons = [b for row in screen.reply_markup.inline_keyboard for b in row]
    assert any(b.callback_data == "cb_mc_profile" for b in buttons)


def test_minecraft_friends_screens():
    """Verify friends hub, list and request screen layouts."""
    # Hub screen
    hub = get_minecraft_friends_hub_screen(total_friends=3, online_friends=1, pending_requests_count=2)
    assert "3" in hub.text
    assert "1" in hub.text
    assert "2" in hub.text
    hub_buttons = [b for row in hub.reply_markup.inline_keyboard for b in row]
    assert any(b.callback_data == "mc:friends_list" for b in hub_buttons)
    assert any(b.callback_data == "mc:add_friend" for b in hub_buttons)
    assert any("Заявки (2)" in b.text for b in hub_buttons)

    # Friends list screen
    friends = [
        {"nickname": "Alex", "telegram_tag": "@alex", "is_online": True},
        {"nickname": "Bob", "telegram_tag": "@bob", "is_online": False},
    ]
    list_screen = get_minecraft_friends_list_screen(friends=friends, page=1)
    assert "Alex" in list_screen.text
    assert "@alex" in list_screen.text
    assert "В сети" in list_screen.text
    assert "Bob" in list_screen.text

    # Friend requests screen
    requests = [
        {"id": 42, "from_nickname": "Charlie", "from_tag": "@charlie"},
    ]
    req_screen = get_minecraft_friend_requests_screen(requests=requests)
    assert "Charlie" in req_screen.text
    req_buttons = [b for row in req_screen.reply_markup.inline_keyboard for b in row]
    assert any(b.callback_data == "mc:accept_req:42" for b in req_buttons)
    assert any(b.callback_data == "mc:decline_req:42" for b in req_buttons)


def test_minecraft_channel_screen():
    """Verify channel screen has URLs for official channel and player chat."""
    screen = get_minecraft_channel_screen(
        channel_url="https://t.me/aitu_minecraft",
        chat_url="https://t.me/aitu_minecraft_chat",
    )
    buttons = [b for row in screen.reply_markup.inline_keyboard for b in row]
    assert any(b.url == "https://t.me/aitu_minecraft" for b in buttons)
    assert any(b.url == "https://t.me/aitu_minecraft_chat" for b in buttons)
    assert any(b.callback_data == "nav:minecraft" for b in buttons)


def test_fsm_states_conformance():
    """Verify MinecraftProfileSG and ChangeMinecraftNick states group conformance."""
    assert hasattr(MinecraftProfileSG, "waiting_for_nickname")
    assert hasattr(MinecraftProfileSG, "waiting_for_friend_tag")
    assert ChangeMinecraftNick == MinecraftProfileSG.waiting_for_nickname
