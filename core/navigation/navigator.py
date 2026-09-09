from collections.abc import Awaitable, Callable
from typing import Any
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from redis.asyncio import Redis
from common.dtos.screen import Screen
from core.navigation.stack import NavigationStackManager
from core.protocols import NavigatorProtocol

logger = logging.getLogger("core.navigation.navigator")

ScreenRenderer = Callable[[int, int, dict[str, Any]], Awaitable[Screen]]


class Navigator(NavigatorProtocol):
    """Anchor Wizard UI Engine managing the Single Persistent Visual Message per user."""

    def __init__(self, bot: Bot, redis: Redis) -> None:
        self._bot = bot
        self._redis = redis
        self._stack = NavigationStackManager(redis)
        self._screen_renderers: dict[str, ScreenRenderer] = {}

    def register_screen_renderer(self, screen_id: str, renderer: ScreenRenderer) -> None:
        """Register a screen renderer function associated with a screen identifier."""
        self._screen_renderers[screen_id] = renderer
        logger.debug(f"Registered screen renderer for screen_id='{screen_id}'")

    def _anchor_key(self, user_id: int) -> str:
        return f"anchor:user:{user_id}:message_id"

    async def get_anchor_id(self, user_id: int) -> int | None:
        """Fetch the stored anchor message ID from Redis."""
        val = await self._redis.get(self._anchor_key(user_id))
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    async def set_anchor_id(self, user_id: int, message_id: int) -> None:
        """Store or update the active anchor message ID in Redis."""
        # 30 days retention
        await self._redis.set(self._anchor_key(user_id), str(message_id), ex=2592000)

    async def reset_history(self, user_id: int) -> None:
        """Clear navigation stack history for the user."""
        await self._stack.clear(user_id)

    async def render(
        self,
        user_id: int,
        chat_id: int,
        screen: Screen,
        screen_id: str | None = None,
        payload: dict[str, Any] | None = None,
        push_to_history: bool = True,
    ) -> Message | None:
        """
        Render a declarative Screen into the single persistent anchor message.
        - Silently ignores 'message is not modified'.
        - If anchor message was deleted or cannot be edited, sends a new message and updates Redis.
        """
        anchor_id = await self.get_anchor_id(user_id)
        msg: Message | None = None

        if anchor_id is not None:
            try:
                msg = await self._bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=anchor_id,
                    text=screen.text,
                    reply_markup=screen.reply_markup,
                    parse_mode=screen.parse_mode,
                )
            except TelegramBadRequest as err:
                err_msg = str(err).lower()
                if "message is not modified" in err_msg:
                    # Deterministic silent catch per specification
                    logger.debug(f"Anchor message {anchor_id} for user {user_id} not modified.")
                    return None
                elif (
                    "message to edit not found" in err_msg
                    or "message can't be edited" in err_msg
                    or "message_id_invalid" in err_msg
                ):
                    logger.warning(
                        f"Anchor message {anchor_id} missing or cannot be edited. "
                        f"Recreating persistent anchor for user {user_id}."
                    )
                    msg = await self._bot.send_message(
                        chat_id=chat_id,
                        text=screen.text,
                        reply_markup=screen.reply_markup,
                        parse_mode=screen.parse_mode,
                    )
                    await self.set_anchor_id(user_id, msg.message_id)
                else:
                    logger.error(f"Unexpected TelegramBadRequest editing anchor: {err}")
                    raise
        else:
            # First interaction: create anchor message
            msg = await self._bot.send_message(
                chat_id=chat_id,
                text=screen.text,
                reply_markup=screen.reply_markup,
                parse_mode=screen.parse_mode,
            )
            await self.set_anchor_id(user_id, msg.message_id)

        # Track history for deterministic "Back" navigation
        if push_to_history and screen_id:
            await self._stack.push(user_id, screen_id, payload)

        return msg

    async def back(self, user_id: int, chat_id: int) -> bool:
        """
        Pop the current screen from LIFO stack and render the previous screen.
        Returns True if navigation succeeded, False if stack was empty.
        """
        # Pop active screen
        _ = await self._stack.pop(user_id)
        # Peek at previous screen
        prev = await self._stack.peek(user_id)
        if not prev:
            logger.info(f"Navigation stack empty for user {user_id}.")
            return False

        screen_id = prev.get("screen_id")
        payload = prev.get("payload", {})

        renderer = self._screen_renderers.get(screen_id)
        if not renderer:
            logger.warning(f"No renderer registered for screen_id='{screen_id}'")
            return False

        screen = await renderer(user_id, chat_id, payload)
        await self.render(
            user_id=user_id,
            chat_id=chat_id,
            screen=screen,
            screen_id=screen_id,
            payload=payload,
            push_to_history=False,
        )
        return True
