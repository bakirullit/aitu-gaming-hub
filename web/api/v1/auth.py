from typing import Any
from fastapi import APIRouter, Depends, status

from schemas.user import (
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
from web.api.dependencies import (
    get_auth_service,
    get_steam_service,
    get_user_service,
)

v1_auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth V1"])


@v1_auth_router.get(
    "/check-user/{telegram_id}",
    response_model=CheckUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Fast user existence check for bot /start handler",
)
async def check_user(
    telegram_id: int,
    user_service: UserService = Depends(get_user_service),
) -> CheckUserResponse:
    """
    Checks if a user exists by their Telegram ID.
    Used by thin-client bot handlers to route new vs returning users.
    """
    user = await user_service.get_by_telegram_id(telegram_id)
    if user is None:
        return CheckUserResponse(exists=False, user=None)
    return CheckUserResponse(
        exists=True,
        user=UserResponse.model_validate(user),
    )


@v1_auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user profile",
)
async def register(
    payload: UserCreate,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Create a new user profile (guest, student, etc.).
    Validates uniqueness of telegram_id and gmail.
    """
    user = await user_service.register_user(payload)
    return UserResponse.model_validate(user)


@v1_auth_router.post(
    "/student/request-otp",
    status_code=status.HTTP_200_OK,
    summary="Request OTP verification code for student email",
)
async def request_student_otp(
    payload: StudentVerifyRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """
    Initiate student academic verification:
    - Checks 60s rate limit on Telegram ID.
    - Validates barcode uniqueness.
    - Generates 6-digit OTP cached in Redis for 5 minutes.
    - Dispatches verification email to {barcode}@astanait.edu.kz.
    """
    await auth_service.send_student_otp(
        telegram_id=payload.telegram_id,
        barcode=payload.barcode,
    )
    return {
        "status": "ok",
        "message": f"Verification code sent to {payload.barcode}@astanait.edu.kz",
        "barcode": payload.barcode,
    }


@v1_auth_router.post(
    "/student/confirm-otp",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm student OTP and promote account",
)
async def confirm_student_otp(
    payload: OTPConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Validate student OTP:
    - Checks remaining verification attempts (max 3).
    - Compares OTP against Redis state.
    - Promotes user to student role and links student barcode.
    """
    await auth_service.verify_student_otp(
        telegram_id=payload.telegram_id,
        barcode=payload.barcode,
        otp_code=payload.otp_code,
    )
    user = await user_service.promote_to_student(
        telegram_id=payload.telegram_id,
        barcode=payload.barcode,
    )
    return UserResponse.model_validate(user)


@v1_auth_router.post(
    "/steam/link",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Link Steam profile to user account",
)
async def link_steam(
    payload: SteamLinkRequest,
    steam_service: SteamService = Depends(get_steam_service),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Extracts and resolves SteamID64, checks uniqueness, and attaches to user profile.
    Elevates guest users to verified_guest.
    """
    steam_id = await steam_service.validate_and_extract_steam_id(payload.steam_payload)
    user = await user_service.attach_steam(
        telegram_id=payload.telegram_id,
        steam_id=steam_id,
    )
    return UserResponse.model_validate(user)
