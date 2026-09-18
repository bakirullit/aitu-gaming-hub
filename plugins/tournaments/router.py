import logging
from datetime import date
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import DisciplineType, TournamentStatus, UserRole
from common.models.tournament import DisciplineAdmin, TournamentBooking
from common.models.user import User
from core.context import CoreContext
from plugins.tournaments.states import TournamentBookingStates
from plugins.tournaments.screens import (
    get_access_denied_screen,
    get_tournaments_home_screen,
    get_discipline_choice_screen,
    get_booking_title_prompt_screen,
    get_slot_picker_screen,
    get_format_chips_screen,
    get_rulebook_prompt_screen,
    get_booking_confirmation_screen,
    get_booking_submitted_screen,
    get_booking_approved_screen,
    get_booking_rejected_screen,
    get_my_bookings_screen,
    build_admin_approval_keyboard,
    build_admin_approval_text,
    format_summary_label,
)

logger = logging.getLogger("plugins.tournaments.router")

router = Router(name="tournaments_router")


def setup_tournaments_routes(core: CoreContext) -> Router:
    """Configures and binds core dependencies to the Tournaments router."""

    # Register screen renderer for deterministic back-navigation
    async def render_tournaments_home(user_id: int, chat_id: int, payload: dict) -> any:
        async with core.db_session_factory() as session:
            stmt = select(DisciplineAdmin).where(DisciplineAdmin.telegram_id == user_id)
            res = await session.execute(stmt)
            admin_roles = res.scalars().all()
            disciplines = [str(r.discipline) for r in admin_roles]

            # Also check user role
            u_stmt = select(User).where(User.telegram_id == user_id)
            u_res = await session.execute(u_stmt)
            user = u_res.scalar_one_or_none()

            if not disciplines and user and user.role != UserRole.HEAD_ADMIN:
                return get_access_denied_screen()

            if not disciplines and user and user.role == UserRole.HEAD_ADMIN:
                disciplines = [d.value for d in DisciplineType]

            b_stmt = select(TournamentBooking).where(
                TournamentBooking.creator_id == user_id,
                TournamentBooking.status.in_([TournamentStatus.PENDING, TournamentStatus.APPROVED]),
            )
            b_res = await session.execute(b_stmt)
            active_count = len(b_res.scalars().all())

            return get_tournaments_home_screen(disciplines, active_bookings_count=active_count)

    core.navigator.register_screen_renderer("tournaments:home", render_tournaments_home)  # type: ignore

    # 1. Main entry: Tournaments Hub
    @router.callback_query(F.data == "nav:tournaments")
    async def cb_tournaments_home(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(DisciplineAdmin).where(DisciplineAdmin.telegram_id == user_id)
        res = await session.execute(stmt)
        admin_roles = res.scalars().all()
        disciplines = [str(r.discipline) for r in admin_roles]

        u_stmt = select(User).where(User.telegram_id == user_id)
        u_res = await session.execute(u_stmt)
        user = u_res.scalar_one_or_none()

        if not disciplines and user and user.role != UserRole.HEAD_ADMIN:
            screen = get_access_denied_screen()
            await core.navigator.render(
                user_id=user_id,
                chat_id=chat_id,
                screen=screen,
                screen_id="tournaments:denied",
                push_to_history=True,
            )
            await callback.answer()
            return

        if not disciplines and user and user.role == UserRole.HEAD_ADMIN:
            disciplines = [d.value for d in DisciplineType]

        b_stmt = select(TournamentBooking).where(
            TournamentBooking.creator_id == user_id,
            TournamentBooking.status.in_([TournamentStatus.PENDING, TournamentStatus.APPROVED]),
        )
        b_res = await session.execute(b_stmt)
        active_count = len(b_res.scalars().all())

        screen = get_tournaments_home_screen(disciplines, active_bookings_count=active_count)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="tournaments:home",
            push_to_history=True,
        )
        await callback.answer()

    # 2. Step 1: Start Zero-Input Wizard
    @router.callback_query(F.data == "tb:start")
    async def cb_start_booking(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        # Auto-lookup organizer identity from DB
        stmt = select(User).where(User.telegram_id == user_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        da_stmt = select(DisciplineAdmin).where(DisciplineAdmin.telegram_id == user_id)
        da_res = await session.execute(da_stmt)
        admin_roles = da_res.scalars().all()
        disciplines = [str(r.discipline) for r in admin_roles]

        if not disciplines and user and user.role == UserRole.HEAD_ADMIN:
            disciplines = [d.value for d in DisciplineType]

        if not disciplines:
            screen = get_access_denied_screen()
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=screen)
            await callback.answer()
            return

        organizer_name = (
            f"{user.first_name or ''} {user.last_name or ''}".strip()
            if user
            else (callback.from_user.full_name or f"@{callback.from_user.username}")
        )
        organizer_email = (user.email if user and user.email else "student@astanait.edu.kz")

        await state.update_data(
            creator_id=user_id,
            organizer_name=organizer_name,
            organizer_email=organizer_email,
            username=callback.from_user.username or "",
        )

        # If admin manages multiple disciplines, prompt for discipline first
        if len(disciplines) > 1:
            screen = get_discipline_choice_screen(disciplines)
            await core.navigator.render(
                user_id=user_id,
                chat_id=chat_id,
                screen=screen,
                screen_id="tb:choose_discipline",
                push_to_history=True,
            )
            await callback.answer()
            return

        # Single discipline auto-selected
        chosen_discipline = disciplines[0]
        await state.update_data(discipline=chosen_discipline)
        await state.set_state(TournamentBookingStates.waiting_title)

        screen = get_booking_title_prompt_screen(
            discipline=chosen_discipline,
            organizer_name=organizer_name,
            organizer_email=organizer_email,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="tb:prompt_title",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("tb:choose_disc:"))
    async def cb_choose_discipline(callback: CallbackQuery, state: FSMContext) -> None:
        chosen_disc = callback.data.split(":", 2)[2]
        data = await state.get_data()
        await state.update_data(discipline=chosen_disc)
        await state.set_state(TournamentBookingStates.waiting_title)

        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        screen = get_booking_title_prompt_screen(
            discipline=chosen_disc,
            organizer_name=data.get("organizer_name", ""),
            organizer_email=data.get("organizer_email", ""),
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="tb:prompt_title",
            push_to_history=True,
        )
        await callback.answer()

    # Step 1 -> Step 2: Title input intercept -> Slot Picker Grid
    @router.message(TournamentBookingStates.waiting_title)
    async def process_title(message: Message, state: FSMContext, session: AsyncSession) -> None:
        raw_text = (message.text or "").strip()
        user_id = message.from_user.id
        chat_id = message.chat.id
        data = await state.get_data()

        if len(raw_text) < 3:
            screen = get_booking_title_prompt_screen(
                discipline=data.get("discipline", "CS2"),
                organizer_name=data.get("organizer_name", ""),
                organizer_email=data.get("organizer_email", ""),
            )
            error_screen = screen.__class__(
                text=f"❌ <b>Слишком короткое название!</b>\n\n{screen.text}",
                reply_markup=screen.reply_markup,
            )
            await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=error_screen, push_to_history=False)
            return

        title = raw_text[:128]
        await state.update_data(title=title)
        await state.set_state(TournamentBookingStates.selecting_date)

        # Query occupied dates (APPROVED bookings lock the slot)
        stmt = select(TournamentBooking.booking_date).where(
            TournamentBooking.status == TournamentStatus.APPROVED
        )
        res = await session.execute(stmt)
        occupied_dates = set(res.scalars().all())

        screen = get_slot_picker_screen(
            title=title,
            discipline=data.get("discipline", "CS2"),
            occupied_dates=occupied_dates,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="tb:slot_picker",
            push_to_history=True,
        )

    # Slot Picker Interactions
    @router.callback_query(F.data.startswith("tb:occupied:"))
    async def cb_occupied_slot(callback: CallbackQuery) -> None:
        await callback.answer("⚠️ Этот слот уже занят другим турниром!", show_alert=True)

    @router.callback_query(F.data.startswith("tb:date:"))
    async def cb_select_date(callback: CallbackQuery, state: FSMContext) -> None:
        selected_date_str = callback.data.split(":", 2)[2]
        await state.update_data(
            booking_date=selected_date_str,
            format_loc="online",
            format_bracket="single_elim",
            format_roster="5x5",
        )
        await state.set_state(TournamentBookingStates.selecting_format)

        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        data = await state.get_data()

        # Format date for display (e.g. 24.09.2026)
        try:
            d_obj = date.fromisoformat(selected_date_str)
            disp_date = d_obj.strftime("%d.%m.%Y")
        except ValueError:
            disp_date = selected_date_str

        screen = get_format_chips_screen(
            title=data.get("title", ""),
            booking_date_str=disp_date,
            loc="online",
            bracket="single_elim",
            roster="5x5",
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="tb:format_chips",
            push_to_history=True,
        )
        await callback.answer()

    # Step 3: Format Chips
    @router.callback_query(F.data.startswith("tb:chip:"))
    async def cb_toggle_format_chip(callback: CallbackQuery, state: FSMContext) -> None:
        parts = callback.data.split(":")
        category = parts[2]
        value = parts[3]

        data = await state.get_data()
        loc = data.get("format_loc", "online")
        bracket = data.get("format_bracket", "single_elim")
        roster = data.get("format_roster", "5x5")

        if category == "loc":
            loc = value
            await state.update_data(format_loc=loc)
        elif category == "bracket":
            bracket = value
            await state.update_data(format_bracket=bracket)
        elif category == "roster":
            roster = value
            await state.update_data(format_roster=roster)

        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        date_str = data.get("booking_date", "")

        screen = get_format_chips_screen(
            title=data.get("title", ""),
            booking_date_str=date_str,
            loc=loc,
            bracket=bracket,
            roster=roster,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            push_to_history=False,
        )
        await callback.answer()

    @router.callback_query(F.data == "tb:confirm_format")
    async def cb_confirm_format(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        loc = data.get("format_loc", "online")
        bracket = data.get("format_bracket", "single_elim")
        roster = data.get("format_roster", "5x5")
        event_format = f"{loc}_{bracket}_{roster}"
        await state.update_data(event_format=event_format)

        await state.set_state(TournamentBookingStates.waiting_rulebook)
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        format_label = format_summary_label(event_format)

        screen = get_rulebook_prompt_screen(
            title=data.get("title", ""),
            booking_date_str=data.get("booking_date", ""),
            format_label=format_label,
            file_name=data.get("rulebook_file_name"),
            url=data.get("rulebook_url"),
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="tb:waiting_rulebook",
            push_to_history=True,
        )
        await callback.answer()

    # Step 4: Rulebook Interception (Document & URL)
    @router.message(TournamentBookingStates.waiting_rulebook, F.document)
    async def process_rulebook_document(message: Message, state: FSMContext) -> None:
        doc = message.document
        file_id = doc.file_id
        file_name = doc.file_name or "Rules.pdf"

        await state.update_data(
            rulebook_file_id=file_id,
            rulebook_file_name=file_name,
            rulebook_url=None,
        )

        user_id = message.from_user.id
        chat_id = message.chat.id
        data = await state.get_data()
        format_label = format_summary_label(data.get("event_format", "online_single_elim_5x5"))

        screen = get_rulebook_prompt_screen(
            title=data.get("title", ""),
            booking_date_str=data.get("booking_date", ""),
            format_label=format_label,
            file_name=file_name,
            url=None,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            push_to_history=False,
        )

    @router.message(TournamentBookingStates.waiting_rulebook, F.text)
    async def process_rulebook_text(message: Message, state: FSMContext) -> None:
        raw_text = (message.text or "").strip()
        user_id = message.from_user.id
        chat_id = message.chat.id
        data = await state.get_data()
        format_label = format_summary_label(data.get("event_format", "online_single_elim_5x5"))

        if raw_text.startswith("http://") or raw_text.startswith("https://"):
            await state.update_data(
                rulebook_url=raw_text,
                rulebook_file_id=None,
                rulebook_file_name=None,
            )
            screen = get_rulebook_prompt_screen(
                title=data.get("title", ""),
                booking_date_str=data.get("booking_date", ""),
                format_label=format_label,
                file_name=None,
                url=raw_text,
            )
        else:
            screen = get_rulebook_prompt_screen(
                title=data.get("title", ""),
                booking_date_str=data.get("booking_date", ""),
                format_label=format_label,
                file_name=data.get("rulebook_file_name"),
                url=data.get("rulebook_url"),
            )
            screen = screen.__class__(
                text=f"⚠️ <b>Пожалуйста, отправьте корректную ссылку (http/https) или прикрепите документ (PDF/DOCX).</b>\n\n{screen.text}",
                reply_markup=screen.reply_markup,
            )

        await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=screen, push_to_history=False)

    # Step 5: Summary Confirmation Card
    @router.callback_query(F.data == "tb:to_confirm")
    async def cb_to_confirm(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(TournamentBookingStates.confirm_booking)
        data = await state.get_data()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        format_label = format_summary_label(data.get("event_format", "online_single_elim_5x5"))
        if data.get("rulebook_file_name"):
            rulebook_display = f"📄 {data['rulebook_file_name']} (Telegram File)"
        elif data.get("rulebook_url"):
            rulebook_display = f"🔗 {data['rulebook_url']}"
        else:
            rulebook_display = "Не указан"

        screen = get_booking_confirmation_screen(
            title=data.get("title", ""),
            discipline=data.get("discipline", "CS2"),
            organizer_name=data.get("organizer_name", ""),
            organizer_email=data.get("organizer_email", ""),
            booking_date_str=data.get("booking_date", ""),
            format_label=format_label,
            rulebook_display=rulebook_display,
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="tb:confirmation",
            push_to_history=True,
        )
        await callback.answer()

    # Step 6: Submit to Management Admin Chat
    @router.callback_query(F.data == "tb:submit")
    async def cb_submit_booking(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        data = await state.get_data()
        await state.clear()

        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        booking_date_raw = data.get("booking_date")
        b_date = date.fromisoformat(booking_date_raw) if booking_date_raw else date.today()

        # Create booking in DB
        booking = TournamentBooking(
            creator_id=user_id,
            discipline=DisciplineType(data.get("discipline", "CS2")),
            title=data.get("title", "Турнир"),
            booking_date=b_date,
            event_format=data.get("event_format", "online_single_elim_5x5"),
            rulebook_file_id=data.get("rulebook_file_id"),
            rulebook_url=data.get("rulebook_url"),
            status=TournamentStatus.PENDING,
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)

        # Lookup creator user for notification & admin card
        u_stmt = select(User).where(User.telegram_id == user_id)
        u_res = await session.execute(u_stmt)
        creator_user = u_res.scalar_one_or_none() or User(telegram_id=user_id)

        # Forward to Head Admin Topic / Management Chat
        admin_chat_id = core.settings.TOURNAMENT_ADMIN_CHAT_ID or core.settings.HELPDESK_ADMIN_CHAT_ID
        if admin_chat_id:
            try:
                organizer_tag = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
                admin_text = build_admin_approval_text(booking, creator_user, organizer_tag)
                approval_kb = build_admin_approval_keyboard(booking.id)

                # Send document directly if file_id is attached, else send message
                if booking.rulebook_file_id:
                    admin_msg = await core.bot.send_document(
                        chat_id=admin_chat_id,
                        document=booking.rulebook_file_id,
                        caption=admin_text,
                        parse_mode="HTML",
                        reply_markup=approval_kb,
                    )
                else:
                    admin_msg = await core.bot.send_message(
                        chat_id=admin_chat_id,
                        text=admin_text,
                        parse_mode="HTML",
                        reply_markup=approval_kb,
                    )

                booking.approval_msg_id = admin_msg.message_id
                await session.commit()
            except Exception as exc:
                logger.error(f"Failed to route tournament booking #{booking.id} to admin chat: {exc}")

        # Render submission confirmation in user's anchor message
        screen = get_booking_submitted_screen(
            title=booking.title,
            booking_date_str=booking.booking_date.strftime("%d.%m.%Y"),
        )
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="tb:submitted",
            push_to_history=True,
        )
        await callback.answer("Заявка успешно отправлена руководству!")

    # -------------------------------------------------------------
    # Admin Approval Gateway Handlers (with Race Condition Guard)
    # -------------------------------------------------------------
    @router.callback_query(F.data.startswith("tb_adm:approve:"))
    async def cb_admin_approve(callback: CallbackQuery, session: AsyncSession) -> None:
        booking_id = int(callback.data.split(":", 2)[2])

        stmt = select(TournamentBooking).where(TournamentBooking.id == booking_id)
        res = await session.execute(stmt)
        booking = res.scalar_one_or_none()

        if not booking:
            await callback.answer("❌ Заявка не найдена!", show_alert=True)
            return

        if booking.status == TournamentStatus.APPROVED:
            await callback.answer("ℹ️ Этот слот уже подтвержден ранее.", show_alert=True)
            return

        # RACE CONDITION GUARD: Check if another booking on the same date was already APPROVED
        occupied = await session.scalar(
            select(TournamentBooking).where(
                TournamentBooking.booking_date == booking.booking_date,
                TournamentBooking.status == TournamentStatus.APPROVED,
                TournamentBooking.id != booking.id,
            )
        )
        if occupied:
            await callback.answer("⚠️ Этот слот уже был одобрен для другого турнира!", show_alert=True)
            return

        # Mark APPROVED
        booking.status = TournamentStatus.APPROVED
        await session.commit()

        approver_name = (
            f"@{callback.from_user.username}"
            if callback.from_user.username
            else (callback.from_user.full_name or "Администратор")
        )

        # Update message in admin channel to show approval verdict
        try:
            status_line = f"\n\n✅ <b>Слот подтвержден</b> администратором {approver_name}"
            if callback.message.caption:
                await callback.message.edit_caption(
                    caption=callback.message.caption + status_line,
                    parse_mode="HTML",
                    reply_markup=None,
                )
            elif callback.message.text:
                await callback.message.edit_text(
                    text=callback.message.text + status_line,
                    parse_mode="HTML",
                    reply_markup=None,
                )
        except Exception as exc:
            logger.warning(f"Could not edit admin message: {exc}")

        await callback.answer("✅ Слот успешно подтвержден!")

        # Notify creator in private chat via Anchor Navigator
        date_str = booking.booking_date.strftime("%d.%m.%Y")
        screen = get_booking_approved_screen(
            title=booking.title,
            booking_date_str=date_str,
            discipline=str(booking.discipline),
        )
        try:
            await core.navigator.render(
                user_id=booking.creator_id,
                chat_id=booking.creator_id,
                screen=screen,
                screen_id="tb:approved_notify",
                push_to_history=True,
            )
        except Exception as exc:
            logger.warning(f"Could not notify creator #{booking.creator_id} of approval: {exc}")

    @router.callback_query(F.data.startswith("tb_adm:reject:"))
    async def cb_admin_reject(callback: CallbackQuery, session: AsyncSession) -> None:
        booking_id = int(callback.data.split(":", 2)[2])

        stmt = select(TournamentBooking).where(TournamentBooking.id == booking_id)
        res = await session.execute(stmt)
        booking = res.scalar_one_or_none()

        if not booking:
            await callback.answer("❌ Заявка не найдена!", show_alert=True)
            return

        booking.status = TournamentStatus.REJECTED
        await session.commit()

        rejector_name = (
            f"@{callback.from_user.username}"
            if callback.from_user.username
            else (callback.from_user.full_name or "Администратор")
        )

        try:
            status_line = f"\n\n❌ <b>Заявка отклонена</b> администратором {rejector_name}"
            if callback.message.caption:
                await callback.message.edit_caption(
                    caption=callback.message.caption + status_line,
                    parse_mode="HTML",
                    reply_markup=None,
                )
            elif callback.message.text:
                await callback.message.edit_text(
                    text=callback.message.text + status_line,
                    parse_mode="HTML",
                    reply_markup=None,
                )
        except Exception as exc:
            logger.warning(f"Could not edit admin message: {exc}")

        await callback.answer("❌ Заявка отклонена")

        # Notify creator via Navigator
        date_str = booking.booking_date.strftime("%d.%m.%Y")
        screen = get_booking_rejected_screen(
            title=booking.title,
            booking_date_str=date_str,
            discipline=str(booking.discipline),
        )
        try:
            await core.navigator.render(
                user_id=booking.creator_id,
                chat_id=booking.creator_id,
                screen=screen,
                screen_id="tb:rejected_notify",
                push_to_history=True,
            )
        except Exception as exc:
            logger.warning(f"Could not notify creator #{booking.creator_id} of rejection: {exc}")

    # Back Navigation Helpers
    @router.callback_query(F.data == "tb:back_to_title")
    async def cb_back_to_title(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(TournamentBookingStates.waiting_title)
        data = await state.get_data()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        screen = get_booking_title_prompt_screen(
            discipline=data.get("discipline", "CS2"),
            organizer_name=data.get("organizer_name", ""),
            organizer_email=data.get("organizer_email", ""),
        )
        await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=screen, push_to_history=False)
        await callback.answer()

    @router.callback_query(F.data == "tb:back_to_date")
    async def cb_back_to_date(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        await state.set_state(TournamentBookingStates.selecting_date)
        data = await state.get_data()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(TournamentBooking.booking_date).where(
            TournamentBooking.status == TournamentStatus.APPROVED
        )
        res = await session.execute(stmt)
        occupied_dates = set(res.scalars().all())

        screen = get_slot_picker_screen(
            title=data.get("title", ""),
            discipline=data.get("discipline", "CS2"),
            occupied_dates=occupied_dates,
        )
        await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=screen, push_to_history=False)
        await callback.answer()

    @router.callback_query(F.data == "tb:back_to_format")
    async def cb_back_to_format(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(TournamentBookingStates.selecting_format)
        data = await state.get_data()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        screen = get_format_chips_screen(
            title=data.get("title", ""),
            booking_date_str=data.get("booking_date", ""),
            loc=data.get("format_loc", "online"),
            bracket=data.get("format_bracket", "single_elim"),
            roster=data.get("format_roster", "5x5"),
        )
        await core.navigator.render(user_id=user_id, chat_id=chat_id, screen=screen, push_to_history=False)
        await callback.answer()

    @router.callback_query(F.data == "tb:my_bookings")
    async def cb_my_bookings(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = (
            select(TournamentBooking)
            .where(TournamentBooking.creator_id == user_id)
            .order_by(TournamentBooking.created_at.desc())
            .limit(10)
        )
        res = await session.execute(stmt)
        bookings = list(res.scalars().all())

        screen = get_my_bookings_screen(bookings=bookings)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="tb:my_bookings",
            push_to_history=True,
        )
        await callback.answer()

    return router
