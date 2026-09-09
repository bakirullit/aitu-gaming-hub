from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from common.dtos.screen import Screen
from common.models.ticket import HelpdeskTicket


def get_helpdesk_home_screen(open_tickets_count: int = 0) -> Screen:
    """Helpdesk main menu screen."""
    tickets_info = f"У вас <b>{open_tickets_count}</b> открытых обращений." if open_tickets_count else "У вас нет активных обращений."
    text = (
        "🎫 <b>Служба поддержки AITU Gaming Hub</b>\n\n"
        "Здесь вы можете задать вопрос администрации клуба, сообщить о проблеме "
        "с доступом или предложить идею для турнира.\n\n"
        f"📊 {tickets_info}\n\n"
        "Выберите действие:"
    )
    buttons = [
        [
            InlineKeyboardButton(text="✍️ Создать обращение (Тикет)", callback_data="hd:create"),
        ],
        [
            InlineKeyboardButton(text="📋 Мои обращения", callback_data="hd:my_tickets"),
        ],
        [
            InlineKeyboardButton(text="◀️ Главное меню", callback_data="nav:home"),
        ],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_ticket_subject_prompt_screen() -> Screen:
    """Prompt asking user to select or enter ticket subject."""
    text = (
        "🎫 <b>Создание обращения (Шаг 1 из 2)</b>\n\n"
        "Выберите или кратко напишите тему обращения:\n"
        "<i>💡 Текст будет удален сборщиком мусора, экран обновится на месте.</i>"
    )
    buttons = [
        [InlineKeyboardButton(text="⛏️ Проблема с сервером Minecraft", callback_data="hd:subj:mc")],
        [InlineKeyboardButton(text="🎓 Проблема с верификацией", callback_data="hd:subj:auth")],
        [InlineKeyboardButton(text="🏆 Турниры и киберспорт", callback_data="hd:subj:tournaments")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="nav:helpdesk")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_ticket_message_prompt_screen(subject: str) -> Screen:
    """Prompt asking user to enter ticket description."""
    text = (
        f"🎫 <b>Создание обращения (Шаг 2 из 2)</b>\n\n"
        f"Тема: <b>{subject}</b>\n\n"
        "Напишите подробно ваш вопрос или описание проблемы.\n\n"
        "<i>💡 Ваше сообщение будет удалено, а тикет мгновенно направлен кураторам клуба.</i>"
    )
    buttons = [
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:helpdesk")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_ticket_created_screen(ticket_id: int, subject: str) -> Screen:
    """Screen confirming ticket creation."""
    text = (
        f"✅ <b>Обращение #{ticket_id} успешно создано!</b>\n\n"
        f"• Тема: <b>{subject}</b>\n"
        f"• Статус: 🟡 <b>Ожидает ответа администратора</b>\n\n"
        "Администраторы клуба получили уведомление. Как только поступит ответ, "
        "вы получите мгновенное уведомление в этом чате."
    )
    buttons = [
        [InlineKeyboardButton(text="📋 Мои обращения", callback_data="hd:my_tickets")],
        [InlineKeyboardButton(text="◀️ В меню поддержки", callback_data="nav:helpdesk")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_my_tickets_screen(tickets: list[HelpdeskTicket]) -> Screen:
    """Screen displaying user's ticket list."""
    if not tickets:
        text = (
            "📋 <b>Мои обращения</b>\n\n"
            "У вас пока нет созданных обращений в службу поддержки."
        )
    else:
        text = "📋 <b>Ваши обращения:</b>\n\n"
        for t in tickets[:5]:
            status_icon = "🟢" if t.status == "RESOLVED" else "🟡"
            text += (
                f"{status_icon} <b>Тикет #{t.id}</b>: {t.subject}\n"
                f"Статус: <i>{t.status.value}</i> | Создан: {t.created_at.strftime('%d.%m %H:%M')}\n\n"
            )

    buttons = [
        [InlineKeyboardButton(text="✍️ Создать новое обращение", callback_data="hd:create")],
        [InlineKeyboardButton(text="◀️ В меню поддержки", callback_data="nav:helpdesk")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
