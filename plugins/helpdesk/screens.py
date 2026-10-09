from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from common.dtos.screen import Screen
from common.models.ticket import HelpdeskTicket
from common.texts import get_text


def get_helpdesk_home_screen(open_tickets_count: int = 0) -> Screen:
    """Helpdesk main menu screen."""
    if open_tickets_count:
        tickets_info = get_text("helpdesk.home.open_tickets", count=open_tickets_count)
    else:
        tickets_info = get_text("helpdesk.home.no_open_tickets")

    text = get_text("helpdesk.home.text", tickets_info=tickets_info)
    buttons = [
        [
            InlineKeyboardButton(text=get_text("helpdesk.home.buttons.create"), callback_data="hd:create"),
        ],
        [
            InlineKeyboardButton(text=get_text("helpdesk.home.buttons.my_tickets"), callback_data="hd:my_tickets"),
        ],
        [
            InlineKeyboardButton(text=get_text("helpdesk.home.buttons.main_menu"), callback_data="nav:home"),
        ],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_ticket_subject_prompt_screen() -> Screen:
    """Prompt asking user to select or enter ticket subject."""
    text = get_text("helpdesk.subject_prompt.text")
    buttons = [
        [InlineKeyboardButton(text=get_text("helpdesk.subject_prompt.buttons.minecraft"), callback_data="hd:subj:mc")],
        [InlineKeyboardButton(text=get_text("helpdesk.subject_prompt.buttons.auth"), callback_data="hd:subj:auth")],
        [InlineKeyboardButton(text=get_text("helpdesk.subject_prompt.buttons.tournaments"), callback_data="hd:subj:tournaments")],
        [InlineKeyboardButton(text=get_text("helpdesk.subject_prompt.buttons.back"), callback_data="nav:helpdesk")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_ticket_message_prompt_screen(subject: str) -> Screen:
    """Prompt asking user to enter ticket description."""
    text = get_text("helpdesk.message_prompt.text", subject=subject)
    buttons = [
        [InlineKeyboardButton(text=get_text("helpdesk.message_prompt.buttons.cancel"), callback_data="nav:helpdesk")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_ticket_created_screen(ticket_id: int, subject: str) -> Screen:
    """Screen confirming ticket creation."""
    text = get_text("helpdesk.ticket_created.text", ticket_id=ticket_id, subject=subject)
    buttons = [
        [InlineKeyboardButton(text=get_text("helpdesk.ticket_created.buttons.my_tickets"), callback_data="hd:my_tickets")],
        [InlineKeyboardButton(text=get_text("helpdesk.ticket_created.buttons.helpdesk"), callback_data="nav:helpdesk")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_my_tickets_screen(tickets: list[HelpdeskTicket]) -> Screen:
    """Screen displaying user's ticket list."""
    if not tickets:
        text = get_text("helpdesk.my_tickets.empty")
    else:
        text = get_text("helpdesk.my_tickets.header")
        for t in tickets[:5]:
            status_icon = "🟢" if t.status == "RESOLVED" else "🟡"
            text += (
                f"{status_icon} <b>Тикет #{t.id}</b>: {t.subject}\n"
                f"Статус: <i>{t.status.value}</i> | Создан: {t.created_at.strftime('%d.%m %H:%M')}\n\n"
            )

    buttons = [
        [InlineKeyboardButton(text=get_text("helpdesk.my_tickets.buttons.create"), callback_data="hd:create")],
        [InlineKeyboardButton(text=get_text("helpdesk.my_tickets.buttons.helpdesk"), callback_data="nav:helpdesk")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
