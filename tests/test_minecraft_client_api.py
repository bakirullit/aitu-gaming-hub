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

    # Populate test users (simulating users registered and whitelisted via Telegram bot)
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
            minecraft_nickname="SteveCraft",
        )
        wl1 = MinecraftWhitelist(
            user_id=123456789,
            nickname="SteveCraft",
            is_active=True,
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
            minecraft_nickname="AlexPro",
        )
        wl2 = MinecraftWhitelist(
            user_id=987654321,
            nickname="AlexPro",
            is_active=True,
        )
        session.add_all([user1, wl1, user2, wl2])
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
async def test_auth_java_client_payload_flow(mc_db_setup):
    """Verify authentication using Java Mod Client payload format (pin, tag, mc_nick)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Step 1: request code
        req_res = await ac.post(
            "/api/auth/request-code",
            json={
                "telegram_tag": "@alex_aitu",
                "minecraft_nickname": "AlexMiner",
            },
        )
        assert req_res.status_code == 200

        from web.api.minecraft import _cache_get
        import json
        cached_str = await _cache_get("auth:pin:alex_aitu")
        cached_data = json.loads(cached_str)
        pin = cached_data["pin"]

        # Step 2: verify using exact Java client fields
        verify_res = await ac.post(
            "/api/auth/verify",
            json={
                "telegram_tag": "@alex_aitu",
                "tag": "@alex_aitu",
                "pin": pin,
                "minecraft_nickname": "AlexMiner",
                "mc_nick": "AlexMiner",
            },
        )
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert data["status"] == "success"
        assert data["session_token"]
        assert data["token"] == data["session_token"]
        assert data["telegram_tag"] == "@alex_aitu"
        assert data["tag"] == "@alex_aitu"


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


@pytest.mark.asyncio
async def test_auth_otp_message_lifecycle(mc_db_setup):
    """Verify that OTP message is tracked, deleted immediately on submission, and can delete on timeout."""
    import json
    from unittest.mock import AsyncMock, MagicMock
    from core.lifespan import runtime
    from web.api.minecraft import _cache_get, _delete_mc_otp_message_delayed

    mock_bot = MagicMock()
    mock_sent_msg = MagicMock()
    mock_sent_msg.message_id = 998877
    mock_bot.send_message = AsyncMock(return_value=mock_sent_msg)
    mock_bot.delete_message = AsyncMock()

    original_bot = runtime.bot
    runtime.bot = mock_bot
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Request code
            res = await ac.post(
                "/api/auth/request-code",
                json={"telegram_tag": "@steve_aitu", "minecraft_nickname": "SteveCraft"},
            )
            assert res.status_code == 200
            assert mock_bot.send_message.called
            sent_args = mock_bot.send_message.call_args[1]
            assert "Valid for 3 minutes" in sent_args["text"]

            # Check cached message id
            cached_msg_id = await _cache_get("auth:pin:msg:steve_aitu")
            assert cached_msg_id == "998877"

            cached_pin_data = json.loads(await _cache_get("auth:pin:steve_aitu"))
            pin = cached_pin_data["pin"]
            assert cached_pin_data["message_id"] == 998877

            # 2. Verify with correct code -> message must be deleted immediately
            verify_res = await ac.post(
                "/api/auth/verify",
                json={"telegram_tag": "@steve_aitu", "code": pin, "minecraft_nickname": "SteveCraft"},
            )
            assert verify_res.status_code == 200
            mock_bot.delete_message.assert_called_with(chat_id=123456789, message_id=998877)

            # Both keys must be cleared
            assert await _cache_get("auth:pin:steve_aitu") is None
            assert await _cache_get("auth:pin:msg:steve_aitu") is None

            # 3. Test delayed deletion helper if PIN is still in cache
            mock_bot.delete_message.reset_mock()
            from web.api.minecraft import _cache_set
            await _cache_set("auth:pin:timeout_user", json.dumps({"pin": "123456"}), ex=180)
            await _cache_set("auth:pin:msg:timeout_user", "554433", ex=180)

            # Run helper with 0s sleep to test timeout branch
            from unittest.mock import patch
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await _delete_mc_otp_message_delayed(
                    chat_id=123456789,
                    message_id=554433,
                    pin_key="auth:pin:timeout_user",
                    msg_key="auth:pin:msg:timeout_user",
                )

            mock_bot.delete_message.assert_called_with(chat_id=123456789, message_id=554433)
            assert await _cache_get("auth:pin:timeout_user") is None
            assert await _cache_get("auth:pin:msg:timeout_user") is None
    finally:
        runtime.bot = original_bot


@pytest.mark.asyncio
async def test_server_verify_token_endpoint(mc_db_setup):
    """Test POST /api/server/verify-token with valid, whitelisted, and invalid tokens."""
    session_factory = mc_db_setup

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Test missing token
        empty_res = await ac.post("/api/server/verify-token", json={})
        assert empty_res.status_code == 200
        assert empty_res.json()["valid"] is False
        assert "Session token is required" in empty_res.json()["error"]

        # 2. Test invalid token
        invalid_res = await ac.post("/api/server/verify-token", json={"token": "invalid_fake_token"})
        assert invalid_res.status_code == 200
        assert invalid_res.json()["valid"] is False
        assert "Invalid or expired session token" in invalid_res.json()["error"]

        # 3. Create a valid session for @steve_aitu
        await ac.post(
            "/api/auth/request-code",
            json={"telegram_tag": "@steve_aitu", "minecraft_nickname": "SteveCraft"},
        )
        from web.api.minecraft import _cache_get
        import json
        pin = json.loads(await _cache_get("auth:pin:steve_aitu"))["pin"]
        v_res = await ac.post(
            "/api/auth/verify",
            json={"telegram_tag": "@steve_aitu", "code": pin, "minecraft_nickname": "SteveCraft"},
        )
        valid_token = v_res.json()["session_token"]

        # 4. Verify via JSON body
        verify_body_res = await ac.post("/api/server/verify-token", json={"token": valid_token})
        assert verify_body_res.status_code == 200
        data = verify_body_res.json()
        assert data["valid"] is True
        assert data["telegram_id"] == 123456789
        assert data["telegram_tag"] == "@steve_aitu"
        assert data["minecraft_nickname"] == "SteveCraft"
        assert data["is_whitelisted"] is True

        # 5. Verify via Bearer authorization header
        verify_header_res = await ac.post(
            "/api/server/verify-token",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert verify_header_res.status_code == 200
        assert verify_header_res.json()["valid"] is True
        assert verify_header_res.json()["telegram_id"] == 123456789



@pytest.mark.asyncio
async def test_minecraft_nickname_regression_on_session_reissuance(mc_db_setup):
    """
    Regression test:
    When a player logs out and logs in again using Telegram PIN verification,
    their in-game nickname must retain their persistent database nickname (e.g. Bakirullit),
    even if the client launcher submits a different launcher username or empty nickname.
    """
    session_factory = mc_db_setup
    from sqlalchemy import select
    from web.api.minecraft import _cache_get
    import json

    # 1. Setup persistent user in DB with nickname "Bakirullit"
    async with session_factory() as session:
        bak_user = User(
            telegram_id=2100991409,
            username="ALGORITHMs",
            first_name="Bakir",
            last_name="Ullit",
            email="bakir@aitu.edu.kz",
            barcode="10003",
            role=UserRole.STUDENT,
            is_verified=True,
            minecraft_nickname="Bakirullit",
        )
        session.add(bak_user)
        wl_entry = MinecraftWhitelist(
            user_id=2100991409,
            nickname="Bakirullit",
            is_active=True,
        )
        session.add(wl_entry)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 2. Player logs in from client launcher, where launcher sends username "LauncherNick"
        req_res = await ac.post(
            "/api/auth/request-code",
            json={"telegram_tag": "@ALGORITHMs", "minecraft_nickname": "LauncherNick"},
        )
        assert req_res.status_code == 200

        pin_data = json.loads(await _cache_get("auth:pin:algorithms"))
        pin = pin_data["pin"]

        # 3. Client calls /api/auth/verify with PIN and launcher username "LauncherNick"
        verify_res = await ac.post(
            "/api/auth/verify",
            json={
                "telegram_tag": "@ALGORITHMs",
                "tag": "@ALGORITHMs",
                "pin": pin,
                "code": pin,
                "minecraft_nickname": "LauncherNick",
                "mc_nick": "LauncherNick",
            },
        )
        assert verify_res.status_code == 200
        verify_json = verify_res.json()
        assert verify_json["status"] == "success"
        session_token = verify_json["session_token"]
        assert session_token
        # DB nickname MUST take precedence over launcher payload
        assert verify_json.get("minecraft_nickname") == "Bakirullit"

        # 4. Validate token via /api/server/verify-token
        srv_res = await ac.post(
            "/api/server/verify-token",
            json={"token": session_token, "launcher_nickname": "LauncherNick"},
        )
        assert srv_res.status_code == 200
        srv_data = srv_res.json()
        assert srv_data["valid"] is True
        assert srv_data["telegram_id"] == 2100991409
        assert srv_data["telegram_tag"] == "@ALGORITHMs"
        assert srv_data["minecraft_nickname"] == "Bakirullit"
        assert srv_data["is_whitelisted"] is True
        assert srv_data["role"] in ["student", "STUDENT", "player"]

        # 5. Validate token via /api/auth/validate-token (alternative endpoint used by server mod)
        val_res = await ac.post(
            "/api/auth/validate-token",
            json={"session_token": session_token},
            headers={"Authorization": f"Bearer {session_token}"},
        )
        assert val_res.status_code == 200
        val_data = val_res.json()
        assert val_data["valid"] is True
        assert val_data["telegram_id"] == 2100991409
        assert val_data["minecraft_nickname"] == "Bakirullit"
        assert val_data["is_whitelisted"] is True

    # 6. Verify Database consistency: check that whitelist & user retain "Bakirullit"
    async with session_factory() as session:
        u_res = await session.execute(select(User).where(User.telegram_id == 2100991409))
        u = u_res.scalar_one()
        assert u.minecraft_nickname == "Bakirullit"

        wl_res = await session.execute(select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == 2100991409))
        wl = wl_res.scalar_one()
        assert wl.nickname == "Bakirullit"

        sess_res = await session.execute(select(MinecraftSession).where(MinecraftSession.session_token == session_token))
        sess = sess_res.scalar_one()
        assert sess.minecraft_nickname == "Bakirullit"


@pytest.mark.asyncio
async def test_whitelist_only_persistent_nick_precedence(mc_db_setup):
    """
    When a player previously had their nickname in minecraft_whitelist but user.minecraft_nickname was null,
    logging in again must adopt the whitelist nickname and sync it across tables.
    """
    session_factory = mc_db_setup
    from sqlalchemy import select
    from web.api.minecraft import _cache_get
    import json

    async with session_factory() as session:
        user_wl = User(
            telegram_id=555666777,
            username="whitelisted_user",
            email="wl@aitu.edu.kz",
            barcode="10004",
            role=UserRole.STUDENT,
            is_verified=True,
            minecraft_nickname=None,  # null in user table
        )
        session.add(user_wl)
        wl = MinecraftWhitelist(
            user_id=555666777,
            nickname="PersistentWhitelistedNick",
            is_active=True,
        )
        session.add(wl)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post(
            "/api/auth/request-code",
            json={"telegram_tag": "@whitelisted_user", "minecraft_nickname": "RandomLauncherNick"},
        )
        pin = json.loads(await _cache_get("auth:pin:whitelisted_user"))["pin"]

        v_res = await ac.post(
            "/api/auth/verify",
            json={"telegram_tag": "@whitelisted_user", "code": pin, "minecraft_nickname": "RandomLauncherNick"},
        )
        assert v_res.status_code == 200
        token = v_res.json()["session_token"]
        assert v_res.json()["minecraft_nickname"] == "PersistentWhitelistedNick"

        # Verify token validation returns whitelist nickname
        val_res = await ac.post("/api/server/verify-token", json={"token": token})
        assert val_res.status_code == 200
        assert val_res.json()["minecraft_nickname"] == "PersistentWhitelistedNick"

    async with session_factory() as session:
        u_res = await session.execute(select(User).where(User.telegram_id == 555666777))
        u = u_res.scalar_one()
        # Database user is strictly readonly for launcher: remains untouched
        assert u.minecraft_nickname is None
        wl_res = await session.execute(select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == 555666777))
        assert wl_res.scalar_one().nickname == "PersistentWhitelistedNick"


@pytest.mark.asyncio
async def test_launcher_cannot_mutate_database_nickname(mc_db_setup):
    """
    Verify that the client launcher cannot mutate the database nickname in ANY way.
    Nickname is strictly read-only for the launcher and changed exclusively via the Telegram bot.
    """
    session_factory = mc_db_setup
    from sqlalchemy import select
    from web.api.minecraft import _cache_get
    import json

    # 1. Existing user with persistent nickname in DB
    async with session_factory() as session:
        bot_user = User(
            telegram_id=777888999,
            username="bot_player",
            first_name="Bot",
            last_name="Player",
            email="botplayer@aitu.edu.kz",
            barcode="10009",
            role=UserRole.STUDENT,
            is_verified=True,
            minecraft_nickname="BotConfiguredNick",
        )
        session.add(bot_user)
        wl = MinecraftWhitelist(
            user_id=777888999,
            nickname="BotConfiguredNick",
            is_active=True,
        )
        session.add(wl)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Launcher logs in sending a completely different launcher username
        await ac.post(
            "/api/auth/request-code",
            json={"telegram_tag": "@bot_player", "minecraft_nickname": "MaliciousLauncherNick"},
        )
        pin = json.loads(await _cache_get("auth:pin:bot_player"))["pin"]

        v_res = await ac.post(
            "/api/auth/verify",
            json={
                "telegram_tag": "@bot_player",
                "code": pin,
                "minecraft_nickname": "MaliciousLauncherNick",
            },
        )
        assert v_res.status_code == 200
        # Verify returned nickname is the bot-configured persistent nick
        assert v_res.json()["minecraft_nickname"] == "BotConfiguredNick"
        tok = v_res.json()["session_token"]

        # Token validation must return the bot-configured persistent nick
        val_res = await ac.post("/api/server/verify-token", json={"token": tok, "launcher_nickname": "MaliciousLauncherNick"})
        assert val_res.status_code == 200
        assert val_res.json()["minecraft_nickname"] == "BotConfiguredNick"

    # Verify database was NOT mutated: User and Whitelist still have BotConfiguredNick
    async with session_factory() as session:
        u = (await session.execute(select(User).where(User.telegram_id == 777888999))).scalar_one()
        assert u.minecraft_nickname == "BotConfiguredNick"
        w = (await session.execute(select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == 777888999))).scalar_one()
        assert w.nickname == "BotConfiguredNick"

    # 2. User without a persistent nickname in DB logs in via launcher
    async with session_factory() as session:
        no_nick_user = User(
            telegram_id=333444555,
            username="no_nick_player",
            email="nonick@aitu.edu.kz",
            barcode="10010",
            role=UserRole.STUDENT,
            is_verified=True,
            minecraft_nickname=None,
        )
        session.add(no_nick_user)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post(
            "/api/auth/request-code",
            json={"telegram_tag": "@no_nick_player", "minecraft_nickname": "LauncherAttempt"},
        )
        pin2 = json.loads(await _cache_get("auth:pin:no_nick_player"))["pin"]

        v_res2 = await ac.post(
            "/api/auth/verify",
            json={"telegram_tag": "@no_nick_player", "code": pin2, "minecraft_nickname": "LauncherAttempt"},
        )
        assert v_res2.status_code == 200
        tok2 = v_res2.json()["session_token"]

        # Server token validation shows NOT whitelisted because only the bot can whitelist / set nick
        srv_val = await ac.post("/api/server/verify-token", json={"token": tok2})
        assert srv_val.status_code == 200
        assert srv_val.json()["is_whitelisted"] is False

    # In database: User.minecraft_nickname is STILL None and NO MinecraftWhitelist entry was created
    async with session_factory() as session:
        u2 = (await session.execute(select(User).where(User.telegram_id == 333444555))).scalar_one()
        assert u2.minecraft_nickname is None
        w2 = (await session.execute(select(MinecraftWhitelist).where(MinecraftWhitelist.user_id == 333444555))).scalar_one_or_none()
        assert w2 is None
