from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from common.dtos.screen import Screen
from common.models.user import User


def get_club_info_screen() -> Screen:
    """Screen: About AITU Gaming club for new users with 'Пройти регистрацию' button."""
    text = (
        "🎮 <b>Добро пожаловать в AITU Gaming Hub!</b>\n\n"
        "<b>AITU Gaming</b> — официальное киберспортивное сообщество Astana IT University. "
        "Мы объединяем студентов, проводим турниры по CS2, Dota 2, Valorant, PUBG, FIFA, "
        "а также развиваем собственный сервер Minecraft!\n\n"
        "✨ <b>Что дает регистрация:</b>\n"
        "• Участие в студенческих и открытых турнирах с призовыми фондами\n"
        "• Доступ к серверам и академическому комьюнити\n"
        "• Личный игровой профиль и рейтинг дисциплин\n\n"
        "Чтобы начать пользоваться платформой, пройдите быструю регистрацию 👇"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Пройти регистрацию", callback_data="auth:start_reg"),
            ],
            [
                InlineKeyboardButton(text="🎮 Каталог дисциплин", callback_data="nav:disciplines"),
            ],
            [
                InlineKeyboardButton(text="🎫 Служба поддержки", callback_data="nav:helpdesk"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_choose_role_screen() -> Screen:
    """State: CHOOSE_ROLE - Select status: Guest, Student, Staff."""
    text = (
        "👤 <b>Выберите ваш статус:</b>\n\n"
        "Пожалуйста, укажите ваш статус для настройки профиля:\n\n"
        "🎓 <b>Студент AITU</b>\n"
        "— Для действующих студентов университета\n"
        "— Доступ ко всем закрытым турнирам и кампусному серверу Minecraft\n"
        "— Требуется баркод студенческого билета\n\n"
        "🎮 <b>Гость</b>\n"
        "— Для гостей, выпускников и участников открытых соревнований\n"
        "— Быстрая регистрация (привязка Steam повышает до <i>Verified Guest</i>)\n\n"
        "🛡️ <b>Staff AITU Gaming</b>\n"
        "— Для организаторов и руководства клуба"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎓 Студент AITU", callback_data="auth:role:student"),
            ],
            [
                InlineKeyboardButton(text="🎮 Гость", callback_data="auth:role:guest"),
            ],
            [
                InlineKeyboardButton(text="🛡️ Staff AITU Gaming", callback_data="auth:role:staff"),
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="nav:home"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_staff_closed_screen() -> Screen:
    """Screen shown when Staff registration is selected."""
    text = (
        "⛔ <b>Регистрация Staff закрыта</b>\n\n"
        "Регистрация в роли организатора или судьи AITU Gaming производится "
        "исключительно через главного администратора клуба.\n\n"
        "Пожалуйста, обратитесь в службу поддержки или выберите другой статус."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="auth:start_reg"),
            ],
            [
                InlineKeyboardButton(text="🎫 Написать в саппорт", callback_data="nav:helpdesk"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_full_name_screen() -> Screen:
    """State: INPUT_FULL_NAME - Prompt for full name."""
    text = (
        "📝 <b>Введите ФИО</b>\n\n"
        "Отправьте ваше <b>Имя и Фамилию</b> ответным сообщением в чат.\n\n"
        "⚠️ <i>Требования: минимум 2 слова, только буквы.</i>\n"
        "<i>Пример: Алихан Болатов</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Отмена", callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_phone_screen(full_name: str) -> Screen:
    """State: INPUT_PHONE - Prompt for phone number with contact button info."""
    text = (
        "📱 <b>Отправьте номер телефона</b>\n\n"
        f"ФИО: <b>{full_name}</b> ✅\n\n"
        "Нажмите кнопку <b>«Поделиться контактом»</b> внизу экрана или "
        "напишите номер вручную в международном формате E.164 (например, <code>+77011234567</code>):"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Отмена", callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_phone_reply_keyboard() -> ReplyKeyboardMarkup:
    """Reply markup with Share Contact button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📱 Поделиться контактом", request_contact=True),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_gmail_screen(full_name: str, phone: str) -> Screen:
    """State: INPUT_GMAIL - Prompt for Google email strictly @gmail.com."""
    text = (
        "📧 <b>Введите личную почту Google (@gmail.com)</b>\n\n"
        f"ФИО: <b>{full_name}</b> ✅\n"
        f"Телефон: <code>{phone}</code> ✅\n\n"
        "Введите адрес электронной почты Google.\n"
        "⚠️ <i>Домен строго: <code>@gmail.com</code></i>\n\n"
        "<i>Пример: student.aitu@gmail.com</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Отмена", callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_barcode_screen(full_name: str) -> Screen:
    """State: INPUT_BARCODE - Prompt for 6-digit student barcode."""
    text = (
        "💳 <b>Введите ваш баркод (ID студента)</b>\n\n"
        f"Студент: <b>{full_name}</b> ✅\n\n"
        "Введите 6 цифр штрих-кода с вашей студенческой ID-карты Astana IT University.\n"
        "<i>Пример: 230101</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Отмена", callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_otp_screen(barcode: str) -> Screen:
    """State: INPUT_OTP - Prompt for 6-digit confirmation code."""
    text = (
        "🔐 <b>Введите код подтверждения из письма</b>\n\n"
        f"Письмо с 6-значным кодом отправлено на ваш университетский адрес:\n"
        f"<code>{barcode}@astanait.edu.kz</code>\n\n"
        "⏱ Код действителен в течение <b>5 минут</b> (до 3 попыток ввода).\n"
        "Отправьте полученный код в чат:"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Отправить код повторно", callback_data=f"auth:otp:resend:{barcode}"),
            ],
            [
                InlineKeyboardButton(text="🚫 Отмена", callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_steam_screen() -> Screen:
    """State: INPUT_STEAM - Prompt for Steam profile URL or raw SteamID64 with Skip button."""
    text = (
        "🎮 <b>Привяжите Steam для верификации</b>\n\n"
        "Привязка Steam профиля позволяет получить статус <b>Verified Guest</b> "
        "и участвовать в открытых турнирах клуба!\n\n"
        "Отправьте ссылку на ваш Steam профиль или SteamID64:\n"
        "• <code>https://steamcommunity.com/id/custom_url</code>\n"
        "• <code>https://steamcommunity.com/profiles/76561198000000000</code>\n"
        "• Или чистый 17-значный SteamID64: <code>76561198000000000</code>\n\n"
        "<i>Вы также можете пропустить этот шаг и привязать Steam позже.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏭️ Пропустить", callback_data="auth:steam:skip"),
            ],
            [
                InlineKeyboardButton(text="🚫 Отмена", callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_registration_cancelled_screen() -> Screen:
    """Screen: Registration Cancelled."""
    text = (
        "❌ <b>Регистрация отменена</b>\n\n"
        "Все введенные данные были сброшены. Вы можете начать процесс заново в любое удобное время."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Пройти регистрацию", callback_data="auth:start_reg"),
            ],
            [
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="nav:home"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_authorized_menu_screen(
    full_name: str,
    role: str = "guest",
    is_verified: bool = False,
    has_steam: bool = False,
) -> Screen:
    """Screen: Main Club Menu (Authorized)."""
    role_norm = role.lower() if role else "guest"

    if is_verified or role_norm in ["student", "staff", "admin", "discipline_admin", "head_admin"]:
        status_label = "Студент AITU 🎓"
    elif role_norm == "verified_guest":
        status_label = "Verified Guest 🛡️"
    else:
        status_label = "Гость (Guest) 👤"

    text = (
        f"🎮 <b>AITU Gaming Hub — Главное меню</b>\n\n"
        f"Добро пожаловать, <b>{full_name or 'Игрок'}</b>!\n"
        f"Статус аккаунта: <b>{status_label}</b>\n\n"
        f"Выберите раздел:"
    )

    buttons = [
        [
            InlineKeyboardButton(text="🎮 Каталог дисциплин", callback_data="nav:disciplines"),
        ],
        [
            InlineKeyboardButton(text="🏆 Турниры и киберспорт", callback_data="nav:tournaments"),
        ],
    ]

    # Minecraft button is available for verified students
    if is_verified or role_norm in ["student", "staff", "admin", "discipline_admin", "head_admin"]:
        buttons.append([
            InlineKeyboardButton(text="⛏️ Minecraft Сервер", callback_data="nav:minecraft"),
        ])

    buttons.append([
        InlineKeyboardButton(text="👤 Мой профиль", callback_data="auth:profile"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🎫 Служба поддержки", callback_data="nav:helpdesk"),
    ])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_profile_screen(user_data: dict) -> Screen:
    """Profile details screen."""
    role_val = str(user_data.get("role", "guest")).lower()
    if role_val in ["student", "staff", "admin", "discipline_admin", "head_admin"]:
        role_title = "Студент AITU 🎓"
    elif role_val == "verified_guest":
        role_title = "Verified Guest 🛡️"
    else:
        role_title = "Гость (Guest) 👤"

    fname = user_data.get("full_name") or f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip() or "—"
    steam_val = user_data.get("steam_id") or "Не привязан"
    barcode_val = user_data.get("barcode") or "—"

    text = (
        f"👤 <b>Профиль игрока</b>\n\n"
        f"• ФИО: <b>{fname}</b>\n"
        f"• Username: @{user_data.get('username') or 'не указан'}\n"
        f"• Телефон: <code>{user_data.get('phone_number', '—')}</code>\n"
        f"• Gmail: <code>{user_data.get('email', '—')}</code>\n"
        f"• Bar-Code: <code>{barcode_val}</code>\n"
        f"• Steam ID: <code>{steam_val}</code>\n"
        f"• Роль: <b>{role_title}</b>\n"
    )

    buttons = []
    if not user_data.get("steam_id"):
        buttons.append([InlineKeyboardButton(text="🎮 Привязать Steam", callback_data="auth:profile:link_steam")])
    if role_val in ["guest", "verified_guest"]:
        buttons.append([InlineKeyboardButton(text="🎓 Верифицировать студента AITU", callback_data="auth:profile:upgrade_student")])
    buttons.append([InlineKeyboardButton(text="◀️ В главное меню", callback_data="nav:home")])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


# Backward compatibility aliases
get_welcome_screen = get_authorized_menu_screen


def get_first_name_prompt_screen() -> Screen:
    return Screen(text="📝 Введите ваше Имя:\n", reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


def get_last_name_prompt_screen(first_name: str = "") -> Screen:
    return Screen(text=f"📝 Имя: {first_name} ✅\nТеперь введите Фамилию:\n", reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


def get_barcode_prompt_screen(*args, **kwargs) -> Screen:
    full_name = " ".join(str(a) for a in args if a) or "Студент"
    return get_barcode_screen(full_name=full_name)


def get_phone_prompt_screen(*args, **kwargs) -> Screen:
    full_name = " ".join(str(a) for a in args if a) or "Пользователь"
    return get_phone_screen(full_name=full_name)


def get_email_prompt_screen(phone: str = "") -> Screen:
    return Screen(text=f"📧 Телефон: {phone} ✅\nВведите email:\n", reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


def get_group_prompt_screen(email: str = "") -> Screen:
    return Screen(text=f"🎓 Email: {email} ✅\nВведите группу:\n", reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


def get_verification_success_screen(full_name: str = "", barcode: str = "", group: str = "") -> Screen:
    text = (
        f"🎉 <b>Студенческая верификация успешно пройдена!</b>\n\n"
        f"👤 Студент: <b>{full_name}</b>\n"
        f"💳 Bar-Code: <code>{barcode}</code>\n"
        f"🔰 Роль: <b>Студент AITU</b> ✅"
    )
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


