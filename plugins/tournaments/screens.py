from datetime import date, timedelta
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from common.dtos.screen import Screen
from common.models.tournament import TournamentBooking
from common.models.user import User

FORMAT_LOC_LABELS = {
    "online": "🌐 Онлайн",
    "lan": "🏢 LAN",
}

BRACKET_LABELS = {
    "single_elim": "⚔️ Single Elim",
    "double_elim": "🔄 Double Elim",
    "round_robin": "🔁 Round Robin",
}

ROSTER_LABELS = {
    "1x1": "👤 1x1",
    "2x2": "👥 2x2",
    "5x5": "👥 5x5",
}


def format_summary_label(event_format: str) -> str:
    """Parses format string e.g. online_single_elim_2x2 into human readable label."""
    parts = event_format.split("_")
    if len(parts) >= 4:
        loc = parts[0]
        bracket = f"{parts[1]}_{parts[2]}"
        roster = parts[3]
    elif len(parts) == 3:
        loc = parts[0]
        bracket = parts[1]
        roster = parts[2]
    else:
        return event_format

    loc_str = FORMAT_LOC_LABELS.get(loc, loc)
    bracket_str = BRACKET_LABELS.get(bracket, bracket)
    roster_str = ROSTER_LABELS.get(roster, roster)
    return f"{loc_str} • {bracket_str} • {roster_str}"


def get_access_denied_screen() -> Screen:
    """Screen shown when non-admin tries to access tournament booking."""
    text = (
        "⛔ <b>Доступ ограничен</b>\n\n"
        "Бронирование турниров доступно только аккредитованным <b>администраторам дисциплин</b> "
        "и руководству киберспортивного клуба AITU Gaming Hub.\n\n"
        "Если вы являетесь организатором, обратитесь в поддержку для выдачи прав."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎫 Обратиться в поддержку", callback_data="nav:helpdesk")],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_tournaments_home_screen(admin_disciplines: list[str], active_bookings_count: int = 0) -> Screen:
    """Tournaments hub home screen for discipline admins."""
    disciplines_str = ", ".join(admin_disciplines) if admin_disciplines else "Не назначено"
    text = (
        "🏆 <b>Управление турнирами AITU Gaming Hub</b>\n\n"
        f"Ваши закрепленные дисциплины: <b>{disciplines_str}</b>\n"
        f"Активных броней: <b>{active_bookings_count}</b>\n\n"
        "Anchor Wizard позволяет быстро зарезервировать слот даты, "
        "настроить формат соревнований и передать регламент руководству."
    )
    buttons = [
        [InlineKeyboardButton(text="📅 Забронировать слот турнира", callback_data="tb:start")],
        [InlineKeyboardButton(text="📋 Мои заявки на слоты", callback_data="tb:my_bookings")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="nav:home")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_discipline_choice_screen(disciplines: list[str]) -> Screen:
    """Prompt for admin managing multiple disciplines."""
    text = (
        "🎮 <b>Выбор дисциплины турнира</b>\n\n"
        "Вы курируете несколько дисциплин. Выберите дисциплину для проведения турнира:"
    )
    buttons = [
        [InlineKeyboardButton(text=f"🎮 {disc}", callback_data=f"tb:choose_disc:{disc}")]
        for disc in disciplines
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:tournaments")])
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_booking_title_prompt_screen(discipline: str, organizer_name: str, organizer_email: str) -> Screen:
    """Step 1: Tournament Title."""
    text = (
        f"🏆 <b>Бронь турнира: {discipline} (Шаг 1 из 4)</b>\n\n"
        f"👤 Организатор: <b>{organizer_name}</b>\n"
        f"📧 Email: <code>{organizer_email}</code>\n"
        f"🎮 Дисциплина: <b>{discipline}</b>\n\n"
        "Отправьте в чат <b>название турнира</b> (например: <code>AITU Spring Cup 2026</code>):\n\n"
        "<i>💡 Ввод текста будет удален сборщиком мусора, экран обновится на месте.</i>"
    )
    buttons = [
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:tournaments")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_slot_picker_screen(
    title: str,
    discipline: str,
    occupied_dates: set[date],
    days_ahead: int = 14,
    start_date: date | None = None,
) -> Screen:
    """Step 2: 14-day interactive calendar slot picker."""
    base_date = start_date or (date.today() + timedelta(days=1))
    text = (
        f"📅 <b>Выбор даты проведения (Шаг 2 из 4)</b>\n\n"
        f"Турнир: <b>{title}</b> ({discipline})\n\n"
        "Выберите подходящий день из доступных слотов на ближайшие 2 недели:\n"
        "🟢 — Свободный слот (нажмите для выбора)\n"
        "🔴 — Занято другим турниром (недоступно)"
    )

    buttons: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []

    for i in range(days_ahead):
        slot_day = base_date + timedelta(days=i)
        date_label = slot_day.strftime("%d.%m")
        is_occupied = slot_day in occupied_dates

        if is_occupied:
            btn = InlineKeyboardButton(
                text=f"{date_label} 🔴",
                callback_data=f"tb:occupied:{slot_day.isoformat()}",
            )
        else:
            btn = InlineKeyboardButton(
                text=f"{date_label} 🟢",
                callback_data=f"tb:date:{slot_day.isoformat()}",
            )

        current_row.append(btn)
        if len(current_row) == 2:  # 2 columns per row for clean mobile layout
            buttons.append(current_row)
            current_row = []

    if current_row:
        buttons.append(current_row)

    buttons.append([InlineKeyboardButton(text="◀️ Назад (изменить название)", callback_data="tb:back_to_title")])
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_format_chips_screen(
    title: str,
    booking_date_str: str,
    loc: str = "online",
    bracket: str = "single_elim",
    roster: str = "5x5",
) -> Screen:
    """Step 3: Interactive chips for event format."""
    summary = format_summary_label(f"{loc}_{bracket}_{roster}")
    text = (
        f"⚔️ <b>Формат турнира (Шаг 3 из 4)</b>\n\n"
        f"Турнир: <b>{title}</b>\n"
        f"Дата: <b>{booking_date_str}</b>\n\n"
        f"Текущий выбор: <b>{summary}</b>\n\n"
        "Переключайте параметры инлайн-кнопками ниже:"
    )

    # Row 1: Location (Online / LAN)
    row_loc = [
        InlineKeyboardButton(
            text=f"{'✅ ' if loc == 'online' else ''}🌐 Онлайн",
            callback_data="tb:chip:loc:online",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if loc == 'lan' else ''}🏢 LAN",
            callback_data="tb:chip:loc:lan",
        ),
    ]

    # Row 2: Bracket type
    row_bracket = [
        InlineKeyboardButton(
            text=f"{'✅ ' if bracket == 'single_elim' else ''}Single Elim",
            callback_data="tb:chip:bracket:single_elim",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if bracket == 'double_elim' else ''}Double Elim",
            callback_data="tb:chip:bracket:double_elim",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if bracket == 'round_robin' else ''}Round Robin",
            callback_data="tb:chip:bracket:round_robin",
        ),
    ]

    # Row 3: Roster composition
    row_roster = [
        InlineKeyboardButton(
            text=f"{'✅ ' if roster == '1x1' else ''}1x1",
            callback_data="tb:chip:roster:1x1",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if roster == '2x2' else ''}2x2",
            callback_data="tb:chip:roster:2x2",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if roster == '5x5' else ''}5x5",
            callback_data="tb:chip:roster:5x5",
        ),
    ]

    # Action row
    row_actions = [
        InlineKeyboardButton(text="◀️ Назад к дате", callback_data="tb:back_to_date"),
        InlineKeyboardButton(text="➡️ Далее (Регламент)", callback_data="tb:confirm_format"),
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[row_loc, row_bracket, row_roster, row_actions]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_rulebook_prompt_screen(
    title: str,
    booking_date_str: str,
    format_label: str,
    file_name: str | None = None,
    url: str | None = None,
) -> Screen:
    """Step 4: Rulebook upload or Google Drive link intercept."""
    if file_name:
        status_info = f"📄 <b>Файл регламента принят:</b> <code>{file_name}</code> ✅\n\n"
    elif url:
        status_info = f"🔗 <b>Ссылка на регламент:</b> <a href=\"{url}\">{url}</a> ✅\n\n"
    else:
        status_info = "⚠️ <i>Регламент пока не загружен.</i>\n\n"

    text = (
        f"📜 <b>Регламент турнира (Шаг 4 из 4)</b>\n\n"
        f"Турнир: <b>{title}</b>\n"
        f"Дата: <b>{booking_date_str}</b>\n"
        f"Формат: <b>{format_label}</b>\n\n"
        f"{status_info}"
        "Отправьте регламент соревнований в этот чат одним из способов:\n"
        "1️⃣ Прикрепите файл документом (<b>PDF</b> или <b>DOCX</b>)\n"
        "2️⃣ Пришлите ссылку на <b>Google Drive / Google Docs</b>\n\n"
        "<i>💡 Файл или ссылка будут автоматически прикреплены к заявке.</i>"
    )

    buttons: list[list[InlineKeyboardButton]] = []
    if file_name or url:
        buttons.append([
            InlineKeyboardButton(text="➡️ Далее к подтверждению", callback_data="tb:to_confirm")
        ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад к формату", callback_data="tb:back_to_format")
    ])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_booking_confirmation_screen(
    title: str,
    discipline: str,
    organizer_name: str,
    organizer_email: str,
    booking_date_str: str,
    format_label: str,
    rulebook_display: str,
) -> Screen:
    """Step 5: Final review card before sending to management chat."""
    text = (
        f"📅 <b>Бронь турнира: {title}</b>\n\n"
        f"• <b>Организатор:</b> {organizer_name} ({discipline} Admin)\n"
        f"• <b>Email:</b> <code>{organizer_email}</code>\n"
        f"• <b>Дата:</b> <b>{booking_date_str}</b>\n"
        f"• <b>Формат:</b> <b>{format_label}</b>\n"
        f"• <b>Регламент:</b> {rulebook_display}\n\n"
        "Отправить заявку на согласование руководству клуба?\n"
        "<i>После отправки дата будет ожидать подтверждения в чате руководства.</i>"
    )
    buttons = [
        [InlineKeyboardButton(text="🚀 Отправить руководству", callback_data="tb:submit")],
        [
            InlineKeyboardButton(text="🔄 С начала", callback_data="tb:start"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="nav:tournaments"),
        ],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_booking_submitted_screen(title: str, booking_date_str: str) -> Screen:
    """Screen shown immediately after submitting booking to management."""
    text = (
        "✅ <b>Заявка успешно отправлена руководству!</b>\n\n"
        f"Турнир: <b>{title}</b>\n"
        f"Запрошенный слот: <b>{booking_date_str}</b>\n\n"
        "Заявка направлена в закрытый чат руководства. "
        "Как только слот будет подтвержден, дата заблокируется в календаре, "
        "а вам придет уведомление в этом диалоге."
    )
    buttons = [
        [InlineKeyboardButton(text="🏆 В меню турниров", callback_data="nav:tournaments")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="nav:home")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_booking_approved_screen(title: str, booking_date_str: str, discipline: str) -> Screen:
    """Screen rendered into creator's anchor when head admin approves slot."""
    text = (
        "🎉 <b>Ваш турнир согласован!</b>\n\n"
        f"Турнир <b>{title}</b> ({discipline}) на дату <b>{booking_date_str}</b> "
        "успешно утвержден руководством киберспортивного клуба AITU Gaming Hub.\n\n"
        "🔒 Слот заблокирован в расписании для других организаторов."
    )
    buttons = [
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="tb:my_bookings")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="nav:home")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_booking_rejected_screen(title: str, booking_date_str: str, discipline: str) -> Screen:
    """Screen rendered into creator's anchor when head admin rejects slot."""
    text = (
        "❌ <b>Заявка на турнир отклонена</b>\n\n"
        f"Турнир <b>{title}</b> ({discipline}) на дату <b>{booking_date_str}</b> "
        "не был согласован руководством клуба.\n\n"
        "Слот освобожден. Вы можете выбрать другую дату или обратиться в поддержку."
    )
    buttons = [
        [InlineKeyboardButton(text="📅 Выбрать другой слот", callback_data="tb:start")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="nav:home")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_my_bookings_screen(bookings: list[TournamentBooking]) -> Screen:
    """List of creator's tournament bookings."""
    if not bookings:
        text = (
            "📋 <b>Ваши заявки на турниры</b>\n\n"
            "У вас пока нет созданных заявок на турниры."
        )
    else:
        text = "📋 <b>Ваши заявки на турниры</b>\n\n"
        for b in bookings:
            status_emoji = {
                "APPROVED": "🟢 Одобрен",
                "PENDING": "🟡 На согласовании",
                "REJECTED": "🔴 Отклонен",
                "CANCELLED": "⚪ Отменен",
            }.get(str(b.status), str(b.status))
            fmt = format_summary_label(b.event_format)
            text += (
                f"• <b>{b.title}</b> ({b.discipline})\n"
                f"  📅 {b.booking_date.strftime('%d.%m.%Y')} | {status_emoji}\n"
                f"  Формат: {fmt}\n\n"
            )

    buttons = [
        [InlineKeyboardButton(text="📅 Новая бронь", callback_data="tb:start")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="nav:tournaments")],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def build_admin_approval_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard sent to management channel for slot approval."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить слот", callback_data=f"tb_adm:approve:{booking_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"tb_adm:reject:{booking_id}"),
            ]
        ]
    )


def build_admin_approval_text(
    booking: TournamentBooking,
    creator: User,
    organizer_tag: str,
) -> str:
    """Builds formatted post for closed management topic/chat."""
    format_label = format_summary_label(booking.event_format)
    rulebook_info = (
        f"Ссылка: {booking.rulebook_url}"
        if booking.rulebook_url
        else ("Прикрепленный файл регламента (см. вложение)" if booking.rulebook_file_id else "Не указан")
    )
    email_str = creator.email or "Не указан"
    date_str = booking.booking_date.strftime("%d.%m.%Y")

    return (
        f"📅 <b>Бронь турнира: {booking.title}</b>\n\n"
        f"• <b>Организатор:</b> {organizer_tag} ({booking.discipline} Admin)\n"
        f"• <b>Email:</b> <code>{email_str}</code>\n"
        f"• <b>Дата:</b> <b>{date_str}</b>\n"
        f"• <b>Формат:</b> {format_label}\n"
        f"• <b>Регламент:</b> {rulebook_info}\n\n"
        "👉 <i>Выберите решение по бронированию даты:</i>"
    )
