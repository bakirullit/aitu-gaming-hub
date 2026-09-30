import math
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from common.config import settings
from common.dtos.screen import Screen


def get_minecraft_home_screen(
    linked_nick: str | None = None,
    online: int = 14,
    max_players: int = 50,
    server_ip: str | None = None,
) -> Screen:
    """
    Minecraft Discipline Hub Dashboard screen.
    Menu:
    [ 🌐 Сервера ]        [ 👤 Профиль ]
    [ 👥 Друзья ]         [ 📢 Канал дисциплины ]
    [ ⬅ Назад в дисциплины ]
    """
    addr = server_ip or settings.MINECRAFT_SERVER_IP
    if linked_nick:
        nick_info = f"<code>{linked_nick}</code> (Вайтлист активен ✅)"
    else:
        nick_info = "<i>Не привязан ⚠️</i>"

    text = (
        "⛏️ <b>AITU Minecraft Community Server</b>\n\n"
        "Официальный сервер киберспортивного клуба Astana IT University.\n"
        "Добро пожаловать в игровое пространство <b>AITU SMP</b>!\n\n"
        f"• <b>Minecraft Никнейм:</b> {nick_info}\n"
        f"• <b>Статус сервера:</b> 🟢 Онлайн (<code>{online} / {max_players} игроков</code>)\n"
        f"• <b>Адрес:</b> <code>{addr}</code>\n\n"
        "Выберите интересующий раздел:"
    )

    buttons = [
        [
            InlineKeyboardButton(text="🌐 Сервера", callback_data="cb_mc_servers"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="cb_mc_profile"),
        ],
        [
            InlineKeyboardButton(text="👥 Друзья", callback_data="cb_mc_friends"),
            InlineKeyboardButton(text="📢 Канал дисциплины", callback_data="cb_mc_channel"),
        ],
        [
            InlineKeyboardButton(text="⬅ Назад в дисциплины", callback_data="nav:disciplines"),
        ],
    ]

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_minecraft_servers_screen(
    server_name: str,
    version: str,
    online: int,
    max_players: int,
    address: str,
    motd: str,
    modpack_url: str,
) -> Screen:
    """Submodule A: 🌐 Сервера screen."""
    text = (
        "🌐 <b>Игровые сервера AITU Minecraft</b>\n\n"
        f"• <b>Название:</b> <b>{server_name}</b>\n"
        f"• <b>Версия:</b> <code>{version}</code> (Java Edition)\n"
        f"• <b>Статус:</b> 🟢 Online (<code>{online} / {max_players} игроков</code>)\n"
        f"• <b>Адрес для входа:</b> <code>{address}</code>\n"
        f"• <b>Описание:</b> <i>{motd}</i>\n\n"
        "<i>Для подключения к серверу необходим официальный модпак клуба.</i>"
    )

    buttons = [
        [
            InlineKeyboardButton(text="📋 Скопировать IP", callback_data="mc:copy_ip"),
        ],
        [
            InlineKeyboardButton(text="📦 Скачать модпак / Клиент", url=modpack_url),
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить статус", callback_data="cb_mc_servers"),
        ],
        [
            InlineKeyboardButton(text="⬅ Назад", callback_data="nav:minecraft"),
        ],
    ]

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_minecraft_profile_screen(
    nickname: str | None,
    username: str | None,
    telegram_id: int,
    has_active_session: bool,
) -> Screen:
    """Submodule B: 👤 Профиль игрока screen."""
    if nickname:
        acc_status = "✅ Привязан"
        nick_display = f"<code>{nickname}</code>"
    else:
        acc_status = "⚠️ Не привязан"
        nick_display = "<i>Не установлен</i>"

    if username:
        tg_display = f"@{username} (ID: <code>{telegram_id}</code>)"
    else:
        tg_display = f"ID: <code>{telegram_id}</code>"

    mod_status = "🟢 Активная сессия" if has_active_session else "⚪ Не активен"

    text = (
        "👤 <b>Профиль игрока Minecraft</b>\n\n"
        f"• <b>Статус аккаунта:</b> {acc_status}\n"
        f"• <b>Minecraft Никнейм:</b> {nick_display}\n"
        f"• <b>Telegram:</b> {tg_display}\n"
        f"• <b>Статус мода:</b> {mod_status}\n\n"
        "<i>Используйте кнопки ниже для настройки вашего профиля, привязки никнейма и получения кода для входа через клиентский мод:</i>"
    )

    buttons = [
        [
            InlineKeyboardButton(text="✏ Сменить никнейм", callback_data="mc:change_nick"),
        ],
        [
            InlineKeyboardButton(text="🔑 Сгенерировать код для входа", callback_data="mc:gen_code"),
        ],
        [
            InlineKeyboardButton(text="🔓 Отвязать аккаунт", callback_data="mc:unlink"),
        ],
        [
            InlineKeyboardButton(text="⬅ Назад", callback_data="nav:minecraft"),
        ],
    ]

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_minecraft_code_screen(pin: str, nickname: str) -> Screen:
    """Display generated 6-digit PIN code."""
    text = (
        "🔑 <b>Код авторизации для Minecraft клиента</b>\n\n"
        f"Ваш одноразовый PIN-код:\n"
        f"<code>{pin}</code>\n\n"
        f"• Никнейм: <code>{nickname}</code>\n"
        "• Срок действия: <b>3 минуты</b>\n\n"
        "<i>Откройте Minecraft с установленным модом AITU Auth и введите этот код для входа.</i>"
    )

    buttons = [
        [
            InlineKeyboardButton(text="🔄 Сгенерировать новый код", callback_data="mc:gen_code"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад в профиль", callback_data="cb_mc_profile"),
        ],
    ]

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_nickname_prompt_screen() -> Screen:
    """Prompt asking user to enter their Java Edition nickname."""
    text = (
        "✏️ <b>Привязка / смена никнейма Minecraft</b>\n\n"
        "Отправьте ваш игровой никнейм в Minecraft Java Edition (от 3 до 16 символов, только английские буквы, цифры и _).\n\n"
        "Пример: <code>Steve_AITU</code>\n\n"
        "<i>💡 Никнейм будет автоматически добавлен в вайтлист сервера и синхронизирован с клиентом.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="cb_mc_profile")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


get_minecraft_prompt_nickname_screen = get_nickname_prompt_screen


def get_whitelist_success_screen(nickname: str, rcon_response: str) -> Screen:
    """Screen shown upon successful whitelist addition."""
    text = (
        "🎉 <b>Никнейм успешно привязан и добавлен в вайтлист!</b>\n\n"
        f"• Никнейм: <code>{nickname}</code>\n"
        f"• Ответ сервера: <i>{rcon_response}</i>\n"
        f"• IP для подключения: <code>{settings.MINECRAFT_SERVER_IP}</code>\n\n"
        "Приятной игры на сервере AITU!"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 В профиль", callback_data="cb_mc_profile")],
            [InlineKeyboardButton(text="◀️ Меню Minecraft", callback_data="nav:minecraft")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_minecraft_friends_hub_screen(
    total_friends: int,
    online_friends: int,
    pending_requests_count: int,
) -> Screen:
    """Submodule C: 👥 Друзья hub screen."""
    text = (
        "👥 <b>Друзья Minecraft</b>\n\n"
        f"• <b>Всего друзей:</b> <code>{total_friends}</code>\n"
        f"• <b>В сети:</b> 🟢 <code>{online_friends}</code>\n"
        f"• <b>Входящие заявки:</b> 📬 <code>{pending_requests_count}</code>\n\n"
        "<i>Играйте вместе на сервере AITU SMP, находите тиммейтов и отслеживайте друзей онлайн прямо из мода или бота!</i>"
    )

    buttons = [
        [
            InlineKeyboardButton(text="📜 Список друзей", callback_data="mc:friends_list"),
            InlineKeyboardButton(text="➕ Добавить друга", callback_data="mc:add_friend"),
        ],
        [
            InlineKeyboardButton(text=f"📥 Заявки ({pending_requests_count})", callback_data="mc:friend_requests"),
        ],
        [
            InlineKeyboardButton(text="⬅ Назад", callback_data="nav:minecraft"),
        ],
    ]

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def get_minecraft_friends_list_screen(
    friends: list[dict],
    page: int = 1,
    page_size: int = 5,
) -> Screen:
    """Paginated friends list screen."""
    total_items = len(friends)
    total_pages = max(1, math.ceil(total_items / page_size))
    current_page = max(1, min(page, total_pages))

    start_idx = (current_page - 1) * page_size
    slice_items = friends[start_idx:start_idx + page_size]

    if not friends:
        body = "<i>У вас пока нет добавленных друзей. Нажмите «➕ Добавить друга», чтобы найти тиммейтов!</i>\n"
    else:
        lines = []
        for f in slice_items:
            nick = f.get("nickname", "Player")
            tag = f.get("telegram_tag", "@user")
            is_online = f.get("is_online", False)
            status_icon = "🟢" if is_online else "⚪"
            status_desc = "В сети" if is_online else "Не в сети"
            lines.append(f"• {status_icon} <b>{nick}</b> ({tag}) — <i>{status_desc}</i>")
        body = "\n".join(lines) + "\n"

    text = (
        "📜 <b>Список друзей Minecraft</b>\n\n"
        f"{body}\n"
        f"Страница: <b>{current_page} из {total_pages}</b> (Всего: {total_items})"
    )

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    # Pagination buttons if multiple pages
    if total_pages > 1:
        prev_page = current_page - 1 if current_page > 1 else total_pages
        next_page = current_page + 1 if current_page < total_pages else 1
        keyboard_rows.append([
            InlineKeyboardButton(text="⬅️", callback_data=f"mc:friends_list:{prev_page}"),
            InlineKeyboardButton(text=f"· {current_page}/{total_pages} ·", callback_data="mc:noop"),
            InlineKeyboardButton(text="➡️", callback_data=f"mc:friends_list:{next_page}"),
        ])

    keyboard_rows.append([
        InlineKeyboardButton(text="➕ Добавить друга", callback_data="mc:add_friend"),
        InlineKeyboardButton(text="⬅ Назад к друзьям", callback_data="cb_mc_friends"),
    ])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))


def get_minecraft_add_friend_prompt_screen() -> Screen:
    """Prompt for friend username or nickname."""
    text = (
        "➕ <b>Добавление друга в Minecraft</b>\n\n"
        "Отправьте <b>@username</b> в Telegram или <b>Minecraft никнейм</b> вашего друга.\n\n"
        "Пример: <code>@alex_aitu</code> или <code>Alex_Crafter</code>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="cb_mc_friends")],
        ]
    )
    return Screen(text=text, reply_markup=keyboard)


def get_minecraft_friend_requests_screen(requests: list[dict]) -> Screen:
    """Incoming friend requests screen with accept / decline actions."""
    if not requests:
        text = (
            "📥 <b>Входящие заявки в друзья</b>\n\n"
            "<i>У вас нет ожидающих заявок в друзья.</i>"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад к друзьям", callback_data="cb_mc_friends")],
            ]
        )
        return Screen(text=text, reply_markup=keyboard)

    req_lines = [f"• <b>{r.get('from_nickname', 'Player')}</b> ({r.get('from_tag', '@user')})" for r in requests]
    text = (
        "📥 <b>Входящие заявки в друзья</b>\n\n"
        + "\n".join(req_lines)
        + "\n\nВыберите действие для каждой заявки:"
    )

    keyboard_rows: list[list[InlineKeyboardButton]] = []
    for req in requests:
        req_id = req["id"]
        from_nick = req.get("from_nickname", "Player")
        from_tag = req.get("from_tag", "@user")

        keyboard_rows.append([
            InlineKeyboardButton(text=f"👤 {from_nick} ({from_tag})", callback_data="mc:noop"),
        ])
        keyboard_rows.append([
            InlineKeyboardButton(text="✔ Принять", callback_data=f"mc:accept_req:{req_id}"),
            InlineKeyboardButton(text="✖ Отклонить", callback_data=f"mc:decline_req:{req_id}"),
        ])

    keyboard_rows.append([
        InlineKeyboardButton(text="⬅ Назад к друзьям", callback_data="cb_mc_friends"),
    ])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))


def get_minecraft_channel_screen(channel_url: str, chat_url: str) -> Screen:
    """Submodule D: 📢 Канал дисциплины screen."""
    text = (
        "📢 <b>Канал и чат дисциплины Minecraft</b>\n\n"
        "Присоединяйтесь к официальному сообществу <b>AITU Minecraft</b>:\n\n"
        "• Анонсы турниров, вайпов и технических работ\n"
        "• Голосования за новые моды и датапаки\n"
        "• Конкурсы лучших построек и призовые ивенты\n"
        "• Общение с куратором и поиск тиммейтов\n\n"
        "Нажмите кнопку ниже, чтобы перейти:"
    )

    buttons = [
        [
            InlineKeyboardButton(text="🔗 Перейти в канал", url=channel_url),
        ],
        [
            InlineKeyboardButton(text="💬 Чат игроков", url=chat_url),
        ],
        [
            InlineKeyboardButton(text="⬅ Назад", callback_data="nav:minecraft"),
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
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="cb_mc_servers")],
            [InlineKeyboardButton(text="◀️ Назад в Minecraft", callback_data="nav:minecraft")],
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
            [InlineKeyboardButton(text="🔄 Повторить попытку", callback_data="cb_mc_servers")],
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
