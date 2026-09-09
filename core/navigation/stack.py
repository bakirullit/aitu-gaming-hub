import json
from typing import Any
import logging
from redis.asyncio import Redis

logger = logging.getLogger("core.navigation.stack")


class NavigationStackManager:
    """Manages user screen navigation history stored in Redis as a LIFO stack."""

    def __init__(self, redis: Redis, max_depth: int = 20) -> None:
        self._redis = redis
        self._max_depth = max_depth

    def _key(self, user_id: int) -> str:
        return f"anchor:user:{user_id}:stack"

    async def push(self, user_id: int, screen_id: str, payload: dict[str, Any] | None = None) -> None:
        """Push a screen identifier and state payload to the user's navigation stack."""
        key = self._key(user_id)
        entry = json.dumps({"screen_id": screen_id, "payload": payload or {}})
        await self._redis.lpush(key, entry)
        await self._redis.ltrim(key, 0, self._max_depth - 1)
        # Keep stack alive for 24 hours
        await self._redis.expire(key, 86400)

    async def pop(self, user_id: int) -> dict[str, Any] | None:
        """Pop the current screen off the top of the stack."""
        key = self._key(user_id)
        val = await self._redis.lpop(key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except Exception:
            return None

    async def peek(self, user_id: int) -> dict[str, Any] | None:
        """Inspect the current screen at the top of the stack without removing it."""
        key = self._key(user_id)
        items = await self._redis.lrange(key, 0, 0)
        if not items:
            return None
        try:
            return json.loads(items[0])
        except Exception:
            return None

    async def clear(self, user_id: int) -> None:
        """Reset the entire navigation history for the user."""
        await self._redis.delete(self._key(user_id))
