"""
Factory and dependency provider for CursorStore.
Attempts to connect to Redis; falls back gracefully to InMemoryCursorStore if unavailable.
"""

import logging

from app.config import settings
from app.state.cursor_store import CursorStore, InMemoryCursorStore, RedisCursorStore
from app.state.redis_manager import get_redis_client, is_redis_available

logger = logging.getLogger("transformer_backend.state")

_cursor_store: CursorStore | None = None


async def init_cursor_store() -> CursorStore:
    """
    Initialize the cursor store singleton.
    Uses Redis client if available; falls back gracefully to InMemoryCursorStore.
    """
    global _cursor_store
    client = get_redis_client()
    if client is not None and is_redis_available():
        logger.info("Initializing RedisCursorStore with active Redis connection.")
        _cursor_store = RedisCursorStore(
            redis_client=client, ttl_seconds=settings.REDIS_CURSOR_TTL_SECONDS
        )
    else:
        logger.info("Initializing fallback InMemoryCursorStore (Redis offline or uninitialized).")
        _cursor_store = InMemoryCursorStore(default_ttl_seconds=settings.REDIS_CURSOR_TTL_SECONDS)
    return _cursor_store


async def close_cursor_store() -> None:
    """Close and clean up the active cursor store singleton."""
    global _cursor_store
    if _cursor_store is not None:
        try:
            await _cursor_store.close()
        except Exception as e:
            logger.warning(f"Error closing cursor store: {e}")
        finally:
            _cursor_store = None


def get_cursor_store() -> CursorStore:
    """
    FastAPI dependency returning the active CursorStore singleton.
    If uninitialized, returns an in-memory cursor store.
    """
    global _cursor_store
    if _cursor_store is None:
        logger.debug(
            "CursorStore not yet initialized via lifespan; providing fallback InMemoryCursorStore."
        )
        _cursor_store = InMemoryCursorStore(default_ttl_seconds=settings.REDIS_CURSOR_TTL_SECONDS)
    return _cursor_store
