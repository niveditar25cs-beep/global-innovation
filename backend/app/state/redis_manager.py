"""
Central Redis connection and lifecycle management.
Provides connection pooling, health checks, and graceful failure handling.
"""

import logging
import time
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger("transformer_backend.redis")

_pool: aioredis.ConnectionPool | None = None
_client: aioredis.Redis | None = None
_is_available: bool = False


async def init_redis_client() -> aioredis.Redis | None:
    """
    Initialize Redis connection pool and verify connectivity.
    If Redis is unreachable, backend logs a warning and operates in degraded mode.
    """
    global _pool, _client, _is_available
    try:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            decode_responses=True,
        )
        _client = aioredis.Redis(connection_pool=_pool)

        # Verify connectivity
        start = time.perf_counter()
        await _client.ping()
        latency = (time.perf_counter() - start) * 1000.0

        _is_available = True
        logger.info(
            f"Redis connected successfully to {settings.REDIS_URL} "
            f"(latency: {latency:.2f}ms, pool_max: {settings.REDIS_MAX_CONNECTIONS})"
        )
        return _client
    except Exception as e:
        _is_available = False
        await close_redis_client()
        logger.warning(
            f"Redis connection failed for {settings.REDIS_URL} ({type(e).__name__}: {e}). "
            "Backend operating in graceful degraded mode "
            "(in-memory cursors, direct DB queries, fail-open rate limiting)."
        )
        return None


async def close_redis_client() -> None:
    """Close Redis client and release all pool connections cleanly."""
    global _pool, _client, _is_available
    if _client is not None:
        try:
            await _client.aclose()
        except Exception as e:
            logger.warning(f"Error closing Redis client: {e}")
        finally:
            _client = None

    if _pool is not None:
        try:
            await _pool.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting Redis pool: {e}")
        finally:
            _pool = None

    _is_available = False
    logger.info("Redis connections closed cleanly.")


def get_redis_client() -> aioredis.Redis | None:
    """
    FastAPI dependency and utility function to get the active Redis client.
    Returns None if Redis is currently unavailable.
    """
    if _is_available and _client is not None:
        return _client
    return None


def is_redis_available() -> bool:
    """Check if Redis connection is active and operational."""
    return _is_available and _client is not None


async def check_redis_health() -> dict[str, Any]:
    """
    Perform a live ping check to evaluate Redis health.
    Returns health status dictionary for inclusion in system health probes.
    """
    global _is_available
    client = _client
    if client is None or not is_redis_available():
        return {
            "status": "unavailable",
            "mode": "degraded (in-memory fallback active)",
            "url": settings.REDIS_URL,
        }

    try:
        start = time.perf_counter()
        await client.ping()
        latency_ms = (time.perf_counter() - start) * 1000.0
        return {
            "status": "connected",
            "latency_ms": round(latency_ms, 2),
            "url": settings.REDIS_URL,
        }
    except Exception as e:
        _is_available = False
        logger.warning(f"Redis health check failed: {e}")
        return {
            "status": "disconnected",
            "error": str(e),
            "mode": "degraded (in-memory fallback active)",
        }
