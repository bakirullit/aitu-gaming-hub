from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from common.dtos.screen import Screen
from core.navigation.navigator import Navigator


class MockRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.data[key] = value

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)
        self.lists.pop(key, None)

    async def lpush(self, key: str, value: str) -> None:
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].insert(0, value)

    async def lpop(self, key: str) -> str | None:
        if key in self.lists and self.lists[key]:
            return self.lists[key].pop(0)
        return None

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        if key not in self.lists:
            return []
        end_idx = None if end == -1 else end + 1
        return self.lists[key][start:end_idx]

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        if key in self.lists:
            stop_idx = None if stop == -1 else stop + 1
            self.lists[key] = self.lists[key][start:stop_idx]

    async def expire(self, key: str, seconds: int) -> None:
        pass


@pytest.mark.asyncio
async def test_navigator_creates_anchor_on_first_render() -> None:
    bot = MagicMock()
    fake_msg = MagicMock(spec=Message)
    fake_msg.message_id = 777
    bot.send_message = AsyncMock(return_value=fake_msg)

    redis = MockRedis()
    navigator = Navigator(bot=bot, redis=redis)  # type: ignore

    screen = Screen(text="Welcome to AITU Gaming Hub")
    res = await navigator.render(user_id=101, chat_id=101, screen=screen)

    assert res == fake_msg
    bot.send_message.assert_awaited_once()
    stored_id = await navigator.get_anchor_id(101)
    assert stored_id == 777


@pytest.mark.asyncio
async def test_navigator_edits_existing_anchor() -> None:
    bot = MagicMock()
    fake_msg = MagicMock(spec=Message)
    fake_msg.message_id = 777
    bot.edit_message_text = AsyncMock(return_value=fake_msg)

    redis = MockRedis()
    await redis.set("anchor:user:101:message_id", "777")
    navigator = Navigator(bot=bot, redis=redis)  # type: ignore

    screen = Screen(text="Updated Screen")
    res = await navigator.render(user_id=101, chat_id=101, screen=screen)

    assert res == fake_msg
    bot.edit_message_text.assert_awaited_once_with(
        chat_id=101,
        message_id=777,
        text="Updated Screen",
        reply_markup=None,
        parse_mode="HTML",
    )


@pytest.mark.asyncio
async def test_navigator_silently_ignores_message_not_modified() -> None:
    bot = MagicMock()
    # Mock TelegramBadRequest with "message is not modified"
    method = MagicMock()
    exc = TelegramBadRequest(method=method, message="Bad Request: message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message")
    bot.edit_message_text = AsyncMock(side_effect=exc)

    redis = MockRedis()
    await redis.set("anchor:user:101:message_id", "777")
    navigator = Navigator(bot=bot, redis=redis)  # type: ignore

    screen = Screen(text="Exact Same Text")
    # Must not raise exception
    res = await navigator.render(user_id=101, chat_id=101, screen=screen)
    assert res is None


@pytest.mark.asyncio
async def test_navigator_recreates_anchor_if_deleted() -> None:
    bot = MagicMock()
    method = MagicMock()
    exc = TelegramBadRequest(method=method, message="Bad Request: message to edit not found")
    bot.edit_message_text = AsyncMock(side_effect=exc)

    new_msg = MagicMock(spec=Message)
    new_msg.message_id = 888
    bot.send_message = AsyncMock(return_value=new_msg)

    redis = MockRedis()
    await redis.set("anchor:user:101:message_id", "777")
    navigator = Navigator(bot=bot, redis=redis)  # type: ignore

    screen = Screen(text="Recovered Screen")
    res = await navigator.render(user_id=101, chat_id=101, screen=screen)

    assert res == new_msg
    bot.send_message.assert_awaited_once()
    stored_id = await navigator.get_anchor_id(101)
    assert stored_id == 888


@pytest.mark.asyncio
async def test_navigator_back_navigation() -> None:
    bot = MagicMock()
    redis = MockRedis()
    navigator = Navigator(bot=bot, redis=redis)  # type: ignore

    # Register screen renderers
    async def render_screen_a(user_id: int, chat_id: int, payload: dict) -> Screen:
        return Screen(text="Screen A Content")

    navigator.register_screen_renderer("screen_a", render_screen_a)

    # Push screen_a then screen_b to history
    await navigator._stack.push(101, "screen_a")
    await navigator._stack.push(101, "screen_b")

    # Spy on navigator.render
    navigator.render = AsyncMock(return_value=None)  # type: ignore

    success = await navigator.back(user_id=101, chat_id=101)
    assert success is True
    # Verify render was called with Screen A
    assert navigator.render.call_count == 1
    call_args = navigator.render.call_args[1]
    assert call_args["screen"].text == "Screen A Content"
    assert call_args["screen_id"] == "screen_a"
