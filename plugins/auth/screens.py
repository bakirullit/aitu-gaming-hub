from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from common.dtos.screen import Screen
from common.models.user import User
from common.texts import get_text


def get_club_info_screen() -> Screen:
    """Screen: About AITU Gaming club for new users with 'Пройти регистрацию' button."""
    text = get_text("auth.club_info.text")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("auth.club_info.buttons.start_reg"), callback_data="auth:start_reg"),
            ],
            [
                InlineKeyboardButton(text=get_text("auth.club_info.buttons.disciplines"), callback_data="nav:disciplines"),
            ],
            [
                InlineKeyboardButton(text=get_text("auth.club_info.buttons.helpdesk"), callback_data="nav:helpdesk"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_choose_role_screen() -> Screen:
    """State: CHOOSE_ROLE - Select status: Guest, Student, Staff."""
    text = get_text("auth.choose_role.text")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("auth.choose_role.buttons.student"), callback_data="auth:role:student"),
            ],
            [
                InlineKeyboardButton(text=get_text("auth.choose_role.buttons.guest"), callback_data="auth:role:guest"),
            ],
            [
                InlineKeyboardButton(text=get_text("auth.choose_role.buttons.staff"), callback_data="auth:role:staff"),
            ],
            [
                InlineKeyboardButton(text=get_text("auth.choose_role.buttons.back"), callback_data="nav:home"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_staff_closed_screen() -> Screen:
    """Screen shown when Staff registration is selected."""
    text = get_text("auth.staff_closed.text")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("auth.staff_closed.buttons.back"), callback_data="auth:start_reg"),
            ],
            [
                InlineKeyboardButton(text=get_text("auth.staff_closed.buttons.helpdesk"), callback_data="nav:helpdesk"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_full_name_screen() -> Screen:
    """State: INPUT_FULL_NAME - Prompt for full name."""
    text = get_text("auth.full_name.text")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("auth.full_name.buttons.cancel"), callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_phone_screen(full_name: str) -> Screen:
    """State: INPUT_PHONE - Prompt for phone number with contact button info."""
    text = get_text("auth.phone.text", full_name=full_name)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("auth.phone.buttons.cancel"), callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_phone_reply_keyboard() -> ReplyKeyboardMarkup:
    """Reply markup with Share Contact button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_text("auth.phone.buttons.share_contact"), request_contact=True),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_gmail_screen(full_name: str, phone: str) -> Screen:
    """State: INPUT_GMAIL - Prompt for Google email strictly @gmail.com."""
    text = get_text("auth.gmail.text", full_name=full_name, phone=phone)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("auth.gmail.buttons.cancel"), callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_barcode_screen(full_name: str) -> Screen:
    """State: INPUT_BARCODE - Prompt for 6-digit student barcode."""
    text = get_text("auth.barcode.text", full_name=full_name)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("auth.barcode.buttons.cancel"), callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_otp_screen(barcode: str, target_email: str | None = None) -> Screen:
    """State: INPUT_OTP - Prompt for 6-digit confirmation code."""
    email_destination = target_email or f"{barcode}@astanait.edu.kz"
    text = get_text("auth.otp.text", email_destination=email_destination)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("auth.otp.buttons.resend"), callback_data=f"auth:otp:resend:{barcode}"),
            ],
            [
                InlineKeyboardButton(text=get_text("auth.otp.buttons.cancel"), callback_data="auth:cancel"),
            ],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_steam_screen(
    steam_auth_url: str = "",
    is_registration: bool = True,
    use_web_app: bool = True,
) -> Screen:
    """State: INPUT_STEAM - Official Steam OpenID 2.0 authorization screen via Telegram Mini App."""
    text = get_text("auth.steam.text")
    buttons = []
    if steam_auth_url:
        if use_web_app:
            buttons.append([
                InlineKeyboardButton(
                    text=get_text("auth.steam.buttons.link_steam"),
                    web_app=WebAppInfo(url=steam_auth_url),
                ),
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    text=get_text("auth.steam.buttons.login_steam"),
                    url=steam_auth_url,
                ),
            ])

    bottom_row = []
    if is_registration:
        bottom_row.append(InlineKeyboardButton(text=get_text("auth.steam.buttons.skip"), callback_data="auth:steam:skip"))
        bottom_row.append(InlineKeyboardButton(text=get_text("auth.steam.buttons.cancel"), callback_data="auth:cancel"))
    else:
        bottom_row.append(InlineKeyboardButton(text=get_text("auth.steam.buttons.to_profile"), callback_data="auth:profile"))

    if bottom_row:
        buttons.append(bottom_row)

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_registration_cancelled_screen() -> Screen:
    """Screen: Registration Cancelled."""
    text = get_text("auth.registration_cancelled.text")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("auth.registration_cancelled.buttons.start_reg"), callback_data="auth:start_reg"),
            ],
            [
                InlineKeyboardButton(text=get_text("auth.registration_cancelled.buttons.main_menu"), callback_data="nav:home"),
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
        status_label = get_text("auth.menu.roles.student", default="Студент AITU 🎓")
    elif role_norm == "verified_guest":
        status_label = get_text("auth.menu.roles.verified_guest", default="Verified Guest 🛡️")
    else:
        status_label = get_text("auth.menu.roles.guest", default="Гость (Guest) 👤")

    text = get_text("auth.menu.text", full_name=full_name or "Игрок", status_label=status_label)

    buttons = [
        [
            InlineKeyboardButton(text=get_text("auth.menu.buttons.disciplines"), callback_data="nav:disciplines"),
        ],
        [
            InlineKeyboardButton(text=get_text("auth.menu.buttons.tournaments"), callback_data="nav:tournaments"),
        ],
    ]

    # Minecraft button is available for verified students
    if is_verified or role_norm in ["student", "staff", "admin", "discipline_admin", "head_admin"]:
        buttons.append([
            InlineKeyboardButton(text=get_text("auth.menu.buttons.minecraft"), callback_data="nav:minecraft"),
        ])

    buttons.append([
        InlineKeyboardButton(text=get_text("auth.menu.buttons.profile"), callback_data="auth:profile"),
    ])
    buttons.append([
        InlineKeyboardButton(text=get_text("auth.menu.buttons.helpdesk"), callback_data="nav:helpdesk"),
    ])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_profile_screen(user_data: dict) -> Screen:
    """Profile details screen."""
    role_val = str(user_data.get("role", "guest")).lower()
    if role_val in ["student", "staff", "admin", "discipline_admin", "head_admin"]:
        role_title = get_text("auth.menu.roles.student", default="Студент AITU 🎓")
    elif role_val == "verified_guest":
        role_title = get_text("auth.menu.roles.verified_guest", default="Verified Guest 🛡️")
    else:
        role_title = get_text("auth.menu.roles.guest", default="Гость (Guest) 👤")

    fname = user_data.get("full_name") or f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip() or "—"
    steam_val = user_data.get("steam_id") or "Не привязан"
    barcode_val = user_data.get("barcode") or "—"
    username_val = user_data.get("username") or "не указан"

    text = get_text(
        "auth.profile.text",
        full_name=fname,
        username=username_val,
        phone=user_data.get("phone_number", "—"),
        email=user_data.get("email", "—"),
        barcode=barcode_val,
        steam_id=steam_val,
        role_title=role_title,
    )

    buttons = []
    if not user_data.get("steam_id"):
        buttons.append([InlineKeyboardButton(text=get_text("auth.profile.buttons.link_steam"), callback_data="auth:profile:link_steam")])
    if role_val in ["guest", "verified_guest"]:
        buttons.append([InlineKeyboardButton(text=get_text("auth.profile.buttons.verify_student"), callback_data="auth:profile:upgrade_student")])
    buttons.append([InlineKeyboardButton(text=get_text("auth.profile.buttons.delete_account"), callback_data="auth:profile:delete_account")])
    buttons.append([InlineKeyboardButton(text=get_text("auth.profile.buttons.main_menu"), callback_data="nav:home")])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_delete_account_confirm_screen(steam_id: str | None = None) -> Screen:
    """Confirmation screen before permanent account deletion."""
    if steam_id:
        steam_info = get_text("auth.delete_confirm.steam_info_saved", steam_id=steam_id)
    else:
        steam_info = get_text("auth.delete_confirm.steam_info_none")

    text = get_text("auth.delete_confirm.text", steam_info=steam_info)
    buttons = [
        [
            InlineKeyboardButton(
                text=get_text("auth.delete_confirm.buttons.confirm"),
                callback_data="auth:profile:delete_account:confirm",
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_text("auth.delete_confirm.buttons.cancel"),
                callback_data="auth:profile",
            ),
        ],
    ]
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_account_deleted_screen(steam_id: str | None = None) -> Screen:
    """Screen displayed after account has been deleted."""
    if steam_id:
        steam_info = get_text("auth.deleted.steam_info_saved", steam_id=steam_id)
    else:
        steam_info = ""

    text = get_text("auth.deleted.text", steam_info=steam_info)
    buttons = [
        [
            InlineKeyboardButton(text=get_text("auth.deleted.buttons.register"), callback_data="auth:start_reg"),
        ],
        [
            InlineKeyboardButton(text=get_text("auth.deleted.buttons.club_info"), callback_data="auth:club_info"),
        ],
    ]
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
    text = get_text(
        "auth.verification_success.text",
        full_name=full_name,
        barcode=barcode,
        group=group,
    )
    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
