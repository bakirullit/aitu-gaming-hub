from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Chat, Message
from core.middlewares.garbage_collector import GarbageCollectorMiddleware


@pytest.mark.asyncio
async def test_garbage_collector_deletes_message_in_private_chat() -> None:
    bot = MagicMock()
    bot.delete_message = AsyncMock(return_value=True)

    chat = MagicMock(spec=Chat)
    chat.id = 12345
    chat.type = "private"

    message = MagicMock(spec=Message)
    message.chat = chat
    message.message_id = 999
    message.text = "210103001"
    message.bot = bot

    next_handler = AsyncMock(return_value="handler_result")

    middleware = GarbageCollectorMiddleware()
    data = {"bot": bot}

    result = await middleware(next_handler, message, data)

    bot.delete_message.assert_awaited_once_with(chat_id=12345, message_id=999)
    next_handler.assert_awaited_once_with(message, data)
    assert result == "handler_result"


@pytest.mark.asyncio
async def test_garbage_collector_suppresses_delete_bad_request() -> None:
    bot = MagicMock()
    method = MagicMock()
    exc = TelegramBadRequest(method=method, message="Bad Request: message to delete not found")
    bot.delete_message = AsyncMock(side_effect=exc)

    chat = MagicMock(spec=Chat)
    chat.id = 12345
    chat.type = "private"

    message = MagicMock(spec=Message)
    message.chat = chat
    message.message_id = 999
    message.bot = bot

    next_handler = AsyncMock(return_value="success")

    middleware = GarbageCollectorMiddleware()
    data = {"bot": bot}

    # Must not raise exception
    result = await middleware(next_handler, message, data)
    assert result == "success"
    bot.delete_message.assert_awaited_once()
