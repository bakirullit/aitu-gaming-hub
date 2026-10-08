from typing import Any
import logging
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.models.user import User
from core.lifespan import runtime
from schemas.user import (
    UserCreate,
    UserResponse,
    CheckUserResponse,
    StudentVerifyRequest,
    OTPConfirmRequest,
    SteamLinkRequest,
)
from services.auth_service import AuthService
from services.steam_service import (
    SteamService,
    render_steam_bridge_html,
    render_steam_error_html,
    render_steam_success_html,
)
from services.user_service import UserService
from web.api.dependencies import (
    get_auth_service,
    get_db_session,
    get_redis,
    get_steam_service,
    get_user_service,
)

logger = logging.getLogger("web.api.v1.auth")

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
    recipient = await auth_service.send_student_otp(
        telegram_id=payload.telegram_id,
        barcode=payload.barcode,
        target_email=payload.email,
    )
    return {
        "status": "ok",
        "message": f"Verification code sent to {recipient}",
        "barcode": payload.barcode,
        "recipient": recipient,
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


@v1_auth_router.get(
    "/steam/login",
    summary="Initiate Steam OpenID 2.0 authentication redirect",
    response_class=RedirectResponse,
)
async def steam_openid_login(
    request: Request,
    state: str = Query(..., description="One-time session token from Telegram bot"),
    redis: Redis = Depends(get_redis),
    steam_service: SteamService = Depends(get_steam_service),
):
    """
    Validates state token in Redis and redirects client to Valve's official Steam OpenID 2.0 gateway.
    """
    key = f"{steam_service.STATE_PREFIX}{state.strip()}"
    exists = await redis.exists(key)
    if not exists:
        return HTMLResponse(
            content=render_steam_error_html(
                title="Сессия не найдена",
                message="Срок действия сессии истек или ссылка недействительна. Пожалуйста, вернитесь в Telegram-бот и запросите привязку заново.",
                bot_username=settings.BOT_USERNAME,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    base_url = (settings.WEBAPP_URL or str(request.base_url)).rstrip("/")
    login_url = steam_service.build_openid_login_url(state=state.strip(), base_url=base_url)
    return RedirectResponse(url=login_url, status_code=status.HTTP_302_FOUND)


@v1_auth_router.get(
    "/steam/callback",
    summary="Handle Steam OpenID 2.0 authentication callback",
    response_class=HTMLResponse,
)
async def steam_openid_callback(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    steam_service: SteamService = Depends(get_steam_service),
):
    """
    Validates Steam OpenID 2.0 response signature against Valve's gateway,
    extracts SteamID64, performs VAC/ban checks via Steam Web API,
    binds Steam account to Telegram user in DB, and notifies user via bot.
    """
    query_params = dict(request.query_params)
    mode = query_params.get("openid.mode")
    if mode == "cancel":
        return HTMLResponse(
            content=render_steam_error_html(
                title="Авторизация отменена",
                message="Вы отменили вход через Steam. Вы можете вернуться в Telegram-бот и повторить попытку в любое время.",
                bot_username=settings.BOT_USERNAME,
            ),
            status_code=status.HTTP_200_OK,
        )

    state = query_params.get("state")
    if not state:
        return HTMLResponse(
            content=render_steam_error_html(
                title="Ошибка авторизации",
                message="Параметр сессии (state) отсутствует в запросе. Пожалуйста, запросите привязку заново в Telegram-боте.",
                bot_username=settings.BOT_USERNAME,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 1. Atomically verify and consume single-use state from Redis
    state_data = await steam_service.verify_and_consume_state(state=state, redis=redis)
    if not state_data:
        return HTMLResponse(
            content=render_steam_error_html(
                title="Сессия устарела",
                message="Срок действия этой ссылки истек или она уже была использована. Вернитесь в Telegram-бот и нажмите «Привязать Steam» снова.",
                bot_username=settings.BOT_USERNAME,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    telegram_id = int(state_data["telegram_id"])
    extra_data = state_data.get("extra_data", {})

    # 2. Validate cryptographic signature with Valve OpenID gateway
    is_valid, steam_id = await steam_service.validate_openid_response(query_params=query_params)
    if not is_valid or not steam_id:
        await steam_service.set_login_status(
            state=state,
            redis=redis,
            status_val="failed",
            data={"reason": "Шлюз Steam отклонил цифровую подпись OpenID"},
        )
        return HTMLResponse(
            content=render_steam_error_html(
                title="Ошибка верификации подписи",
                message="Шлюз Steam отклонил подпись OpenID или claimed_id некорректен. Пожалуйста, попробуйте еще раз.",
                bot_username=settings.BOT_USERNAME,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Check SteamID uniqueness across other accounts
    stmt_existing = select(User).where(
        User.steam_id == steam_id,
        User.telegram_id != telegram_id,
    )
    existing_other = (await session.execute(stmt_existing)).scalar_one_or_none()
    if existing_other:
        await steam_service.set_login_status(
            state=state,
            redis=redis,
            status_val="failed",
            data={"reason": f"SteamID {steam_id} уже привязан к другому пользователю"},
        )
        if runtime.bot:
            try:
                await runtime.bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        f"❌ <b>Ошибка привязки Steam:</b>\n\n"
                        f"Steam-профиль (ID: <code>{steam_id}</code>) уже привязан к другому Telegram-аккаунту AITU Gaming Hub."
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

        return HTMLResponse(
            content=render_steam_error_html(
                title="Аккаунт уже привязан",
                message=f"SteamID <code>{steam_id}</code> уже используется другим пользователем AITU Gaming Hub.",
                bot_username=settings.BOT_USERNAME,
            ),
            status_code=status.HTTP_409_CONFLICT,
        )

    # 4. Query Steam Web API for persona name, avatar, and VAC bans
    player_summary = await steam_service.get_player_summaries(steam_id=steam_id)
    player_bans = await steam_service.get_player_bans(steam_id=steam_id)

    persona_name = (player_summary and player_summary.get("personaname")) or f"Steam_{steam_id[-6:]}"
    avatar_url = (player_summary and player_summary.get("avatarfull")) or None
    is_vac = bool(player_bans and player_bans.get("VACBanned"))
    is_community = bool(player_bans and player_bans.get("CommunityBanned"))

    # 5. Persist SteamID to User in PostgreSQL
    stmt_user = select(User).where(User.telegram_id == telegram_id)
    user = (await session.execute(stmt_user)).scalar_one_or_none()

    if user:
        user.steam_id = steam_id
        if user.role == "guest":
            user.role = "verified_guest"
    else:
        # Create user profile if completed during guest registration
        full_name = extra_data.get("full_name", "")
        parts = full_name.split(maxsplit=1) if full_name else []
        first_name = parts[0] if parts else "Гость"
        last_name = parts[1] if len(parts) > 1 else ""

        user = User(
            telegram_id=telegram_id,
            username=extra_data.get("username"),
            full_name=full_name or "Гость",
            first_name=first_name,
            last_name=last_name,
            phone_number=extra_data.get("phone"),
            email=extra_data.get("gmail"),
            steam_id=steam_id,
            role="verified_guest",
            is_verified=False,
        )
        session.add(user)

    await session.commit()
    await session.refresh(user)

    # 6. Update TMA polling status in Redis (completed)
    await steam_service.set_login_status(
        state=state,
        redis=redis,
        status_val="completed",
        data={
            "steam_id": steam_id,
            "personaname": persona_name,
            "avatar": avatar_url,
        },
    )

    # 7. Clear registration FSM state in Redis if present
    try:
        fsm_pattern = f"fsm:*:{telegram_id}:{telegram_id}:*"
        keys = await redis.keys(fsm_pattern)
        if keys:
            await redis.delete(*keys)
    except Exception:
        pass

    # 8. Notify user in Telegram DM and update their anchor screen
    ban_status_label = "✅ Чистый аккаунт (без банов)"
    if is_vac or is_community:
        bans_list = []
        if is_vac:
            bans_list.append("VAC-бан")
        if is_community:
            bans_list.append("Community-бан")
        ban_status_label = f"⚠️ Обнаружены блокировки ({', '.join(bans_list)})"

    if runtime.bot:
        try:
            await runtime.bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"🎮 <b>Steam-аккаунт успешно привязан!</b>\n\n"
                    f"• Никнейм: <b>{persona_name}</b>\n"
                    f"• SteamID64: <code>{steam_id}</code>\n"
                    f"• Статус: {ban_status_label}\n\n"
                    f"Ваш профиль верифицирован для участия в киберспортивных турнирах AITU Gaming Hub! 🏆"
                ),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning(f"Failed to send Telegram message to {telegram_id}: {exc}")

    if runtime.core and runtime.core.navigator:
        try:
            from plugins.auth.screens import get_authorized_menu_screen
            anchor_id = await runtime.core.navigator.get_anchor_id(telegram_id)
            if anchor_id:
                screen = get_authorized_menu_screen(
                    full_name=user.full_name or "Игрок",
                    role=user.role,
                    is_verified=user.is_verified,
                    has_steam=True,
                )
                await runtime.core.navigator.render(
                    user_id=telegram_id,
                    chat_id=telegram_id,
                    screen=screen,
                    screen_id="home",
                    push_to_history=False,
                )
        except Exception as exc:
            logger.debug(f"Failed to refresh navigator anchor: {exc}")

    # 9. Render sleek HTML response for browser
    html_content = render_steam_success_html(
        persona_name=persona_name,
        steam_id=steam_id,
        avatar_url=avatar_url,
        is_vac=is_vac,
        is_community=is_community,
        bot_username=settings.BOT_USERNAME,
    )
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


@v1_auth_router.get(
    "/steam/status",
    summary="Check status of Steam authentication for TMA polling",
)
async def steam_auth_status(
    state: str = Query(..., description="One-time session token"),
    redis: Redis = Depends(get_redis),
    steam_service: SteamService = Depends(get_steam_service),
):
    """
    Returns real-time status of the Steam OpenID session for Telegram Mini App polling.
    """
    status_data = await steam_service.get_login_status(state=state, redis=redis)
    if not status_data:
        return {"status": "expired"}
    return status_data


@v1_auth_router.get(
    "/steam/bridge",
    summary="Telegram Mini App pre-flight bridge for Steam OpenID",
    response_class=HTMLResponse,
)
async def steam_tma_bridge(
    request: Request,
    state: str = Query(..., description="One-time session token"),
    redis: Redis = Depends(get_redis),
    steam_service: SteamService = Depends(get_steam_service),
):
    """
    Renders Telegram Mini App bridge modal with SSL verification plaque,
    esports branding, and native openLink transition to Steam OpenID 2.0 gateway.
    """
    key = f"{steam_service.STATE_PREFIX}{state.strip()}"
    exists = await redis.exists(key)
    if not exists:
        return HTMLResponse(
            content=render_steam_error_html(
                title="Сессия не найдена",
                message="Срок действия сессии истек или ссылка недействительна. Пожалуйста, вернитесь в Telegram-бот и запросите привязку заново.",
                bot_username=settings.BOT_USERNAME,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    base_url = (settings.WEBAPP_URL or str(request.base_url)).rstrip("/")
    login_url = steam_service.build_login_url(state=state.strip(), base_url=base_url)
    status_url = f"{base_url}/api/v1/auth/steam/status?state={state.strip()}"

    html = render_steam_bridge_html(
        state=state.strip(),
        login_url=login_url,
        status_url=status_url,
        bot_username=settings.BOT_USERNAME,
    )
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)
