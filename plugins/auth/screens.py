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
                    InlineKeyboardButton(text="🎓 Начать верификацию", callback_data="auth:start"),
                ],
                [
                    InlineKeyboardButton(text="🎫 Помощь / Саппорт", callback_data="nav:helpdesk"),
                ],
            ]
        )

    return Screen(text=text, reply_markup=keyboard)


def get_student_id_prompt_screen() -> Screen:
    """Prompt asking user to enter Student ID."""
    text = (
        "🎓 <b>Шаг 1 из 2: Student ID</b>\n\n"
        "Отправьте ваш 9-значный Student ID в этот чат (например: <code>210103001</code>).\n\n"
        "<i>💡 Ваше сообщение будет автоматически удалено сборщиком мусора, а экран обновится на месте.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="nav:back")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_barcode_prompt_screen(student_id: str) -> Screen:
    """Prompt asking user to enter Barcode from student card."""
    text = (
        f"💳 <b>Шаг 2 из 2: Штрих-код студенческого билета</b>\n\n"
        f"Student ID: <code>{student_id}</code> ✅\n\n"
        f"Теперь введите номер со штрих-кода вашей ID-карты AITU (от 6 до 16 цифр).\n\n"
        f"<i>💡 Сообщение будет мгновенно удалено для сохранения чистоты чата.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="auth:start")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_verification_success_screen(student_id: str, full_name: str) -> Screen:
    """Screen shown when student is successfully verified."""
    text = (
        f"🎉 <b>Верификация успешно пройдена!</b>\n\n"
        f"👤 Студент: <b>{full_name}</b>\n"
        f"🆔 Student ID: <code>{student_id}</code>\n"
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
        f"• Имя: <b>{user_data.get('full_name', 'Студент')}</b>\n"
        f"• Username: @{user_data.get('username') or 'не указан'}\n"
        f"• Student ID: <code>{user_data.get('student_id', '—')}</code>\n"
        f"• Штрих-код: <code>{user_data.get('barcode', '—')}</code>\n"
        f"• Статус: {'✅ Верифицирован' if user_data.get('is_verified') else '❌ Не верифицирован'}\n"
        f"• Роль: <b>{user_data.get('role', 'STUDENT')}</b>\n"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="nav:home")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)
