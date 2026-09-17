import re
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import UserRole
from common.models.user import User
from common.dtos.events import UserVerifiedEvent
from core.context import CoreContext
from plugins.auth.screens import (
    get_welcome_screen,
    get_first_name_prompt_screen,
    get_last_name_prompt_screen,
    get_barcode_prompt_screen,
    get_phone_prompt_screen,
    get_email_prompt_screen,
    get_group_prompt_screen,
    get_verification_success_screen,
    get_profile_screen,
)

logger = logging.getLogger("plugins.auth.router")

router = Router(name="auth_router")


class AuthStates(StatesGroup):
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_barcode = State()
    waiting_phone = State()
    waiting_email = State()
    waiting_group = State()


def setup_auth_routes(core: CoreContext) -> Router:
    """Configures and binds core dependencies to the Auth router."""

    # Register screen renderers in Navigator for deterministic Back navigation
    async def render_home(user_id: int, chat_id: int, payload: dict) -> any:
        async with core.db_session_factory() as session:
            stmt = select(User).where(User.telegram_id == user_id)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            is_verified = user.is_verified if user else False
            full_name = f"{user.first_name} {user.last_name}".strip() if user and user.first_name else "Студент"
            return get_welcome_screen(is_verified=is_verified, full_name=full_name)

    core.navigator.register_screen_renderer("home", render_home)  # type: ignore

    @router.message(CommandStart())
    async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = message.from_user.id
        chat_id = message.chat.id
        username = message.from_user.username

        # Upsert User in DB
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=user_id,
                username=username,
                role=UserRole.STUDENT,
                is_verified=False,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # Reset history and render Welcome screen
        await core.navigator.reset_history(user_id)
        full_name = f"{user.first_name} {user.last_name}".strip() if user.first_name else "Студент"
        screen = get_welcome_screen(is_verified=user.is_verified, full_name=full_name)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="home",
            push_to_history=True,
        )

    @router.callback_query(F.data == "nav:home")
    async def cb_home(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        is_verified = user.is_verified if user else False
        full_name = f"{user.first_name} {user.last_name}".strip() if user and user.first_name else "Студент"

        screen = get_welcome_screen(is_verified=is_verified, full_name=full_name)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="home",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "nav:back")
    async def cb_back(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        success = await core.navigator.back(user_id=user_id, chat_id=chat_id)
        if not success:
            # If stack is empty, return to home
            stmt = select(User).where(User.telegram_id == user_id)
            async with core.db_session_factory() as session:
                res = await session.execute(stmt)
                user = res.scalar_one_or_none()
                full_name = f"{user.first_name} {user.last_name}".strip() if user and user.first_name else "Студент"
                screen = get_welcome_screen(
                    is_verified=user.is_verified if user else False,
                    full_name=full_name,
                )
                await core.navigator.render(
                    user_id=user_id,
                    chat_id=chat_id,
                    screen=screen,
                    screen_id="home",
                    push_to_history=False,
                )
        await callback.answer()

    @router.callback_query(F.data == "auth:start")
    async def cb_auth_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(AuthStates.waiting_first_name)
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        screen = get_first_name_prompt_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:first_name",
            push_to_history=True,
        )
        await callback.answer()

    @router.message(AuthStates.waiting_first_name)
    async def process_first_name(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        raw_text = (message.text or "").strip()

        if len(raw_text) < 2:
            screen = get_first_name_prompt_screen()
            error_screen = screen.__class__(
                text="❌ <b>Имя слишком короткое.</b> Пожалуйста, введите настоящее Имя:\n",
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=error_screen, push_to_history=False)
            return

        await state.update_data(first_name=raw_text)
        await state.set_state(AuthStates.waiting_last_name)

        screen = get_last_name_prompt_screen(first_name=raw_text)
        await core.navigator.render(
            user_id=user_id, chat_id=chat_id, screen=screen, screen_id="auth:last_name", push_to_history=True
        )

    @router.message(AuthStates.waiting_last_name)
    async def process_last_name(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        raw_text = (message.text or "").strip()

        data = await state.get_data()
        first_name = data.get("first_name", "")

        if len(raw_text) < 2:
            screen = get_last_name_prompt_screen(first_name=first_name)
            error_screen = screen.__class__(
                text=f"❌ <b>Фамилия слишком короткая.</b>\nИмя: {first_name} ✅\nПожалуйста, введите настоящую Фамилию:\n",
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=error_screen, push_to_history=False)
            return

        await state.update_data(last_name=raw_text)
        await state.set_state(AuthStates.waiting_barcode)

        screen = get_barcode_prompt_screen(first_name=first_name, last_name=raw_text)
        await core.navigator.render(
            user_id=user_id, chat_id=chat_id, screen=screen, screen_id="auth:barcode", push_to_history=True
        )

    @router.message(AuthStates.waiting_barcode)
    async def process_barcode(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        barcode = (message.text or "").strip()

        data = await state.get_data()
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")

        # Validation: exactly 6 digits
        if not re.fullmatch(r"^\d{6}$", barcode):
            screen = get_barcode_prompt_screen(first_name=first_name, last_name=last_name)
            error_screen = screen.__class__(
                text=(
                    f"❌ <b>Некорректный формат штрих-кода!</b>\n\n"
                    f"Штрих-код должен состоять ровно из 6 цифр.\n"
                    "Пожалуйста, повторите ввод:"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=error_screen, push_to_history=False)
            return

        await state.update_data(barcode=barcode)
        await state.set_state(AuthStates.waiting_phone)

        screen = get_phone_prompt_screen(barcode=barcode)
        await core.navigator.render(
            user_id=user_id, chat_id=chat_id, screen=screen, screen_id="auth:phone", push_to_history=True
        )

    @router.message(AuthStates.waiting_phone)
    async def process_phone(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        phone = (message.text or "").strip()

        data = await state.get_data()
        barcode = data.get("barcode", "")

        # Basic phone validation (e.g. +7... or 8...)
        if not re.fullmatch(r"^\+?\d{10,15}$", phone.replace(" ", "").replace("-", "")):
            screen = get_phone_prompt_screen(barcode=barcode)
            error_screen = screen.__class__(
                text=(
                    f"❌ <b>Некорректный формат телефона!</b>\n\n"
                    f"Пожалуйста, введите корректный номер (например: +77772179050):"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=error_screen, push_to_history=False)
            return

        await state.update_data(phone=phone)
        await state.set_state(AuthStates.waiting_email)

        screen = get_email_prompt_screen(phone=phone)
        await core.navigator.render(
            user_id=user_id, chat_id=chat_id, screen=screen, screen_id="auth:email", push_to_history=True
        )

    @router.message(AuthStates.waiting_email)
    async def process_email(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        email = (message.text or "").strip()

        data = await state.get_data()
        phone = data.get("phone", "")

        # Basic email validation
        if not re.fullmatch(r"^[\w\.\-]+@[\w\.\-]+\.\w+$", email):
            screen = get_email_prompt_screen(phone=phone)
            error_screen = screen.__class__(
                text=(
                    f"❌ <b>Некорректный формат email!</b>\n\n"
                    f"Пожалуйста, введите корректный адрес (например: example@gmail.com):"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=error_screen, push_to_history=False)
            return

        await state.update_data(email=email)
        await state.set_state(AuthStates.waiting_group)

        screen = get_group_prompt_screen(email=email)
        await core.navigator.render(
            user_id=user_id, chat_id=chat_id, screen=screen, screen_id="auth:group", push_to_history=True
        )

    @router.message(AuthStates.waiting_group)
    async def process_group(message: Message, state: FSMContext, session: AsyncSession) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        group = (message.text or "").strip().upper()

        data = await state.get_data()
        email = data.get("email", "")

        # Group validation XX-YYZZ
        if not re.fullmatch(r"^[A-Z]{2,4}-\d{4}$", group):
            screen = get_group_prompt_screen(email=email)
            error_screen = screen.__class__(
                text=(
                    f"❌ <b>Некорректный формат группы!</b>\n\n"
                    f"Убедитесь, что формат XX-YYZZ (например: CS-2424, SE-2331).\n"
                    "Пожалуйста, повторите ввод:"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=error_screen, push_to_history=False)
            return

        data = await state.get_data()
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        barcode = data.get("barcode", "")
        phone = data.get("phone", "")
        await state.clear()

        # Persist verified user in Database
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.first_name = first_name
            user.last_name = last_name
            user.barcode = barcode
            user.phone_number = phone
            user.email = email
            user.academic_group = group
            user.is_verified = True
            user.role = UserRole.STUDENT
        else:
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=first_name,
                last_name=last_name,
                barcode=barcode,
                phone_number=phone,
                email=email,
                academic_group=group,
                role=UserRole.STUDENT,
                is_verified=True,
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)

        # Publish Domain Event to Event Bus (strictly past-tense domain fact)
        event = UserVerifiedEvent(
            telegram_id=user.telegram_id,
            barcode=user.barcode,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            phone_number=user.phone_number or "",
            email=user.email or "",
            academic_group=user.academic_group or "",
            role=user.role,
        )
        await core.event_bus.publish(event)

        # Render Success Screen
        full_name = f"{first_name} {last_name}".strip()
        screen = get_verification_success_screen(full_name=full_name, barcode=barcode, group=group)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:success",
            push_to_history=True,
        )

    @router.callback_query(F.data == "auth:profile")
    async def cb_profile(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        user_data = {
            "first_name": user.first_name if user else callback.from_user.first_name,
            "last_name": user.last_name if user else callback.from_user.last_name,
            "username": user.username if user else callback.from_user.username,
            "barcode": user.barcode if user else None,
            "phone_number": user.phone_number if user else None,
            "email": user.email if user else None,
            "academic_group": user.academic_group if user else None,
            "is_verified": user.is_verified if user else False,
            "role": user.role.value if user else "STUDENT",
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

    return router
