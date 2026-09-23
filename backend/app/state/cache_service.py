"""
Resilient, short-lived caching service backed by Redis.
Automatically handles serialization and fails safely if Redis is offline.
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings
from app.state.redis_manager import get_redis_client

logger = logging.getLogger("transformer_backend.cache")


class CacheService:
    """
    Ephemeral caching layer for non-critical query acceleration.
    Guaranteed fail-safe: All errors degrade silently to cache misses.
    """

    def __init__(self, redis_client: aioredis.Redis | None = None, default_ttl: int | None = None):
        self._custom_client = redis_client
        self.default_ttl = default_ttl or settings.REDIS_CACHE_TTL_SECONDS

    @property
    def client(self) -> aioredis.Redis | None:
        return self._custom_client if self._custom_client is not None else get_redis_client()

    @staticmethod
    def _build_key(key: str, prefix: str) -> str:
        return f"cache:{prefix}:{key}"

    async def get(self, key: str, prefix: str = "default") -> Any | None:
        """
        Fetch and deserialize a cached object.
        Returns None on cache miss or when Redis is unreachable.
        """
        client = self.client
        if client is None:
            return None

        full_key = self._build_key(key, prefix)
        try:
            raw = await client.get(full_key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug(f"Cache GET failed for '{full_key}' ({e}); bypassing cache.")
            return None

    async def set(
        self, key: str, value: Any, ttl: int | None = None, prefix: str = "default"
    ) -> bool:
        """
        Serialize and store a value in Redis with a time-to-live (TTL).
        Returns False on error without raising exceptions.
        """
        client = self.client
        if client is None:
            return False

        full_key = self._build_key(key, prefix)
        effective_ttl = ttl if ttl is not None else self.default_ttl

        try:
            serialized = json.dumps(value, default=str)
            await client.set(full_key, serialized, ex=effective_ttl)
            return True
        except Exception as e:
            logger.debug(f"Cache SET failed for '{full_key}' ({e}); skipping cache write.")
            return False

    async def delete(self, key: str, prefix: str = "default") -> bool:
        """Invalidate a specific cached entry."""
        client = self.client
        if client is None:
            return False

        full_key = self._build_key(key, prefix)
        try:
            await client.delete(full_key)
            return True
        except Exception as e:
            logger.debug(f"Cache DELETE failed for '{full_key}' ({e}).")
            return False

    async def delete_prefix(self, prefix: str) -> int:
        """
        Invalidate all keys matching a specific cache namespace prefix.
        Uses non-blocking SCAN to preserve Redis performance.
        """
        client = self.client
        if client is None:
            return 0

        pattern = f"cache:{prefix}:*"
        deleted_count = 0
        try:
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    deleted = await client.delete(*keys)
                    deleted_count += deleted
                if cursor == 0:
                    break
            return deleted_count
        except Exception as e:
            logger.debug(f"Cache DELETE_PREFIX failed for '{pattern}' ({e}).")
            return 0


# Default singleton instance for application use
cache_service = CacheService()


def get_cache_service() -> CacheService:
    """FastAPI dependency for accessing CacheService."""
    return cache_service
