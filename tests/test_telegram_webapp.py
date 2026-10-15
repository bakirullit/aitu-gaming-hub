import hashlib
import hmac
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from common.database.base import Base
from common.enums import UserRole
from common.models.user import User
from common.utils.telegram_auth import validate_telegram_init_data
from plugins.auth.screens import get_club_info_screen, get_authorized_menu_screen


def build_test_init_data(user_dict: dict, bot_token: str, auth_date: int | None = None) -> str:
    """Helper to generate cryptographically valid initData for unit tests."""
    if auth_date is None:
        auth_date = int(time.time())
    
    user_json = json.dumps(user_dict, separators=(',', ':'))
    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHd9xwAAAAAAN33HHXy5z",
        "user": user_json,
    }
    
    data_check_list = [f"{k}={params[k]}" for k in sorted(params.keys())]
    data_check_string = "\n".join(data_check_list)
    
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    
    # URL encoded query string
    from urllib.parse import urlencode
    params_with_hash = {**params, "hash": calc_hash}
    return urlencode(params_with_hash)


@pytest.fixture
async def in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


def test_telegram_init_data_validation():
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    user_payload = {"id": 99912345, "first_name": "Arman", "username": "arman_kz"}
    
    # 1. Valid signature
    valid_init_data = build_test_init_data(user_payload, bot_token)
    res = validate_telegram_init_data(valid_init_data, bot_token)
    assert res["user"]["id"] == 99912345
    assert res["user"]["first_name"] == "Arman"
    assert res["user"]["username"] == "arman_kz"
    
    # 2. Tampered signature (wrong bot token)
    with pytest.raises(ValueError, match="Invalid initData cryptographic signature"):
        validate_telegram_init_data(valid_init_data, "wrong_token_here")
        
    # 3. Missing hash
    with pytest.raises(ValueError, match="Missing 'hash'"):
        validate_telegram_init_data("user=abc&auth_date=123", bot_token)

    # 4. Expired auth_date
    expired_init_data = build_test_init_data(user_payload, bot_token, auth_date=int(time.time()) - 900000)
    with pytest.raises(ValueError, match="expired"):
        validate_telegram_init_data(expired_init_data, bot_token, max_age_seconds=3600)


@pytest.mark.asyncio
async def test_api_seamless_telegram_webapp_admin_login(in_memory_db):
    from httpx import AsyncClient, ASGITransport
    from main import app
    from common.config import settings
    from web.api.dependencies import get_db_session

    bot_token = settings.BOT_TOKEN
    admin_user = User(
        telegram_id=777001,
        username="lead_admin",
        first_name="Lead",
        role=UserRole.HEAD_ADMIN,
        is_verified=True,
    )

    async with in_memory_db() as session:
        session.add(admin_user)
        await session.commit()

    async def override_get_db_session():
        async with in_memory_db() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        init_data = build_test_init_data(
            {"id": 777001, "first_name": "Lead", "username": "lead_admin"},
            bot_token=bot_token
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/auth/telegram/webapp", json={"init_data": init_data})
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["is_admin"] is True
            assert data["user"]["telegram_id"] == 777001
            assert data["user"]["username"] == "lead_admin"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_seamless_telegram_webapp_new_guest_registration(in_memory_db):
    from httpx import AsyncClient, ASGITransport
    from main import app
    from common.config import settings
    from web.api.dependencies import get_db_session

    bot_token = settings.BOT_TOKEN

    async def override_get_db_session():
        async with in_memory_db() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        init_data = build_test_init_data(
            {"id": 888123, "first_name": "NewStudent", "last_name": "AITU", "username": "student_aitu"},
            bot_token=bot_token
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/auth/telegram/webapp", json={"init_data": init_data})
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["is_admin"] is False
            assert data["user"]["telegram_id"] == 888123
            assert data["user"]["first_name"] == "NewStudent"
            assert data["user"]["role"] == "guest"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_seamless_telegram_webapp_invalid_signature():
    from httpx import AsyncClient, ASGITransport
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/auth/telegram/webapp",
            json={"init_data": "auth_date=123&hash=invalid_hash_value&user=%7B%22id%22%3A1%7D"}
        )
        assert resp.status_code == 401


def test_telegram_screens_include_webapp_buttons():
    # 1. Club info screen for new visitors
    club_screen = get_club_info_screen()
    buttons = [btn for row in club_screen.reply_markup.inline_keyboard for btn in row]
    assert any(btn.web_app is not None and "Hub" in btn.text for btn in buttons)

    # 2. Authorized menu screen
    auth_screen = get_authorized_menu_screen(
        full_name="Almas Admin",
        role="head_admin",
        is_verified=True,
    )
    auth_buttons = [btn for row in auth_screen.reply_markup.inline_keyboard for btn in row]
    assert any(btn.web_app is not None and "Web" in btn.text for btn in auth_buttons)
