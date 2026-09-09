from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from common.dtos.screen import Screen


def get_minecraft_home_screen(linked_nick: str | None = None) -> Screen:
    """Main Minecraft hub screen."""
    nick_info = f"<b>{linked_nick}</b> (Вайтлист активен ✅)" if linked_nick else "<i>Не привязан ⚠️</i>"
    text = (
        "⛏️ <b>AITU Minecraft Community Server</b>\n\n"
        "Официальный сервер киберспортивного клуба Astana IT University.\n"
        f"• Ваш никнейм: {nick_info}\n"
        f"• Версия: <b>Java Edition 1.21.x</b>\n"
        f"• IP адрес: <code>mc.aitu.edu.kz</code>\n\n"
        "Выберите действие:"
    )

    buttons = [
        [
            InlineKeyboardButton(text="📊 Статус сервера & Онлайн", callback_data="mc:status"),
        ],
        [
            InlineKeyboardButton(text="✍️ Привязать никнейм (Whitelist)", callback_data="mc:whitelist"),
        ],
        [
            InlineKeyboardButton(text="📜 Правила сервера", callback_data="mc:rules"),
        ],
        [
            InlineKeyboardButton(text="◀️ Главное меню", callback_data="nav:home"),
        ],
    ]

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_minecraft_status_screen(status_text: str) -> Screen:
    """Server status screen returning RCON player list and ping info."""
    text = (
        "📊 <b>Статус сервера Minecraft</b>\n\n"
        f"{status_text}\n\n"
        "<i>Информация обновлена в реальном времени через RCON.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="mc:status")],
            [InlineKeyboardButton(text="◀️ Назад в Minecraft", callback_data="nav:minecraft")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_nickname_prompt_screen() -> Screen:
    """Prompt asking user to enter their Java Edition nickname."""
    text = (
        "✍️ <b>Привязка никнейма Minecraft</b>\n\n"
        "Отправьте ваш игровой никнейм в Minecraft Java Edition (от 3 до 16 символов, английские буквы, цифры и _).\n\n"
        "Пример: <code>Steve_AITU</code>\n\n"
        "<i>💡 Ваше сообщение будет автоматически удалено, а никнейм мгновенно добавлен в вайтлист сервера.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="nav:minecraft")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_whitelist_success_screen(nickname: str, rcon_response: str) -> Screen:
    """Screen shown upon successful whitelist addition."""
    text = (
        "🎉 <b>Никнейм успешно привязан и добавлен в вайтлист!</b>\n\n"
        f"• Никнейм: <code>{nickname}</code>\n"
        f"• Ответ сервера: <i>{rcon_response}</i>\n"
        f"• IP для подключения: <code>mc.aitu.edu.kz</code>\n\n"
        "Приятной игры на сервере AITU!"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню Minecraft", callback_data="nav:minecraft")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_rcon_error_screen(error_detail: str) -> Screen:
    """Graceful failure screen when Minecraft server is offline or RCON timed out."""
    text = (
        "⚠️ <b>Сервер Minecraft временно недоступен</b>\n\n"
        "Не удалось связаться с игровым сервером в пределах лимита времени (3.0 сек).\n\n"
        f"<b>Причина:</b> <i>{error_detail}</i>\n\n"
        "Возможно, сервер перезагружается или проводятся техработы. Попробуйте снова через минуту."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Повторить попытку", callback_data="mc:status")],
            [InlineKeyboardButton(text="◀️ В меню Minecraft", callback_data="nav:minecraft")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_rules_screen() -> Screen:
    """Server rules and regulations screen."""
    text = (
        "📜 <b>Правила сервера AITU Minecraft</b>\n\n"
        "1. <b>Уважение:</b> запрещены оскорбления, буллинг и нецензурная лексика.\n"
        "2. <b>Честная игра:</b> любые чит-клиенты, X-Ray, макросы и боты строго запрещены (перманентный бан).\n"
        "3. <b>Гриферство:</b> запрещено разрушать чужие постройки и воровать ресурсы.\n"
        "4. <b>Нагрузка:</b> запрещены лаг-машины и бесконтрольное размножение мобов.\n"
        "5. <b>Один аккаунт:</b> одному студенту разрешен ровно один аккаунт в вайтлисте.\n\n"
        "<i>Нарушение правил ведет к блокировке в клубе и передаче информации куратору.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в Minecraft", callback_data="nav:minecraft")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)
