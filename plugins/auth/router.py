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
    get_student_id_prompt_screen,
    get_barcode_prompt_screen,
    get_verification_success_screen,
    get_profile_screen,
)

logger = logging.getLogger("plugins.auth.router")

router = Router(name="auth_router")


class AuthStates(StatesGroup):
    waiting_student_id = State()
    waiting_barcode = State()


def setup_auth_routes(core: CoreContext) -> Router:
    """Configures and binds core dependencies to the Auth router."""

    # Register screen renderers in Navigator for deterministic Back navigation
    async def render_home(user_id: int, chat_id: int, payload: dict) -> any:
        async with core.db_session_factory() as session:
            stmt = select(User).where(User.telegram_id == user_id)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            is_verified = user.is_verified if user else False
            full_name = user.full_name if user else "Студент"
            return get_welcome_screen(is_verified=is_verified, full_name=full_name)

    core.navigator.register_screen_renderer("home", render_home)  # type: ignore

    @router.message(CommandStart())
    async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = message.from_user.id
        chat_id = message.chat.id
        full_name = message.from_user.full_name or "Студент"
        username = message.from_user.username

        # Upsert User in DB
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=user_id,
                username=username,
                full_name=full_name,
                role=UserRole.STUDENT,
                is_verified=False,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # Reset history and render Welcome screen
        await core.navigator.reset_history(user_id)
        screen = get_welcome_screen(is_verified=user.is_verified, full_name=user.full_name)
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
        full_name = user.full_name if user else "Студент"

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
                screen = get_welcome_screen(
                    is_verified=user.is_verified if user else False,
                    full_name=user.full_name if user else "Студент",
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
        await state.set_state(AuthStates.waiting_student_id)
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        screen = get_student_id_prompt_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:student_id",
            push_to_history=True,
        )
        await callback.answer()

    @router.message(AuthStates.waiting_student_id)
    async def process_student_id(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        raw_text = (message.text or "").strip()

        # Validation: 6-12 digits (AITU standard student ID is 9 digits)
        if not re.fullmatch(r"^\d{6,12}$", raw_text):
            screen = get_student_id_prompt_screen()
            error_screen = screen.__class__(
                text=(
                    "❌ <b>Некорректный формат Student ID!</b>\n\n"
                    "Student ID должен состоять только из цифр (например: <code>210103001</code>).\n\n"
                    "Попробуйте еще раз:"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(
                user_id=user_id,
                chat_id=chat_id,
                screen=error_screen,
                push_to_history=False,
            )
            return

        await state.update_data(student_id=raw_text)
        await state.set_state(AuthStates.waiting_barcode)

        screen = get_barcode_prompt_screen(student_id=raw_text)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="auth:barcode",
            push_to_history=True,
        )

    @router.message(AuthStates.waiting_barcode)
    async def process_barcode(message: Message, state: FSMContext, session: AsyncSession) -> None:
        user_id = message.from_user.id
        chat_id = message.chat.id
        barcode = (message.text or "").strip()

        # Validation: 6-20 digits
        if not re.fullmatch(r"^\d{6,20}$", barcode):
            data = await state.get_data()
            st_id = data.get("student_id", "")
            screen = get_barcode_prompt_screen(student_id=st_id)
            error_screen = screen.__class__(
                text=(
                    f"❌ <b>Некорректный формат штрих-кода!</b>\n\n"
                    f"Student ID: <code>{st_id}</code> ✅\n\n"
                    "Номер штрих-кода должен содержать от 6 до 20 цифр.\n"
                    "Пожалуйста, повторите ввод:"
                ),
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(
                user_id=user_id,
                chat_id=chat_id,
                screen=error_screen,
                push_to_history=False,
            )
            return

        data = await state.get_data()
        student_id = data.get("student_id", "")
        await state.clear()

        # Persist verified user in Database
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.student_id = student_id
            user.barcode = barcode
            user.is_verified = True
            user.role = UserRole.STUDENT
        else:
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name or "Студент",
                student_id=student_id,
                barcode=barcode,
                role=UserRole.STUDENT,
                is_verified=True,
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)

        # Publish Domain Event to Event Bus (strictly past-tense domain fact)
        event = UserVerifiedEvent(
            telegram_id=user.telegram_id,
            student_id=user.student_id,
            barcode=user.barcode,
            full_name=user.full_name,
            role=user.role,
        )
        await core.event_bus.publish(event)

        # Render Success Screen
        screen = get_verification_success_screen(student_id=student_id, full_name=user.full_name)
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
            "full_name": user.full_name if user else callback.from_user.full_name,
            "username": user.username if user else callback.from_user.username,
            "student_id": user.student_id if user else None,
            "barcode": user.barcode if user else None,
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
