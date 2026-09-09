from collections.abc import Awaitable, Callable
from typing import Any
import logging
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from redis.asyncio import Redis

logger = logging.getLogger("core.middlewares.user_lock")


class UserLockMiddleware(BaseMiddleware):
    """
    Distributed lock middleware for Telegram callback queries.
    Prevents race conditions, double-clicks, and state corruption by acquiring
    a short-lived Redis lock for the user during callback processing.
    """

    def __init__(self, redis: Redis, lock_timeout: float = 2.0) -> None:
        self._redis = redis
        self._lock_timeout = lock_timeout

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        lock_key = f"lock:user:{user_id}"

        # Try to acquire lock non-blocking
        lock = self._redis.lock(lock_key, timeout=self._lock_timeout, blocking=False)
        acquired = await lock.acquire(blocking=False)

        if not acquired:
            logger.warning(f"User {user_id} triggered concurrent callback, dropped by lock.")
            # Acknowledge callback quickly so Telegram stops showing loading spinner
            try:
                await event.answer("Пожалуйста, подождите...", show_alert=False)
            except Exception:
                pass
            return None

        try:
            return await handler(event, data)
        finally:
            try:
                await lock.release()
            except Exception as exc:
                # Lock might have expired if handler took longer than timeout
                logger.debug(f"Lock release for user {user_id} suppressed: {exc}")
