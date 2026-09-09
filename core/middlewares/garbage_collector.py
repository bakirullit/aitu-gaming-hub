from collections.abc import Awaitable, Callable
from typing import Any
import logging
from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

logger = logging.getLogger("core.middlewares.garbage_collector")


class GarbageCollectorMiddleware(BaseMiddleware):
    """
    Garbage Collector Middleware (Input Interceptor).
    Ensures zero chat spam: intercepts and deletes user-sent text messages immediately,
    forwarding the message to the handler so that the anchor message can update in-place.
    """

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        bot: Bot = data.get("bot") or event.bot  # type: ignore

        # Only process actual user text/data messages in private chats
        if event.chat and event.chat.type == "private":
            try:
                await bot.delete_message(
                    chat_id=event.chat.id,
                    message_id=event.message_id,
                )
                logger.debug(
                    f"GarbageCollector deleted incoming message {event.message_id} from chat {event.chat.id}"
                )
            except TelegramBadRequest as exc:
                # Silently catch if message is already deleted or cannot be removed
                logger.debug(f"GarbageCollector could not delete message {event.message_id}: {exc}")
            except Exception as exc:
                logger.warning(f"Unexpected error in GarbageCollector deleting message: {exc}")

        return await handler(event, data)
