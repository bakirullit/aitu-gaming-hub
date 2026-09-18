import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from core.context import CoreContext
from services.discipline_service import DisciplineService
from plugins.disciplines.screens import (
    get_disciplines_catalog_screen,
    get_discipline_detail_screen,
)

logger = logging.getLogger("plugins.disciplines.router")

router = Router(name="disciplines_router")


def setup_disciplines_routes(core: CoreContext) -> Router:
    """Configures and binds core dependencies to the Disciplines catalog router."""

    # Register screen renderer for deterministic Back navigation in Anchor Navigator
    async def render_disciplines_catalog(user_id: int, chat_id: int, payload: dict) -> any:
        page = payload.get("page", 1)
        async with core.db_session_factory() as session:
            disciplines = await DisciplineService.get_all(session=session, active_only=True)
            return get_disciplines_catalog_screen(disciplines=disciplines, page=page)

    core.navigator.register_screen_renderer("disciplines:catalog", render_disciplines_catalog)  # type: ignore

    # 1. Main entry point: Catalog Page 1
    @router.callback_query(F.data.in_(["hub:disciplines", "nav:disciplines"]))
    async def cb_disciplines_catalog_home(callback: CallbackQuery, session: AsyncSession) -> None:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        disciplines = await DisciplineService.get_all(session=session, active_only=True)
        screen = get_disciplines_catalog_screen(disciplines=disciplines, page=1)

        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="disciplines:catalog",
            payload={"page": 1},
            push_to_history=True,
        )
        await callback.answer()

    # 2. Pagination handler: updates anchor in-place without stack pollution
    @router.callback_query(F.data.startswith("disc:page:"))
    async def cb_disciplines_page(callback: CallbackQuery, session: AsyncSession) -> None:
        try:
            page = int(callback.data.split(":", 2)[2])
        except (IndexError, ValueError):
            page = 1

        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        disciplines = await DisciplineService.get_all(session=session, active_only=True)
        screen = get_disciplines_catalog_screen(disciplines=disciplines, page=page)

        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id="disciplines:catalog",
            payload={"page": page},
            push_to_history=False,
        )
        await callback.answer()

    # 3. Informational non-clickable pagination button
    @router.callback_query(F.data == "disc:noop")
    async def cb_disciplines_noop(callback: CallbackQuery) -> None:
        await callback.answer()

    # 4. Details Card View with exact origin page return link
    @router.callback_query(F.data.startswith("disc:view:"))
    async def cb_discipline_view(callback: CallbackQuery, session: AsyncSession) -> None:
        parts = callback.data.split(":")
        slug = parts[2] if len(parts) > 2 else ""
        try:
            return_page = int(parts[3]) if len(parts) > 3 else 1
        except ValueError:
            return_page = 1

        discipline = await DisciplineService.get_by_slug(slug, session=session)
        if not discipline or not discipline.is_active:
            await callback.answer("⚠️ Дисциплина не найдена или временно отключена.", show_alert=True)
            return

        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        screen = get_discipline_detail_screen(discipline=discipline, return_page=return_page)

        await core.navigator.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id=f"disciplines:detail:{slug}",
            payload={"slug": slug, "page": return_page},
            push_to_history=True,
        )
        await callback.answer()

    # 5. Return to Main Menu alias
    @router.callback_query(F.data == "hub:main_menu")
    async def cb_disciplines_main_menu(callback: CallbackQuery) -> None:
        # Delegate to Navigator back or home
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        await core.navigator.back(user_id=user_id, chat_id=chat_id)
        await callback.answer()

    return router
