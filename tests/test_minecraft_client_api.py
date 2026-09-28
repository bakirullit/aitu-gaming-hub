import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.database.base import Base
from common.enums import UserRole
from common.models.minecraft import (
    MinecraftFriendRequest,
    MinecraftFriendship,
    MinecraftSession,
    MinecraftWhitelist,
)
from common.models.user import User
from core.lifespan import runtime
from main import app
from web.api.dependencies import get_db_session


@pytest.fixture
async def mc_db_setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Populate test users
    async with session_factory() as session:
        user1 = User(
            telegram_id=123456789,
            username="steve_aitu",
            first_name="Steve",
            last_name="Miner",
            email="steve@aitu.edu.kz",
            barcode="10001",
            role=UserRole.STUDENT,
            is_verified=True,
        )
        user2 = User(
            telegram_id=987654321,
            username="alex_aitu",
            first_name="Alex",
            last_name="Crafter",
            email="alex@aitu.edu.kz",
            barcode="10002",
            role=UserRole.STUDENT,
            is_verified=True,
        )
        session.add_all([user1, user2])
        await session.commit()

    yield session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_route_matching_and_slashing(mc_db_setup):
    """Test that endpoints respond with 200 both with and without trailing slash."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # GET /api/server/info vs /api/server/info/
        res1 = await ac.get("/api/server/info")
        assert res1.status_code == 200

        res2 = await ac.get("/api/server/info/")
        assert res2.status_code == 200

        # GET /api/friends/list vs /api/friends/list/
        res3 = await ac.get("/api/friends/list")
        assert res3.status_code == 200

        res4 = await ac.get("/api/friends/list/")
        assert res4.status_code == 200


@pytest.mark.asyncio
async def test_server_info_endpoint():
    """Verify server info returns valid network and status details."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/server/info")

    assert response.status_code == 200
    data = response.json()
    assert "ip" in data
    assert "name" in data
    assert "online" in data
    assert "max_players" in data
    assert "motd" in data
    assert data["ip"] == "mc.aitu-gaming.y-not-devs.com:25565"
    assert data["max_players"] == 50


@pytest.mark.asyncio
async def test_auth_request_code_user_not_found(mc_db_setup):
    """Verify 404 is returned when telegram username does not exist."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/request-code",
            json={
                "telegram_tag": "@non_existent_user",
                "minecraft_nickname": "Steve",
            },
        )

    assert response.status_code == 404
    data = response.json()
    assert "User not registered in @aitu_gaming_bot. Please start the bot first." in data["detail"]


@pytest.mark.asyncio
async def test_auth_full_flow(mc_db_setup):
    """Verify request-code -> PIN stored in cache -> verify -> session created."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Request Code
        req_res = await ac.post(
            "/api/auth/request-code",
            json={
                "telegram_tag": "@steve_aitu",
                "minecraft_nickname": "SteveCraft",
            },
        )
        assert req_res.status_code == 200
        req_data = req_res.json()
        assert req_data["status"] == "code_sent"
        assert req_data["message"] == "Verification code sent to Telegram"

        # Check PIN cached in Redis / fallback
        from web.api.minecraft import _cache_get
        import json
        cached_str = await _cache_get("auth:pin:steve_aitu")
        assert cached_str is not None
        cached_data = json.loads(cached_str)
        pin = cached_data["pin"]
        assert len(pin) == 6
        assert pin.isdigit()

        # 2. Verify with wrong code
        bad_res = await ac.post(
            "/api/auth/verify",
            json={
                "telegram_tag": "@steve_aitu",
                "code": "000000",
                "minecraft_nickname": "SteveCraft",
            },
        )
        assert bad_res.status_code == 400
        assert "Invalid or expired code" in bad_res.json()["detail"]

        # 3. Verify with correct code
        good_res = await ac.post(
            "/api/auth/verify",
            json={
                "telegram_tag": "steve_aitu",
                "code": pin,
                "minecraft_nickname": "SteveCraft",
            },
        )
        assert good_res.status_code == 200
        verify_data = good_res.json()
        assert verify_data["status"] == "success"
        assert verify_data["telegram_id"] == 123456789
        assert verify_data["username"] == "steve_aitu"
        session_token = verify_data["session_token"]
        assert session_token

        # 4. Verify replay is prevented (PIN deleted)
        replay_res = await ac.post(
            "/api/auth/verify",
            json={
                "telegram_tag": "steve_aitu",
                "code": pin,
                "minecraft_nickname": "SteveCraft",
            },
        )
        assert replay_res.status_code == 400


@pytest.mark.asyncio
async def test_friends_endpoints_unauthenticated():
    """Verify friends endpoints provide mock/foundation data when unauthenticated."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # GET /api/friends/list
        list_res = await ac.get("/api/friends/list")
        assert list_res.status_code == 200
        friends_data = list_res.json()
        assert "friends" in friends_data
        assert len(friends_data["friends"]) == 1
        assert friends_data["friends"][0]["nickname"] == "Student123"
        assert friends_data["friends"][0]["telegram_tag"] == "@student"

        # GET /api/friends/requests
        reqs_res = await ac.get("/api/friends/requests")
        assert reqs_res.status_code == 200
        assert reqs_res.json() == {"requests": []}

        # POST /api/friends/request
        post_req_res = await ac.post("/api/friends/request", json={"query": "@someone"})
        assert post_req_res.status_code == 200
        assert post_req_res.json() == {"status": "request_sent"}

        # POST /api/friends/accept
        accept_res = await ac.post("/api/friends/accept", json={"request_id": 1})
        assert accept_res.status_code == 200
        assert accept_res.json() == {"status": "accepted"}

        # POST /api/friends/decline
        decline_res = await ac.post("/api/friends/decline", json={"target_tag": "@someone"})
        assert decline_res.status_code == 200
        assert decline_res.json() == {"status": "declined"}


@pytest.mark.asyncio
async def test_friends_flow_authenticated(mc_db_setup):
    """Verify friends request, accept, and list with authenticated session."""
    session_factory = mc_db_setup

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Authenticate user 1 (steve_aitu)
        await ac.post(
            "/api/auth/request-code",
            json={"telegram_tag": "@steve_aitu", "minecraft_nickname": "SteveCraft"},
        )
        from web.api.minecraft import _cache_get
        import json
        pin1 = json.loads(await _cache_get("auth:pin:steve_aitu"))["pin"]
        v1 = await ac.post(
            "/api/auth/verify",
            json={"telegram_tag": "steve_aitu", "code": pin1, "minecraft_nickname": "SteveCraft"},
        )
        token1 = v1.json()["session_token"]

        # Authenticate user 2 (alex_aitu)
        await ac.post(
            "/api/auth/request-code",
            json={"telegram_tag": "@alex_aitu", "minecraft_nickname": "AlexPro"},
        )
        pin2 = json.loads(await _cache_get("auth:pin:alex_aitu"))["pin"]
        v2 = await ac.post(
            "/api/auth/verify",
            json={"telegram_tag": "alex_aitu", "code": pin2, "minecraft_nickname": "AlexPro"},
        )
        token2 = v2.json()["session_token"]

        # User 1 sends friend request to User 2 (@alex_aitu)
        req_res = await ac.post(
            "/api/friends/request",
            json={"query": "@alex_aitu"},
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert req_res.status_code == 200
        assert req_res.json() == {"status": "request_sent"}

        # User 2 checks requests
        incoming_res = await ac.get(
            "/api/friends/requests",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert incoming_res.status_code == 200
        req_list = incoming_res.json()["requests"]
        assert len(req_list) == 1
        req_id = req_list[0]["request_id"]
        assert req_list[0]["from_nickname"] == "SteveCraft"

        # User 2 accepts request
        acc_res = await ac.post(
            "/api/friends/accept",
            json={"request_id": req_id},
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert acc_res.status_code == 200
        assert acc_res.json() == {"status": "accepted"}

        # User 1 lists friends
        u1_friends = await ac.get(
            "/api/friends/list",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert u1_friends.status_code == 200
        friends1 = u1_friends.json()["friends"]
        assert len(friends1) == 1
        assert friends1[0]["nickname"] == "AlexPro"
        assert friends1[0]["telegram_tag"] == "@alex_aitu"
