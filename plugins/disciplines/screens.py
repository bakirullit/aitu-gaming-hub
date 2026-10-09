import math
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from common.dtos.screen import Screen
from common.models.discipline import Discipline, DisciplineTier
from common.texts import get_text

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

    text = get_text(
        "disciplines.catalog.text",
        total_items=total_items,
        current_page=current_page,
        total_pages=total_pages,
    )

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    # 1. Pinned top button: Discord community link
    keyboard_rows.append([
        InlineKeyboardButton(
            text=get_text("disciplines.catalog.buttons.discord"),
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
    if current_page > 1:
        prev_btn = InlineKeyboardButton(text="⬅️", callback_data=f"disc:page:{current_page - 1}")
    else:
        prev_btn = InlineKeyboardButton(text="⬅️", callback_data="disc:noop")

    badge_btn = InlineKeyboardButton(
        text=f"· {current_page}/{total_pages} ·",
        callback_data="disc:noop",
    )

    if current_page < total_pages:
        next_btn = InlineKeyboardButton(text="➡️", callback_data=f"disc:page:{current_page + 1}")
    else:
        next_btn = InlineKeyboardButton(text="➡️", callback_data="disc:noop")

    keyboard_rows.append([prev_btn, badge_btn, next_btn])

    # 4. Exit button: Return to main menu
    keyboard_rows.append([
        InlineKeyboardButton(text=get_text("disciplines.catalog.buttons.main_menu"), callback_data="nav:home")
    ])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))


def get_discipline_detail_screen(
    discipline: Discipline,
    return_page: int = 1,
    can_manage_whitelist: bool | None = None,
    can_book_tournament: bool | None = None,
) -> Screen:
    """Details card for a specific discipline with curator and context actions."""
    if discipline.tier == DisciplineTier.MAJOR:
        tier_label = get_text("disciplines.detail.tier_major", default="🔥 Major (>200 игроков)")
    else:
        tier_label = get_text("disciplines.detail.tier_medium", default="⚡ Medium (50-200 игроков)")

    if discipline.admin:
        if discipline.admin.username:
            curator_str = f"@{discipline.admin.username}"
        else:
            curator_str = f"{discipline.admin.first_name} {discipline.admin.last_name or ''}".strip()
    else:
        curator_str = get_text("disciplines.detail.no_curator", default="<i>Куратор не назначен</i>")

    text = get_text(
        "disciplines.detail.text",
        name=discipline.name,
        tier_label=tier_label,
        curator_str=curator_str,
        description=discipline.description or "",
    )

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    # 1. URL button opening community chat directly
    if discipline.chat_url:
        keyboard_rows.append([
            InlineKeyboardButton(text=get_text("disciplines.detail.buttons.chat"), url=discipline.chat_url)
        ])

    # 2. Context button: Minecraft whitelist management
    # Visible when explicitly enabled, or default enabled if curator is assigned
    show_mc_whitelist = (
        can_manage_whitelist
        if can_manage_whitelist is not None
        else bool(discipline.admin_id)
    )
    if discipline.slug.lower() == "minecraft" and show_mc_whitelist:
        keyboard_rows.append([
            InlineKeyboardButton(text=get_text("disciplines.detail.buttons.minecraft"), callback_data="nav:minecraft")
        ])

    # 3. Context button: Tournament slot booking (only discipline_admin)
    show_booking = can_book_tournament if can_book_tournament is not None else True
    if discipline.slug.lower() in ["cs2", "dota2", "fifa", "valorant", "pubg", "mlbb"] and show_booking:
        keyboard_rows.append([
            InlineKeyboardButton(text=get_text("disciplines.detail.buttons.book_tournament"), callback_data="tb:start")
        ])

    # 4. Return to exact origin page
    keyboard_rows.append([
        InlineKeyboardButton(text=get_text("disciplines.detail.buttons.back_catalog"), callback_data=f"disc:page:{return_page}")
    ])

    return Screen(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))
