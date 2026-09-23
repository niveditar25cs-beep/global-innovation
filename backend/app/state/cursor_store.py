"""
Cursor store protocol and implementations (Redis and InMemory fallback).
Provides atomic per-session sequence tracking for simulated reading playback.
"""

import asyncio
import logging
from typing import Protocol, runtime_checkable

import redis.asyncio as aioredis

logger = logging.getLogger("transformer_backend.state")

LUA_ADVANCE_SCRIPT = """
local key = KEYS[1]
local ttl = tonumber(ARGV[1])
local max_seq = tonumber(ARGV[2])

local current = redis.call('GET', key)
local next_seq
if not current then
    next_seq = 1
else
    next_seq = tonumber(current) + 1
end

if max_seq and max_seq > 0 and next_seq > (max_seq + 1) then
    next_seq = max_seq + 1
end

redis.call('SET', key, next_seq, 'EX', ttl)
return next_seq
"""


@runtime_checkable
class CursorStore(Protocol):
    """Protocol for stateful reading cursor storage."""

    async def get_cursor(self, session_id: str, transformer_id: str) -> int | None:
        """Retrieve the current cursor sequence for a session/transformer pair, or None if unset."""
        ...

    async def advance_cursor(
        self, session_id: str, transformer_id: str, max_sequence: int | None = None
    ) -> int:
        """
        Atomically advance and return the next sequence number for the session.
        If no cursor exists, initializes to 1.
        If max_sequence is provided, pins cursor at max_sequence + 1 once exceeded.
        """
        ...

    async def set_cursor(self, session_id: str, transformer_id: str, sequence: int) -> None:
        """Explicitly set the cursor to a specific sequence number."""
        ...

    async def reset_cursor(self, session_id: str, transformer_id: str) -> None:
        """Reset / delete the cursor for the given session and transformer."""
        ...

    async def close(self) -> None:
        """Close backing connections or clean up resources."""
        ...


class RedisCursorStore:
    """
    Redis-backed cursor store using atomic Lua script execution.
    Safe across multiple backend workers and concurrent requests within a session.
    Features automatic in-memory failover if Redis drops during execution.
    """

    def __init__(self, redis_client: aioredis.Redis, ttl_seconds: int = 14400):
        self.redis = redis_client
        self.ttl = ttl_seconds
        self._advance_script = self.redis.register_script(LUA_ADVANCE_SCRIPT)
        self._fallback_memory = InMemoryCursorStore(default_ttl_seconds=ttl_seconds)

    @staticmethod
    def _build_key(session_id: str, transformer_id: str) -> str:
        return f"cursor:{session_id}:{transformer_id}"

    async def get_cursor(self, session_id: str, transformer_id: str) -> int | None:
        key = self._build_key(session_id, transformer_id)
        try:
            val = await self.redis.get(key)
            if val is not None:
                return int(val)
            return await self._fallback_memory.get_cursor(session_id, transformer_id)
        except Exception as e:
            logger.warning(f"Redis get_cursor failed ({e}); checking in-memory fallback.")
            return await self._fallback_memory.get_cursor(session_id, transformer_id)

    async def advance_cursor(
        self, session_id: str, transformer_id: str, max_sequence: int | None = None
    ) -> int:
        key = self._build_key(session_id, transformer_id)
        max_seq_arg = max_sequence if (max_sequence is not None and max_sequence > 0) else -1
        try:
            result = await self._advance_script(keys=[key], args=[self.ttl, max_seq_arg])
            return int(result)
        except Exception as e:
            logger.warning("Redis advance_cursor failed (%s); failing over to in-memory cursor.", e)
            return await self._fallback_memory.advance_cursor(
                session_id, transformer_id, max_sequence
            )

    async def set_cursor(self, session_id: str, transformer_id: str, sequence: int) -> None:
        key = self._build_key(session_id, transformer_id)
        try:
            await self.redis.set(key, sequence, ex=self.ttl)
        except Exception as e:
            logger.warning(f"Redis set_cursor failed ({e}); setting on in-memory fallback.")
            await self._fallback_memory.set_cursor(session_id, transformer_id, sequence)

    async def reset_cursor(self, session_id: str, transformer_id: str) -> None:
        key = self._build_key(session_id, transformer_id)
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis reset_cursor failed ({e}); clearing in-memory fallback.")
            await self._fallback_memory.reset_cursor(session_id, transformer_id)

    async def close(self) -> None:
        try:
            await self.redis.aclose()
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")
        await self._fallback_memory.close()


class InMemoryCursorStore:
    """
    In-memory fallback cursor store protected by an asyncio.Lock.
    Used during local development or testing when Redis is not running.
    """

    def __init__(self, default_ttl_seconds: int = 14400):
        self._store: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self.default_ttl = default_ttl_seconds

    @staticmethod
    def _build_key(session_id: str, transformer_id: str) -> str:
        return f"cursor:{session_id}:{transformer_id}"

    async def get_cursor(self, session_id: str, transformer_id: str) -> int | None:
        key = self._build_key(session_id, transformer_id)
        async with self._lock:
            return self._store.get(key)

    async def advance_cursor(
        self, session_id: str, transformer_id: str, max_sequence: int | None = None
    ) -> int:
        key = self._build_key(session_id, transformer_id)
        async with self._lock:
            current = self._store.get(key)
            next_seq = 1 if current is None else current + 1

            if max_sequence is not None and max_sequence > 0 and next_seq > (max_sequence + 1):
                next_seq = max_sequence + 1

            self._store[key] = next_seq
            return next_seq

    async def set_cursor(self, session_id: str, transformer_id: str, sequence: int) -> None:
        key = self._build_key(session_id, transformer_id)
        async with self._lock:
            self._store[key] = sequence

    async def reset_cursor(self, session_id: str, transformer_id: str) -> None:
        key = self._build_key(session_id, transformer_id)
        async with self._lock:
            self._store.pop(key, None)

    async def close(self) -> None:
        async with self._lock:
            self._store.clear()
