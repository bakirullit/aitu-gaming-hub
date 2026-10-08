import re
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from common.models.user import User
from core.context import CoreContext
from services.auth_service import AuthService
from services.steam_service import SteamService
from services.user_service import UserService
from plugins.auth.screens import (
    get_club_info_screen,
    get_choose_role_screen,
    get_staff_closed_screen,
    get_full_name_screen,
    get_phone_screen,
    get_phone_reply_keyboard,
    get_gmail_screen,
    get_barcode_screen,
    get_otp_screen,
    get_steam_screen,
    get_registration_cancelled_screen,
    get_authorized_menu_screen,
    get_profile_screen,
)

logger = logging.getLogger("plugins.auth.router")

router = Router(name="auth_router")


class AuthStates(StatesGroup):
    choose_role = State()
    waiting_full_name = State()
    waiting_phone = State()
    waiting_gmail = State()
    waiting_barcode = State()
    waiting_otp = State()
    waiting_steam = State()


def setup_auth_routes(core: CoreContext) -> Router:
    """Configures and binds core dependencies to the Auth router."""

    async def render_home(user_id: int, chat_id: int, payload: dict) -> any:
        async with core.db_session_factory() as session:
            stmt = select(User).where(User.telegram_id == user_id)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()

            if user and user.full_name:
                return get_authorized_menu_screen(
                    full_name=user.full_name,
                    role=user.role,
                    is_verified=user.is_verified,
                    has_steam=bool(user.steam_id),
                )
            return get_club_info_screen()

    core.navigator.register_screen_renderer("home", render_home)  # type: ignore

    async def _clean_contact_markup(chat_id: int, state: FSMContext) -> None:
        """Helper to remove reply keyboard if active."""
        data = await state.get_data()
        msg_id = data.get("phone_reply_msg_id")
        if msg_id:
            try:
                await core.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass
            await state.update_data(phone_reply_msg_id=None)

    # =========================================================================
    # /start handler
    # =========================================================================

    @router.message(CommandStart())
    async def cmd_start(
        message: Message,
        session: AsyncSession,
        state: FSMContext,
        command: CommandObject | None = None,
    ) -> None:
        await state.clear()
        user_id = message.from_user.id
        chat_id = message.chat.id

        # Clean old anchor if exists
        anchor_id = await core.navigator.get_anchor_id(user_id)
        if anchor_id:
            try:
                await core.bot.delete_message(chat_id, anchor_id)
            except Exception:
                pass
            await core.redis.delete(f"anchor:user:{user_id}:message_id")

        await core.navigator.reset_history(user_id)

        # Check user in DB
        stmt = select(User).where(User.telegram_id == user_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        # If user is already registered (has full_name)
        if user and user.full_name:
            screen = get_authorized_menu_screen(
                full_name=user.full_name,
                role=user.role,
                is_verified=user.is_verified,
                has_steam=bool(user.steam_id),
            )
            await core.navigator.render(
                user_id=user_id,
                chat_id=chat_id,
                screen=screen,
                screen_id="home",
                push_to_history=True,
            )
            return

        # New user: Show Club Info Screen
        screen = get_club_info_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="club_info",
            push_to_history=True,
        )

    # =========================================================================
    # /cancel handler
    # =========================================================================

    @router.message(Command("cancel"))
    async def cmd_cancel(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        await _clean_contact_markup(chat_id, state)
        await state.clear()

        screen = get_registration_cancelled_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="reg_cancelled",
            push_to_history=False,
        )

    @router.callback_query(F.data == "auth:cancel")
    async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        await _clean_contact_markup(chat_id, state)
        await state.clear()

        screen = get_registration_cancelled_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="reg_cancelled",
            push_to_history=False,
        )
        await callback.answer("Регистрация отменена")

    # =========================================================================
    # Step 1: Click "Пройти регистрацию" -> State: CHOOSE_ROLE
    # =========================================================================

    @router.callback_query(F.data.in_(["auth:start_reg", "auth:start"]))
    async def cb_start_registration(callback: CallbackQuery, state: FSMContext) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        await state.clear()
        await state.set_state(AuthStates.choose_role)

        screen = get_choose_role_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:choose_role",
            push_to_history=True,
        )
        await callback.answer()

    # Staff role chosen -> Registration closed
    @router.callback_query(F.data == "auth:role:staff")
    async def cb_role_staff(callback: CallbackQuery) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        screen = get_staff_closed_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:staff_closed",
            push_to_history=True,
        )
        await callback.answer()

    # Guest or Student chosen -> State: INPUT_FULL_NAME
    @router.callback_query(F.data.in_(["auth:role:guest", "auth:role:student"]))
    async def cb_choose_role(callback: CallbackQuery, state: FSMContext) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        selected_role = "student" if callback.data == "auth:role:student" else "guest"

        await state.update_data(role=selected_role)
        await state.set_state(AuthStates.waiting_full_name)

        screen = get_full_name_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:full_name",
            push_to_history=True,
        )
        await callback.answer()

    # =========================================================================
    # Step 2: State: INPUT_FULL_NAME -> State: INPUT_PHONE
    # =========================================================================

    @router.message(AuthStates.waiting_full_name)
    async def process_full_name(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        raw_text = (message.text or "").strip()

        words = raw_text.split()
        if len(words) < 2 or not all(w.isalpha() for w in words):
            screen = get_full_name_screen()
            err_screen = screen.__class__(
                text=(
                    "❌ <b>Некорректный формат ФИО!</b>\n\n"
                    "Пожалуйста, введите настоящие <b>Имя и Фамилию</b> (минимум 2 слова, только буквы):\n"
                    "<i>Пример: Алихан Болатов</i>"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=err_screen, push_to_history=False)
            return

        normalized_full_name = " ".join(words)
        await state.update_data(full_name=normalized_full_name)
        await state.set_state(AuthStates.waiting_phone)

        # Render phone prompt
        screen = get_phone_screen(normalized_full_name)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:phone",
            push_to_history=True,
        )

        # Send optional contact button
        try:
            contact_msg = await core.bot.send_message(
                chat_id=chat_id,
                text="📱 Вы можете быстро отправить номер нажатием кнопки ниже:",
                reply_markup=get_phone_reply_keyboard(),
            )
            await state.update_data(phone_reply_msg_id=contact_msg.message_id)
        except Exception:
            pass

    # =========================================================================
    # Step 3: State: INPUT_PHONE -> State: INPUT_GMAIL
    # =========================================================================

    @router.message(AuthStates.waiting_phone)
    async def process_phone(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        data = await state.get_data()
        full_name = data.get("full_name", "")

        # Extract phone
        if message.contact and message.contact.phone_number:
            raw_phone = message.contact.phone_number.strip()
            clean_phone = ("+" + raw_phone.lstrip("+")).strip()
        else:
            raw_phone = (message.text or "").strip()
            clean_phone = re.sub(r"[\s\-\(\)]", "", raw_phone)

        # Validate E.164
        if not re.match(r"^\+[1-9]\d{6,14}$", clean_phone):
            screen = get_phone_screen(full_name)
            err_screen = screen.__class__(
                text=(
                    f"❌ <b>Некорректный номер телефона!</b>\n\n"
                    f"ФИО: <b>{full_name}</b> ✅\n\n"
                    "Убедитесь, что номер указан в международном формате E.164 (например, <code>+77011234567</code>):"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=err_screen, push_to_history=False)
            return

        await _clean_contact_markup(chat_id, state)
        await state.update_data(phone=clean_phone)
        await state.set_state(AuthStates.waiting_gmail)

        screen = get_gmail_screen(full_name=full_name, phone=clean_phone)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:gmail",
            push_to_history=True,
        )

    # =========================================================================
    # Step 4: State: INPUT_GMAIL -> Route based on selected role
    # =========================================================================

    @router.message(AuthStates.waiting_gmail)
    async def process_gmail(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        data = await state.get_data()
        full_name = data.get("full_name", "")
        phone = data.get("phone", "")
        role = data.get("role", "guest")

        email_str = (message.text or "").strip().lower()

        # Strict @gmail.com validation
        if not re.fullmatch(r"^[a-zA-Z0-9_.+-]+@gmail\.com$", email_str):
            screen = get_gmail_screen(full_name=full_name, phone=phone)
            err_screen = screen.__class__(
                text=(
                    f"❌ <b>Некорректная почта Google!</b>\n\n"
                    f"ФИО: <b>{full_name}</b> ✅\n"
                    f"Телефон: <code>{phone}</code> ✅\n\n"
                    "Пожалуйста, введите личную почту Google (домен строго <code>@gmail.com</code>):\n"
                    "<i>Пример: student@gmail.com</i>"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=err_screen, push_to_history=False)
            return

        await state.update_data(gmail=email_str)

        # Check role branch
        if role == "student":
            await state.set_state(AuthStates.waiting_barcode)
            screen = get_barcode_screen(full_name=full_name)
            await core.navigator.render(
                user_id=user_id,
                chat_id=chat_id,
                screen=screen,
                screen_id="auth:barcode",
                push_to_history=True,
            )
        else:
            # Guest branch -> INPUT_STEAM via OpenID 2.0
            await state.set_state(AuthStates.waiting_steam)
            steam_service = SteamService(settings_obj=core.settings)
            login_state = await steam_service.create_login_state(
                telegram_id=user_id,
                redis=core.redis,
                extra_data=data,
            )
            steam_bridge_url = steam_service.build_bridge_url(login_state)
            screen = get_steam_screen(steam_auth_url=steam_bridge_url, is_registration=True, use_web_app=True)
            await core.navigator.render(
                user_id=user_id,
                chat_id=chat_id,
                screen=screen,
                screen_id="auth:steam",
                push_to_history=True,
            )

    # =========================================================================
    # Student branch: State: INPUT_BARCODE -> send OTP -> State: INPUT_OTP
    # =========================================================================

    @router.message(AuthStates.waiting_barcode)
    async def process_barcode(message: Message, state: FSMContext, session: AsyncSession) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        data = await state.get_data()
        full_name = data.get("full_name", "")
        barcode = (message.text or "").strip()

        # 6 digits validation
        if not (barcode.isdigit() and len(barcode) == 6):
            screen = get_barcode_screen(full_name=full_name)
            err_screen = screen.__class__(
                text=(
                    f"❌ <b>Некорректный формат баркода!</b>\n\n"
                    f"Студент: <b>{full_name}</b> ✅\n\n"
                    "Баркод должен состоять ровно из 6 цифр с вашей ID-карты (например, <code>230101</code>):"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=err_screen, push_to_history=False)
            return

        # Check barcode uniqueness
        stmt = select(User).where(
            or_(User.barcode == barcode, User.student_barcode == barcode),
            User.telegram_id != user_id,
        )
        existing_other = (await session.execute(stmt)).scalar_one_or_none()
        if existing_other:
            screen = get_barcode_screen(full_name=full_name)
            err_screen = screen.__class__(
                text=(
                    f"❌ <b>Баркод уже зарегистрирован!</b>\n\n"
                    f"Баркод <code>{barcode}</code> уже привязан к другому аккаунту.\n"
                    "Пожалуйста, проверьте данные или обратитесь в саппорт."
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=err_screen, push_to_history=False)
            return

        # Dispatch OTP via AuthService
        auth_service = AuthService(session=session, redis=core.redis, settings_obj=core.settings)
        try:
            target_gmail = data.get("gmail")
            recipient = await auth_service.send_student_otp(
                telegram_id=user_id,
                barcode=barcode,
                target_email=target_gmail,
            )
        except HTTPException as exc:
            screen = get_barcode_screen(full_name=full_name)
            detail = exc.detail if isinstance(exc.detail, str) else "Ошибка отправки кода"
            err_screen = screen.__class__(
                text=f"⚠️ <b>{detail}</b>\n\nПожалуйста, подождите или повторите ввод баркода:",
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=err_screen, push_to_history=False)
            return

        await state.update_data(barcode=barcode)
        await state.set_state(AuthStates.waiting_otp)

        screen = get_otp_screen(barcode=barcode, target_email=recipient)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:otp",
            push_to_history=True,
        )

    # Resend OTP handler
    @router.callback_query(F.data.startswith("auth:otp:resend"))
    async def cb_resend_otp(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        data = await state.get_data()
        barcode = data.get("barcode")
        target_gmail = data.get("gmail")
        if not barcode:
            await callback.answer("Сначала введите баркод", show_alert=True)
            return

        auth_service = AuthService(session=session, redis=core.redis, settings_obj=core.settings)
        try:
            await auth_service.send_student_otp(
                telegram_id=user_id,
                barcode=barcode,
                target_email=target_gmail,
            )
            await callback.answer("Код отправлен повторно!", show_alert=True)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else "Подождите перед повторной отправкой"
            await callback.answer(f"⚠️ {detail}", show_alert=True)

    # Student OTP verification
    @router.message(AuthStates.waiting_otp)
    async def process_otp(message: Message, state: FSMContext, session: AsyncSession) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        otp_code = (message.text or "").strip()

        data = await state.get_data()
        barcode = data.get("barcode", "")
        full_name = data.get("full_name", "")
        phone = data.get("phone", "")
        gmail = data.get("gmail", "")

        auth_service = AuthService(session=session, redis=core.redis, settings_obj=core.settings)
        try:
            await auth_service.verify_student_otp(telegram_id=user_id, barcode=barcode, otp_code=otp_code)
        except HTTPException as exc:
            if exc.status_code == 403:
                # 3 failed attempts: reset state
                await state.clear()
                screen = get_registration_cancelled_screen()
                await core.navigator.render(
                    user_id=user_id,
                    chat_id=chat_id,
                    screen=screen,
                    screen_id="reg_cancelled",
                    push_to_history=False,
                )
                return
            else:
                target_email = gmail if not core.settings.is_production else None
                screen = get_otp_screen(barcode=barcode, target_email=target_email)
                detail = exc.detail if isinstance(exc.detail, str) else "Неверный код"
                err_screen = screen.__class__(
                    text=f"❌ <b>{detail}</b>\n\nПопробуйте ввести код еще раз:",
                    reply_markup=screen.reply_markup,
                )
                await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=err_screen, push_to_history=False)
                return

        # Success: Write student to DB
        parts = full_name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        if user:
            user.full_name = full_name
            user.first_name = first_name
            user.last_name = last_name
            user.phone_number = phone
            user.email = gmail
            user.barcode = barcode
            user.role = "student"
            user.is_verified = True
        else:
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
                email=gmail,
                barcode=barcode,
                role="student",
                is_verified=True,
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)
        await state.clear()

        # Render Main Authorized Menu
        screen = get_authorized_menu_screen(
            full_name=full_name,
            role="student",
            is_verified=True,
            has_steam=bool(user.steam_id),
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="home",
            push_to_history=True,
        )

    # =========================================================================
    # Guest branch: State: INPUT_STEAM -> Save to DB -> Authorized Menu
    # =========================================================================

    @router.callback_query(F.data == "auth:steam:skip")
    async def cb_steam_skip(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        data = await state.get_data()
        full_name = data.get("full_name", "")
        phone = data.get("phone", "")
        gmail = data.get("gmail", "")

        parts = full_name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        if user:
            user.full_name = full_name
            user.first_name = first_name
            user.last_name = last_name
            user.phone_number = phone
            user.email = gmail
            user.role = "guest"
            user.is_verified = False
        else:
            user = User(
                telegram_id=user_id,
                username=callback.from_user.username,
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
                email=gmail,
                role="guest",
                is_verified=False,
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)
        await state.clear()

        screen = get_authorized_menu_screen(
            full_name=full_name,
            role="guest",
            is_verified=False,
            has_steam=False,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="home",
            push_to_history=True,
        )
        await callback.answer()

    @router.message(AuthStates.waiting_steam)
    async def process_steam(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        data = await state.get_data()
        is_registration = (data.get("role") != "student" and bool(data.get("full_name")))

        steam_service = SteamService(settings_obj=core.settings)
        login_state = await steam_service.create_login_state(
            telegram_id=user_id,
            redis=core.redis,
            extra_data=data,
        )
        steam_bridge_url = steam_service.build_bridge_url(login_state)
        base_screen = get_steam_screen(steam_auth_url=steam_bridge_url, is_registration=is_registration, use_web_app=True)
        err_screen = base_screen.__class__(
            text=(
                "⚠️ <b>Ручной ввод Steam ID отключен!</b>\n\n"
                "Для безопасной привязки аккаунта откройте официальный шлюз Valve по кнопке <b>«🎮 Привязать Steam»</b> ниже."
            ),
            reply_markup=base_screen.reply_markup,
        )
        await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=err_screen, push_to_history=False)

    # =========================================================================
    # Navigation & Profile Handlers
    # =========================================================================

    @router.callback_query(F.data == "nav:home")
    async def cb_home(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        await _clean_contact_markup(chat_id, state)
        await state.clear()

        stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        if user and user.full_name:
            screen = get_authorized_menu_screen(
                full_name=user.full_name,
                role=user.role,
                is_verified=user.is_verified,
                has_steam=bool(user.steam_id),
            )
        else:
            screen = get_club_info_screen()

        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="home",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "auth:profile")
    async def cb_profile(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        user_data = {
            "first_name": user.first_name if user else callback.from_user.first_name,
            "last_name": user.last_name if user else callback.from_user.last_name,
            "full_name": user.full_name if user else None,
            "username": user.username if user else callback.from_user.username,
            "barcode": user.barcode if user else None,
            "phone_number": user.phone_number if user else None,
            "email": user.email if user else None,
            "steam_id": user.steam_id if user else None,
            "is_verified": user.is_verified if user else False,
            "role": user.role if user else "guest",
        }

        screen = get_profile_screen(user_data)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:profile",
            push_to_history=True,
        )
        await callback.answer()

    # Link Steam from Profile
    @router.callback_query(F.data == "auth:profile:link_steam")
    async def cb_profile_link_steam(callback: CallbackQuery, state: FSMContext) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        await state.set_state(AuthStates.waiting_steam)

        steam_service = SteamService(settings_obj=core.settings)
        login_state = await steam_service.create_login_state(
            telegram_id=user_id,
            redis=core.redis,
            extra_data={"is_profile_link": True},
        )
        steam_bridge_url = steam_service.build_bridge_url(login_state)
        screen = get_steam_screen(steam_auth_url=steam_bridge_url, is_registration=False, use_web_app=True)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:steam",
            push_to_history=True,
        )
        await callback.answer()

    # Upgrade to student from Profile
    @router.callback_query(F.data == "auth:profile:upgrade_student")
    async def cb_profile_upgrade_student(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(User).where(User.telegram_id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        await state.update_data(
            full_name=user.full_name if user else "Студент",
            phone=user.phone_number if user else "",
            gmail=user.email if user else "",
            role="student",
        )
        await state.set_state(AuthStates.waiting_barcode)

        screen = get_barcode_screen(full_name=user.full_name if user else "Студент")
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:barcode",
            push_to_history=True,
        )
        await callback.answer()

    @router.message(F.chat.type == "private", default_state)
    async def fallback_handler(message: Message, session: AsyncSession, state: FSMContext) -> None:
        """
        Fallback for when a user deletes the anchor message and sends random text outside of any flow.
        GarbageCollector deletes the text, but this handler recreates the anchor.
        """
        current_state = await state.get_state()
        if current_state is not None:
            return
        await cmd_start(message, session, state)

    return router
