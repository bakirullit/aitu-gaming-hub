import math
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from common.dtos.screen import Screen
from common.models.discipline import Discipline, DisciplineTier

PAGE_SIZE = 6
DISCORD_INVITE_URL = "https://discord.gg/astanait"


def get_disciplines_catalog_screen(
    disciplines: list[Discipline],
    page: int = 1,
    page_size: int = PAGE_SIZE,
) -> Screen:
    """Dynamic paginated disciplines catalog with native non-shifting inline controls."""
    total_items = len(disciplines)
    total_pages = max(1, math.ceil(total_items / page_size))
    current_page = max(1, min(page, total_pages))

    start_idx = (current_page - 1) * page_size
    end_idx = start_idx + page_size
    slice_items = disciplines[start_idx:end_idx]

    text = (
        "🎮 <b>Каталог дисциплин AITU Gaming Hub</b>\n\n"
        "Выберите игровое направление, чтобы присоединиться к сообществу, "
        "узнать регламенты или связаться с куратором дисциплины.\n\n"
        f"📊 Всего активных направлений: <b>{total_items}</b>\n"
        f"📄 Страница: <b>{current_page} из {total_pages}</b>"
    )

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    # 1. Pinned top button: Discord community link
    keyboard_rows.append([
        InlineKeyboardButton(
            text="🌐 Наш Discord-сервер",
            url=DISCORD_INVITE_URL,
        )
    ])

    # 2. Middle grid: 2 columns of dynamic discipline buttons
    current_row: list[InlineKeyboardButton] = []
    for disc in slice_items:
        tier_icon = "🔥" if disc.tier == DisciplineTier.MAJOR else "⚡"
        btn = InlineKeyboardButton(
            text=f"{tier_icon} {disc.name}",
            callback_data=f"disc:view:{disc.slug}:{current_page}",
        )
        current_row.append(btn)
        if len(current_row) == 2:
            keyboard_rows.append(current_row)
            current_row = []

    if current_row:
        keyboard_rows.append(current_row)

    # 3. Bottom pagination row (3 buttons with native non-jumping layout)
    # Previous button
    if current_page > 1:
        prev_btn = InlineKeyboardButton(text="⬅️", callback_data=f"disc:page:{current_page - 1}")
    else:
        prev_btn = InlineKeyboardButton(text="⬅️", callback_data="disc:noop")

    # Center badge: Informational, non-clickable
    badge_btn = InlineKeyboardButton(
        text=f"· {current_page}/{total_pages} ·",
        callback_data="disc:noop",
    )

    # Next button
    if current_page < total_pages:
        next_btn = InlineKeyboardButton(text="➡️", callback_data=f"disc:page:{current_page + 1}")
    else:
        next_btn = InlineKeyboardButton(text="➡️", callback_data="disc:noop")

    keyboard_rows.append([prev_btn, badge_btn, next_btn])

    # 4. Exit button: Return to main menu
    keyboard_rows.append([
        InlineKeyboardButton(text="« ⬅️ В главное меню", callback_data="nav:home")
    ])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))


def get_discipline_detail_screen(
    discipline: Discipline,
    return_page: int = 1,
) -> Screen:
    """Details card for a specific discipline with curator and context actions."""
    tier_label = "🔥 Major (>200 игроков)" if discipline.tier == DisciplineTier.MAJOR else "⚡ Medium (50-200 игроков)"

    if discipline.admin:
        if discipline.admin.username:
            curator_str = f"@{discipline.admin.username}"
        else:
            curator_str = f"{discipline.admin.first_name} {discipline.admin.last_name or ''}".strip()
    else:
        curator_str = "<i>Куратор не назначен</i>"

    text = (
        f"🎮 <b>{discipline.name}</b>\n\n"
        f"🏷 <b>Категория:</b> {tier_label}\n"
        f"👤 <b>Куратор направления:</b> {curator_str}\n\n"
        f"📝 <b>О дисциплине:</b>\n{discipline.description}\n\n"
        "Присоединяйтесь к комьюнити дисциплины в Telegram:"
    )

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    # 1. URL button opening community chat directly
    if discipline.chat_url:
        keyboard_rows.append([
            InlineKeyboardButton(text="💬 Чат дисциплины в Telegram ↗", url=discipline.chat_url)
        ])

    # 2. Context button: Minecraft whitelist management
    if discipline.slug.lower() == "minecraft":
        keyboard_rows.append([
            InlineKeyboardButton(text="⛏ Управление вайтлистом", callback_data="nav:minecraft")
        ])

    # 3. Context button: Tournament slot booking for competitive esports
    if discipline.slug.lower() in ["cs2", "dota2", "fifa", "valorant", "pubg", "mlbb"]:
        keyboard_rows.append([
            InlineKeyboardButton(text="🏆 Забронировать турнир", callback_data="tb:start")
        ])

    # 4. Return to exact origin page
    keyboard_rows.append([
        InlineKeyboardButton(text="◀️ Назад к списку дисциплин", callback_data=f"disc:page:{return_page}")
    ])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))
