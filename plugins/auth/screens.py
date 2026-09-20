from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from common.dtos.screen import Screen


def get_welcome_screen(is_verified: bool = False, full_name: str = "") -> Screen:
    """Home / Welcome screen."""
    if is_verified:
        text = (
            f"🎮 <b>AITU Gaming Hub</b>\n\n"
            f"С возвращением, <b>{full_name}</b>!\n"
            f"Ваш аккаунт студента AITU верифицирован. Выберите раздел:"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🎮 Каталог дисциплин", callback_data="nav:disciplines"),
                ],
                [
                    InlineKeyboardButton(text="🏆 Турниры и киберспорт", callback_data="nav:tournaments"),
                ],
                [
                    InlineKeyboardButton(text="⛏️ Minecraft Сервер", callback_data="nav:minecraft"),
                ],
                [
                    InlineKeyboardButton(text="🎫 Служба поддержки", callback_data="nav:helpdesk"),
                ],
                [
                    InlineKeyboardButton(text="👤 Мой профиль", callback_data="auth:profile"),
                ],
            ]
        )
    else:
        text = (
            "🎮 <b>AITU Gaming Hub</b>\n\n"
            "Добро пожаловать в единую киберспортивную платформу Astana IT University!\n\n"
            "⚠️ <b>Требуется верификация:</b>\n"
            "Для доступа к серверам и турнирам необходимо подтвердить статус студента AITU."
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🎓 Начать регистрацию", callback_data="auth:start"),
                ],
                [
                    InlineKeyboardButton(text="🎮 Каталог дисциплин", callback_data="nav:disciplines"),
                ],
                [
                    InlineKeyboardButton(text="🎫 Помощь / Саппорт", callback_data="nav:helpdesk"),
                ],
            ]
        )

    return Screen(text=text, reply_markup=keyboard)


def get_first_name_prompt_screen() -> Screen:
    """Step 1: First Name"""
    text = (
        "📝 <b>Шаг 1 из 6: Имя</b>\n\n"
        "Пожалуйста, отправьте ваше <b>Имя</b> в этот чат.\n\n"
        "<i>💡 Ваше сообщение будет автоматически удалено, а экран обновится на месте.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_last_name_prompt_screen(first_name: str) -> Screen:
    """Step 2: Last Name"""
    text = (
        f"📝 <b>Шаг 2 из 6: Фамилия</b>\n\n"
        f"Имя: <b>{first_name}</b> ✅\n\n"
        f"Теперь отправьте вашу <b>Фамилию</b>.\n"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_barcode_prompt_screen(first_name: str, last_name: str) -> Screen:
    """Step 3: Barcode"""
    text = (
        f"💳 <b>Шаг 3 из 6: Штрих-код студенческого билета</b>\n\n"
        f"ФИО: <b>{first_name} {last_name}</b> ✅\n\n"
        f"Введите 6-значный <b>Bar-Code</b> с вашей ID-карты.\n"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_phone_prompt_screen(barcode: str) -> Screen:
    """Step 4: Phone Number"""
    text = (
        f"📱 <b>Шаг 4 из 6: Номер телефона</b>\n\n"
        f"Bar-Code: <code>{barcode}</code> ✅\n\n"
        f"Введите ваш <b>Номер телефона</b>.\n"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_email_prompt_screen(phone: str) -> Screen:
    """Step 5: Email"""
    text = (
        f"📧 <b>Шаг 5 из 6: Email почта</b>\n\n"
        f"Телефон: <code>{phone}</code> ✅\n\n"
        f"Введите ваш <b>Email адрес</b>.\n"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_group_prompt_screen(email: str) -> Screen:
    """Step 6: Academic Group"""
    text = (
        f"🎓 <b>Шаг 6 из 6: Академическая группа</b>\n\n"
        f"Email: <code>{email}</code> ✅\n\n"
        f"Введите вашу <b>Академическую группу</b>.\n"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)



def get_verification_success_screen(full_name: str, barcode: str, group: str) -> Screen:
    """Screen shown when student is successfully verified."""
    text = (
        f"🎉 <b>Регистрация успешно пройдена!</b>\n\n"
        f"👤 Студент: <b>{full_name}</b>\n"
        f"🎓 Группа: <b>{group}</b>\n"
        f"💳 Bar-Code: <code>{barcode}</code>\n"
        f"🔰 Роль: <b>Студент AITU</b>\n\n"
        f"Теперь вам открыт доступ к серверу Minecraft, регистрации на турниры и другим сервисам!"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⛏️ Перейти в Minecraft", callback_data="nav:minecraft")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_profile_screen(user_data: dict) -> Screen:
    """Profile details screen."""
    text = (
        f"👤 <b>Профиль студента AITU</b>\n\n"
        f"• Имя: <b>{user_data.get('first_name', '—')}</b>\n"
        f"• Фамилия: <b>{user_data.get('last_name', '—')}</b>\n"
        f"• Группа: <b>{user_data.get('academic_group', '—')}</b>\n"
        f"• Bar-Code: <code>{user_data.get('barcode', '—')}</code>\n"
        f"• Телефон: <code>{user_data.get('phone_number', '—')}</code>\n"
        f"• Email: <code>{user_data.get('email', '—')}</code>\n"
        f"• Username: @{user_data.get('username') or 'не указан'}\n"
        f"• Статус: {'✅ Верифицирован' if user_data.get('is_verified') else '❌ Не верифицирован'}\n"
        f"• Роль: <b>{user_data.get('role', 'STUDENT')}</b>\n"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)
