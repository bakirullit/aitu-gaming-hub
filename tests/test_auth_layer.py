import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from fastapi import HTTPException

from common.database.base import Base
from common.models.user import User
from common.config import Settings
from schemas.user import (
    UserRole,
    UserBase,
    UserCreate,
    UserResponse,
    CheckUserResponse,
    StudentVerifyRequest,
    OTPConfirmRequest,
    SteamLinkRequest,
)
from services.auth_service import AuthService
from services.steam_service import SteamService
from services.user_service import UserService
from web.api.dependencies import get_db_session, get_redis
from main import app


class MockRedis:
    def __init__(self):
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str):
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.data[key] = str(value)
        if ex is not None:
            self.ttls[key] = ex

    async def delete(self, *keys: str):
        count = 0
        for k in keys:
            if k in self.data:
                del self.data[k]
                self.ttls.pop(k, None)
                count += 1
        return count

    async def exists(self, key: str):
        return 1 if key in self.data else 0

    async def ttl(self, key: str):
        if key not in self.data:
            return -2
        return self.ttls.get(key, 60)

    async def incr(self, key: str):
        val = int(self.data.get(key, 0)) + 1
        self.data[key] = str(val)
        return val

    async def expire(self, key: str, seconds: int):
        if key in self.data:
            self.ttls[key] = seconds
            return 1
        return 0


# ============================================================================
# 1. Tests for Pydantic Schemas Validation
# ============================================================================

def test_user_role_enum():
    assert UserRole.guest.value == "guest"
    assert UserRole.verified_guest.value == "verified_guest"
    assert UserRole.student.value == "student"
    assert UserRole.staff.value == "staff"
    assert UserRole.admin.value == "admin"


def test_user_base_validation_success():
    payload = {
        "telegram_id": 111222333,
        "username": "gamer_aitu",
        "full_name": "  Алихан   Болатов  ",
        "phone_number": "+7 (701) 123-45-67",
        "gmail": "alikhan.bolatov@gmail.com",
    }
    user = UserBase(**payload)
    assert user.full_name == "Алихан Болатов"
    assert user.phone_number == "+77011234567"
    assert user.gmail == "alikhan.bolatov@gmail.com"


def test_user_base_full_name_validation_failures():
    # Only 1 word
    with pytest.raises(ValidationError):
        UserBase(
            telegram_id=1,
            full_name="SingleName",
            phone_number="+77011234567",
            gmail="test@gmail.com",
        )
    # Digits in name
    with pytest.raises(ValidationError):
        UserBase(
            telegram_id=1,
            full_name="John Doe123",
            phone_number="+77011234567",
            gmail="test@gmail.com",
        )


def test_user_base_phone_validation_failures():
    # Missing plus
    with pytest.raises(ValidationError):
        UserBase(
            telegram_id=1,
            full_name="John Doe",
            phone_number="87011234567",
            gmail="test@gmail.com",
        )
    # Too short
    with pytest.raises(ValidationError):
        UserBase(
            telegram_id=1,
            full_name="John Doe",
            phone_number="+123",
            gmail="test@gmail.com",
        )


def test_user_base_gmail_validation_failures():
    # Non-gmail domain
    with pytest.raises(ValidationError):
        UserBase(
            telegram_id=1,
            full_name="John Doe",
            phone_number="+77011234567",
            gmail="user@astanait.edu.kz",
        )
    # Subdomain spoofing
    with pytest.raises(ValidationError):
        UserBase(
            telegram_id=1,
            full_name="John Doe",
            phone_number="+77011234567",
            gmail="user@gmail.com.phishing.org",
        )


def test_user_create_defaults():
    user = UserCreate(
        telegram_id=999,
        full_name="Jane Doe",
        phone_number="+77019876543",
        gmail="jane@gmail.com",
    )
    assert user.role == UserRole.guest
    assert user.student_barcode is None
    assert user.steam_id is None


def test_student_verify_request_validation():
    req = StudentVerifyRequest(telegram_id=10, barcode="  230101  ")
    assert req.barcode == "230101"

    # Not 6 digits
    with pytest.raises(ValidationError):
        StudentVerifyRequest(telegram_id=10, barcode="12345")
    with pytest.raises(ValidationError):
        StudentVerifyRequest(telegram_id=10, barcode="1234567")
    with pytest.raises(ValidationError):
        StudentVerifyRequest(telegram_id=10, barcode="abcdef")


def test_otp_confirm_request_validation():
    req = OTPConfirmRequest(telegram_id=10, barcode="230101", otp_code="123456")
    assert req.otp_code == "123456"

    # Invalid OTP code format
    with pytest.raises(ValidationError):
        OTPConfirmRequest(telegram_id=10, barcode="230101", otp_code="12345")
    with pytest.raises(ValidationError):
        OTPConfirmRequest(telegram_id=10, barcode="230101", otp_code="12a456")


def test_steam_link_request_validation():
    req = SteamLinkRequest(telegram_id=10, steam_payload="76561198012345678")
    assert req.steam_payload == "76561198012345678"

    with pytest.raises(ValidationError):
        SteamLinkRequest(telegram_id=10, steam_payload="   ")


# ============================================================================
# 2. Tests for AuthService
# ============================================================================

@pytest.fixture
async def in_mem_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_auth_service_send_otp_success(in_mem_db_session):
    mock_redis = MockRedis()
    custom_settings = Settings(
        RESEND_API_KEY="re_test_dummy_key",
        SENDER_EMAIL="onboarding@resend.dev",
    )
    auth_service = AuthService(
        session=in_mem_db_session,
        redis=mock_redis,
        settings_obj=custom_settings,
    )

    with patch("resend.Emails.send_async", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"id": "email_123"}
        await auth_service.send_student_otp(telegram_id=1001, barcode="230101")

        # Verify rate limit key
        assert await mock_redis.get("rate:otp:1001") == "1"
        assert mock_redis.ttls.get("rate:otp:1001") == 60

        # Verify OTP key stored with 300s TTL
        saved_otp = await mock_redis.get("otp:230101")
        assert saved_otp is not None
        assert len(saved_otp) == 6
        assert saved_otp.isdigit()
        assert mock_redis.ttls.get("otp:230101") == 300

        # Verify email dispatched
        mock_send.assert_awaited_once()
        call_params = mock_send.call_args[0][0]
        assert call_params["to"] == ["230101@astanait.edu.kz"]
        assert saved_otp in call_params["subject"]


@pytest.mark.asyncio
async def test_auth_service_rate_limiting(in_mem_db_session):
    mock_redis = MockRedis()
    custom_settings = Settings(RESEND_API_KEY="")
    auth_service = AuthService(session=in_mem_db_session, redis=mock_redis, settings_obj=custom_settings)

    await auth_service.send_student_otp(telegram_id=1002, barcode="230102")

    # Immediate second request should trigger 429
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.send_student_otp(telegram_id=1002, barcode="230102")

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_auth_service_barcode_conflict(in_mem_db_session):
    # Seed an existing user with barcode 230103
    existing = User(
        telegram_id=5555,
        username="existing_student",
        full_name="Already Here",
        email="existing@gmail.com",
        barcode="230103",
        role=UserRole.student.value,
        is_verified=True,
    )
    in_mem_db_session.add(existing)
    await in_mem_db_session.commit()

    mock_redis = MockRedis()
    auth_service = AuthService(session=in_mem_db_session, redis=mock_redis)

    # Different user attempts to request OTP for this barcode
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.send_student_otp(telegram_id=9999, barcode="230103")

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_auth_service_verify_otp_flow(in_mem_db_session):
    mock_redis = MockRedis()
    auth_service = AuthService(session=in_mem_db_session, redis=mock_redis)

    # Set up active OTP
    await mock_redis.set("otp:230104", "654321", ex=300)

    # 1. Invalid attempt 1
    with pytest.raises(HTTPException) as exc1:
        await auth_service.verify_student_otp(1004, "230104", "000000")
    assert exc1.value.status_code == 400
    assert "2 attempt(s) remaining" in exc1.value.detail

    # 2. Invalid attempt 2
    with pytest.raises(HTTPException) as exc2:
        await auth_service.verify_student_otp(1004, "230104", "000001")
    assert exc2.value.status_code == 400
    assert "1 attempt(s) remaining" in exc2.value.detail

    # 3. Invalid attempt 3 -> Burns code and blocks with 403
    with pytest.raises(HTTPException) as exc3:
        await auth_service.verify_student_otp(1004, "230104", "000002")
    assert exc3.value.status_code == 403
    assert await mock_redis.get("otp:230104") is None  # Burned!

    # 4. New OTP setup and successful verification
    await mock_redis.set("otp:230104", "112233", ex=300)
    await mock_redis.delete("attempts:otp:230104")

    res = await auth_service.verify_student_otp(1004, "230104", "112233")
    assert res is True
    assert await mock_redis.get("otp:230104") is None
    assert await mock_redis.get("attempts:otp:230104") is None


# ============================================================================
# 3. Tests for SteamService
# ============================================================================

@pytest.mark.asyncio
async def test_steam_service_raw_steamid64():
    service = SteamService()
    raw = "76561198012345678"
    assert await service.validate_and_extract_steam_id(raw) == raw


@pytest.mark.asyncio
async def test_steam_service_profiles_url():
    service = SteamService()
    url = "https://steamcommunity.com/profiles/76561198012345678/"
    assert await service.validate_and_extract_steam_id(url) == "76561198012345678"

    rel_url = "/profiles/76561198012345678"
    assert await service.validate_and_extract_steam_id(rel_url) == "76561198012345678"


@pytest.mark.asyncio
async def test_steam_service_vanity_url_with_api_key():
    import httpx
    settings_with_key = Settings(STEAM_API_KEY="fake_steam_key")
    service = SteamService(settings_obj=settings_with_key)

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json={
                "response": {
                    "steamid": "76561198999999999",
                    "success": 1,
                }
            },
        )

        res = await service.validate_and_extract_steam_id("https://steamcommunity.com/id/gabelog")
        assert res == "76561198999999999"


@pytest.mark.asyncio
async def test_steam_service_vanity_url_without_api_key():
    settings_no_key = Settings(STEAM_API_KEY="")
    service = SteamService(settings_obj=settings_no_key)

    res = await service.validate_and_extract_steam_id("https://steamcommunity.com/id/gabelog")
    assert res == "gabelog"


@pytest.mark.asyncio
async def test_steam_service_invalid_payload():
    service = SteamService()
    with pytest.raises(HTTPException) as exc:
        await service.validate_and_extract_steam_id("https://youtube.com/watch")
    assert exc.value.status_code == 400


# ============================================================================
# 4. Tests for UserService
# ============================================================================

@pytest.mark.asyncio
async def test_user_service_registration_and_uniqueness(in_mem_db_session):
    service = UserService(session=in_mem_db_session)

    # 1. Successful register
    dto = UserCreate(
        telegram_id=2001,
        username="player1",
        full_name="Арман Сейтов",
        phone_number="+77051112233",
        gmail="arman@gmail.com",
    )
    user = await service.register_user(dto)
    assert user.telegram_id == 2001
    assert user.role == "guest"
    assert user.email == "arman@gmail.com"
    assert user.first_name == "Арман"
    assert user.last_name == "Сейтов"

    # 2. Duplicate telegram_id -> 409
    with pytest.raises(HTTPException) as exc_tg:
        await service.register_user(dto)
    assert exc_tg.value.status_code == 409

    # 3. Duplicate email -> 409
    dto2 = UserCreate(
        telegram_id=2002,
        username="player2",
        full_name="Бауыржан Момышулы",
        phone_number="+77052223344",
        gmail="arman@gmail.com",  # Same email
    )
    with pytest.raises(HTTPException) as exc_email:
        await service.register_user(dto2)
    assert exc_email.value.status_code == 409


@pytest.mark.asyncio
async def test_user_service_promote_to_student(in_mem_db_session):
    service = UserService(session=in_mem_db_session)
    dto = UserCreate(
        telegram_id=2003,
        full_name="Данияр Касым",
        phone_number="+77053334455",
        gmail="daniyar@gmail.com",
    )
    user = await service.register_user(dto)
    assert user.role == "guest"

    promoted = await service.promote_to_student(2003, "230999")
    assert promoted.role == "student"
    assert promoted.barcode == "230999"
    assert promoted.student_barcode == "230999"
    assert promoted.is_verified is True


@pytest.mark.asyncio
async def test_user_service_attach_steam(in_mem_db_session):
    service = UserService(session=in_mem_db_session)
    dto = UserCreate(
        telegram_id=2004,
        full_name="Ерлан Каримов",
        phone_number="+77054445566",
        gmail="yerlan@gmail.com",
    )
    user = await service.register_user(dto)
    assert user.role == "guest"

    # Attaching steam promotes guest to verified_guest
    updated = await service.attach_steam(2004, "76561198012345678")
    assert updated.steam_id == "76561198012345678"
    assert updated.role == "verified_guest"


# ============================================================================
# 5. Full REST API Endpoints Integration Tests (/api/v1/auth/*)
# ============================================================================

@pytest.fixture
async def api_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    test_redis = MockRedis()

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    async def override_get_redis():
        yield test_redis

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_factory, test_redis

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_e2e_auth_workflow(api_client):
    client, session_factory, mock_redis = api_client

    # 1. GET /check-user/{telegram_id} -> not exists
    res = await client.get("/api/v1/auth/check-user/3001")
    assert res.status_code == 200
    data = res.json()
    assert data["exists"] is False
    assert data["user"] is None

    # 2. POST /register -> register new guest
    reg_payload = {
        "telegram_id": 3001,
        "username": "aitu_champ",
        "full_name": "Мурат Нурланов",
        "phone_number": "+77071234567",
        "gmail": "murat.nurlanov@gmail.com",
    }
    res_reg = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res_reg.status_code == 201
    user_data = res_reg.json()
    assert user_data["telegram_id"] == 3001
    assert user_data["role"] == "guest"
    assert user_data["full_name"] == "Мурат Нурланов"

    # Verify check-user now returns exists = True
    res_check = await client.get("/api/v1/auth/check-user/3001")
    assert res_check.status_code == 200
    assert res_check.json()["exists"] is True

    # 3. POST /student/request-otp
    with patch("resend.Emails.send_async", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = {"id": "resend_e2e"}
        otp_req = {"telegram_id": 3001, "barcode": "230888"}
        res_otp = await client.post("/api/v1/auth/student/request-otp", json=otp_req)
        assert res_otp.status_code == 200
        assert res_otp.json()["status"] == "ok"

    # Read generated OTP from mock redis
    generated_otp = await mock_redis.get("otp:230888")
    assert generated_otp is not None

    # 4. POST /student/confirm-otp with bad code
    bad_confirm = {
        "telegram_id": 3001,
        "barcode": "230888",
        "otp_code": "000000" if generated_otp != "000000" else "111111",
    }
    res_bad = await client.post("/api/v1/auth/student/confirm-otp", json=bad_confirm)
    assert res_bad.status_code == 400

    # 5. POST /student/confirm-otp with correct code
    good_confirm = {
        "telegram_id": 3001,
        "barcode": "230888",
        "otp_code": generated_otp,
    }
    res_good = await client.post("/api/v1/auth/student/confirm-otp", json=good_confirm)
    assert res_good.status_code == 200
    updated_user = res_good.json()
    assert updated_user["role"] == "student"
    assert updated_user["student_barcode"] == "230888"
    assert updated_user["is_verified"] is True

    # 6. POST /steam/link
    steam_req = {
        "telegram_id": 3001,
        "steam_payload": "https://steamcommunity.com/profiles/76561198012345678",
    }
    res_steam = await client.post("/api/v1/auth/steam/link", json=steam_req)
    assert res_steam.status_code == 200
    steam_user = res_steam.json()
    assert steam_user["steam_id"] == "76561198012345678"
    # Role remains student since student role is higher than verified_guest
    assert steam_user["role"] == "student"


@pytest.mark.asyncio
async def test_e2e_guest_steam_promotion(api_client):
    client, _, _ = api_client

    # Register guest
    reg_payload = {
        "telegram_id": 4001,
        "full_name": "Кайрат Нуртас",
        "phone_number": "+77079998877",
        "gmail": "kairat@gmail.com",
    }
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    assert res.json()["role"] == "guest"

    # Link steam promotes guest to verified_guest
    steam_req = {
        "telegram_id": 4001,
        "steam_payload": "76561198099887766",
    }
    res_steam = await client.post("/api/v1/auth/steam/link", json=steam_req)
    assert res_steam.status_code == 200
    assert res_steam.json()["role"] == "verified_guest"
    assert res_steam.json()["steam_id"] == "76561198099887766"
