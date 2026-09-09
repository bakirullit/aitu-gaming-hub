import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import TicketStatus
from common.models.ticket import HelpdeskTicket
from common.models.user import User
from common.dtos.events import TicketCreatedEvent, TicketRepliedEvent
from core.context import CoreContext
from plugins.helpdesk.screens import (
    get_helpdesk_home_screen,
    get_ticket_subject_prompt_screen,
    get_ticket_message_prompt_screen,
    get_ticket_created_screen,
    get_my_tickets_screen,
)

logger = logging.getLogger("plugins.helpdesk.router")

router = Router(name="helpdesk_router")


class HelpdeskStates(StatesGroup):
    waiting_subject = State()
    waiting_message = State()


def setup_helpdesk_routes(core: CoreContext) -> Router:
    """Configures and binds core dependencies to the Helpdesk router."""

    async def render_helpdesk_home(user_id: int, chat_id: int, payload: dict) -> any:
        async with core.db_session_factory() as session:
            stmt = select(HelpdeskTicket).where(
                HelpdeskTicket.user_id == user_id,
                HelpdeskTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
            )
            res = await session.execute(stmt)
            open_count = len(res.scalars().all())
            return get_helpdesk_home_screen(open_tickets_count=open_count)

    core.navigator.register_screen_renderer("helpdesk:home", render_helpdesk_home)  # type: ignore

    @router.callback_query(F.data == "nav:helpdesk")
    async def cb_helpdesk_home(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
        await state.clear()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = select(HelpdeskTicket).where(
            HelpdeskTicket.user_id == user_id,
            HelpdeskTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
        )
        res = await session.execute(stmt)
        open_count = len(res.scalars().all())

        screen = get_helpdesk_home_screen(open_tickets_count=open_count)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="helpdesk:home",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "hd:my_tickets")
    async def cb_my_tickets(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        stmt = (
            select(HelpdeskTicket)
            .where(HelpdeskTicket.user_id == user_id)
            .order_by(HelpdeskTicket.created_at.desc())
            .limit(10)
        )
        res = await session.execute(stmt)
        tickets = list(res.scalars().all())

        screen = get_my_tickets_screen(tickets=tickets)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="helpdesk:my_tickets",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "hd:create")
    async def cb_create_ticket(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(HelpdeskStates.waiting_subject)
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        screen = get_ticket_subject_prompt_screen()
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="helpdesk:prompt_subject",
            push_to_history=True,
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("hd:subj:"))
    async def cb_subject_selected(callback: CallbackQuery, state: FSMContext) -> None:
        topic_map = {
            "hd:subj:mc": "Проблема с сервером Minecraft",
            "hd:subj:auth": "Проблема с верификацией",
            "hd:subj:tournaments": "Турниры и киберспорт",
        }
        subject = topic_map.get(callback.data, "Общий вопрос")
        await state.update_data(subject=subject)
        await state.set_state(HelpdeskStates.waiting_message)

        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        screen = get_ticket_message_prompt_screen(subject=subject)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="helpdesk:prompt_message",
            push_to_history=True,
        )
        await callback.answer()

    @router.message(HelpdeskStates.waiting_subject)
    async def process_custom_subject(message: Message, state: FSMContext) -> None:
        subject = (message.text or "Общий вопрос").strip()[:120]
        await state.update_data(subject=subject)
        await state.set_state(HelpdeskStates.waiting_message)

        user_id = message.from_user.id
        chat_id = message.chat.id
        screen = get_ticket_message_prompt_screen(subject=subject)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="helpdesk:prompt_message",
            push_to_history=True,
        )

    @router.message(HelpdeskStates.waiting_message)
    async def process_ticket_message(message: Message, state: FSMContext, session: AsyncSession) -> None:
        data = await state.get_data()
        subject = data.get("subject", "Общий вопрос")
        msg_text = (message.text or "").strip()[:2000]
        await state.clear()

        user_id = message.from_user.id
        chat_id = message.chat.id
        user_name = message.from_user.full_name or "Студент"
        username = message.from_user.username

        # Create ticket in DB
        ticket = HelpdeskTicket(
            user_id=user_id,
            subject=subject,
            message_text=msg_text,
            status=TicketStatus.OPEN,
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)

        # Publish Domain Event
        event = TicketCreatedEvent(
            ticket_id=ticket.id,
            user_id=user_id,
            subject=subject,
            message_text=msg_text,
        )
        await core.event_bus.publish(event)

        # Route to Admin Channel if configured
        admin_chat_id = core.settings.HELPDESK_ADMIN_CHAT_ID
        if admin_chat_id:
            try:
                username_str = f"@{username}" if username else "без username"
                admin_post = (
                    f"🎫 <b>Новый тикет #{ticket.id}</b>\n\n"
                    f"👤 Студент: <b>{user_name}</b> ({username_str}, ID: <code>{user_id}</code>)\n"
                    f"📌 Тема: <b>{subject}</b>\n\n"
                    f"💬 <b>Сообщение:</b>\n<i>{msg_text}</i>\n\n"
                    f"👉 <i>Чтобы ответить студенту, ответьте (Reply) на это сообщение.</i>"
                )
                admin_msg = await core.bot.send_message(
                    chat_id=admin_chat_id,
                    text=admin_post,
                    parse_mode="HTML",
                )
                ticket.admin_message_id = admin_msg.message_id
                await session.commit()
            except Exception as exc:
                logger.error(f"Failed to forward ticket #{ticket.id} to admin channel: {exc}")

        # Render confirmation screen into student's anchor message
        screen = get_ticket_created_screen(ticket_id=ticket.id, subject=subject)
        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="helpdesk:created",
            push_to_history=True,
        )

    # Admin Channel Reply Bridge (reply-message tracking)
    @router.message(F.reply_to_message)
    async def admin_channel_reply_bridge(message: Message, session: AsyncSession) -> None:
        admin_chat_id = core.settings.HELPDESK_ADMIN_CHAT_ID
        # Verify message originated from configured admin channel/chat
        if not admin_chat_id or message.chat.id != admin_chat_id:
            return

        replied_msg_id = message.reply_to_message.message_id
        reply_text = (message.text or "").strip()
        admin_id = message.from_user.id

        # Lookup ticket by admin_message_id
        stmt = select(HelpdeskTicket).where(HelpdeskTicket.admin_message_id == replied_msg_id)
        res = await session.execute(stmt)
        ticket = res.scalar_one_or_none()

        if not ticket:
            return

        # Update ticket status
        ticket.status = TicketStatus.RESOLVED
        await session.commit()

        # Publish TicketRepliedEvent
        event = TicketRepliedEvent(
            ticket_id=ticket.id,
            user_id=ticket.user_id,
            admin_id=admin_id,
            reply_text=reply_text,
        )
        await core.event_bus.publish(event)

        # Deliver response to student without breaking their anchor session
        try:
            delivery_text = (
                f"📩 <b>Ответ от службы поддержки по тикету #{ticket.id}</b>\n\n"
                f"📌 Тема: <b>{ticket.subject}</b>\n"
                f"💬 Ответ администратора:\n<i>{reply_text}</i>"
            )
            await core.bot.send_message(
                chat_id=ticket.user_id,
                text=delivery_text,
                parse_mode="HTML",
            )
            await message.reply(f"✅ Ответ успешно доставлен студенту по тикету #{ticket.id}.")
        except Exception as exc:
            logger.error(f"Failed to deliver ticket reply to student {ticket.user_id}: {exc}")
            await message.reply(f"⚠️ Не удалось доставить ответ студенту: {exc}")

    return router
