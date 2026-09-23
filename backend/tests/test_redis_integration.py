"""
Comprehensive tests for Redis integration:
- Connection and pool management
- Ephemeral caching service (hit, miss, delete, prefix invalidation)
- Cache service fail-safe behavior on Redis errors
- RateLimiter token bucket enforcement (allow, 429 throttle, headers)
- RateLimiter fail-open resilience on Redis outages
- RedisCursorStore failover to in-memory fallback on connection drop
- Health check reporting Redis operational status
"""
from typing import Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from fastapi import Request, HTTPException
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.state.redis_manager import (
    init_redis_client,
    close_redis_client,
    check_redis_health,
    is_redis_available,
)
from app.state.cache_service import CacheService
from app.state.rate_limiter import RateLimiter
from app.state.cursor_store import RedisCursorStore, InMemoryCursorStore


# ---------------------------------------------------------------------------
# Mock Redis Client Helpers
# ---------------------------------------------------------------------------

class FakeRedisClient:
    """In-memory fake Redis client mimicking redis.asyncio.Redis."""

    def __init__(self):
        self._kv: dict[str, str] = {}
        self._ttls: dict[str, int] = {}
        self.should_fail = False

    async def ping(self):
        if self.should_fail:
            raise ConnectionError("Simulated Redis connection failure")
        return True

    async def get(self, key: str) -> Optional[str]:
        if self.should_fail:
            raise ConnectionError("Simulated Redis connection failure")
        return self._kv.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        if self.should_fail:
            raise ConnectionError("Simulated Redis connection failure")
        self._kv[key] = str(value)
        if ex is not None:
            self._ttls[key] = ex
        return True

    async def delete(self, *keys: str) -> int:
        if self.should_fail:
            raise ConnectionError("Simulated Redis connection failure")
        count = 0
        for k in keys:
            if k in self._kv:
                del self._kv[k]
                self._ttls.pop(k, None)
                count += 1
        return count

    async def scan(self, cursor: int = 0, match: Optional[str] = None, count: int = 10):
        if self.should_fail:
            raise ConnectionError("Simulated Redis connection failure")
        prefix = match.replace("*", "") if match else ""
        matched = [k for k in self._kv.keys() if k.startswith(prefix)]
        return 0, matched

    def pipeline(self):
        fake_self = self

        class FakePipeline:
            def __init__(self):
                self._ops = []

            def incr(self, key: str):
                self._ops.append(("incr", key))
                return self

            def ttl(self, key: str):
                self._ops.append(("ttl", key))
                return self

            async def execute(self):
                if fake_self.should_fail:
                    raise ConnectionError("Simulated Redis pipeline failure")
                results = []
                for op, key in self._ops:
                    if op == "incr":
                        val = int(fake_self._kv.get(key, 0)) + 1
                        fake_self._kv[key] = str(val)
                        results.append(val)
                    elif op == "ttl":
                        results.append(fake_self._ttls.get(key, -1))
                return results

        return FakePipeline()

    async def expire(self, key: str, seconds: int):
        if self.should_fail:
            raise ConnectionError("Simulated Redis connection failure")
        self._ttls[key] = seconds
        return True

    def register_script(self, script: str):
        fake_self = self

        async def _script_executor(keys, args):
            if fake_self.should_fail:
                raise ConnectionError("Simulated Redis Lua failure")
            key = keys[0]
            val = int(fake_self._kv.get(key, 0)) + 1
            fake_self._kv[key] = str(val)
            return val

        return _script_executor

    async def aclose(self):
        self._kv.clear()


# ---------------------------------------------------------------------------
# Tests: Redis Manager & Health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_health_when_disconnected():
    """When Redis is uninitialized or unreachable, health check returns degraded mode."""
    with patch("app.state.redis_manager.is_redis_available", return_value=False):
        health = await check_redis_health()
        assert health["status"] == "unavailable"
        assert "degraded" in health["mode"]


@pytest.mark.asyncio
async def test_redis_health_when_connected():
    """When Redis is operational, health check returns connected with ping latency."""
    fake_redis = FakeRedisClient()
    with patch("app.state.redis_manager.is_redis_available", return_value=True), \
         patch("app.state.redis_manager._client", fake_redis):
        health = await check_redis_health()
        assert health["status"] == "connected"
        assert "latency_ms" in health


@pytest.mark.asyncio
async def test_redis_health_degrades_on_ping_error():
    """If ping throws an exception, health status degrades without raising."""
    fake_redis = FakeRedisClient()
    fake_redis.should_fail = True
    with patch("app.state.redis_manager.is_redis_available", return_value=True), \
         patch("app.state.redis_manager._client", fake_redis):
        health = await check_redis_health()
        assert health["status"] == "disconnected"
        assert "degraded" in health["mode"]


# ---------------------------------------------------------------------------
# Tests: Ephemeral Caching Service
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_service_set_get_and_delete():
    """CacheService stores, retrieves, and deletes JSON objects with prefixing."""
    fake_redis = FakeRedisClient()
    cache = CacheService(redis_client=fake_redis, default_ttl=60)

    data = {"transformer_id": "TR-001", "voltage": 132.5}

    # Set
    ok = await cache.set("tr_1", data, prefix="tx")
    assert ok is True

    # Get (hit)
    cached = await cache.get("tr_1", prefix="tx")
    assert cached == data

    # Get (miss)
    miss = await cache.get("nonexistent", prefix="tx")
    assert miss is None

    # Delete
    del_ok = await cache.delete("tr_1", prefix="tx")
    assert del_ok is True
    assert await cache.get("tr_1", prefix="tx") is None


@pytest.mark.asyncio
async def test_cache_service_prefix_invalidation():
    """CacheService deletes all keys matching a prefix via SCAN."""
    fake_redis = FakeRedisClient()
    cache = CacheService(redis_client=fake_redis)

    await cache.set("k1", "v1", prefix="tx")
    await cache.set("k2", "v2", prefix="tx")
    await cache.set("k3", "v3", prefix="other")

    deleted = await cache.delete_prefix("tx")
    assert deleted == 2
    assert await cache.get("k1", prefix="tx") is None
    assert await cache.get("k3", prefix="other") == "v3"


@pytest.mark.asyncio
async def test_cache_service_graceful_fail_safe_on_redis_error():
    """CacheService never raises if Redis fails; it simply returns None (cache miss)."""
    fake_redis = FakeRedisClient()
    fake_redis.should_fail = True
    cache = CacheService(redis_client=fake_redis)

    # Should not raise exception
    res_get = await cache.get("any_key")
    assert res_get is None

    res_set = await cache.set("any_key", {"a": 1})
    assert res_set is False

    res_del = await cache.delete("any_key")
    assert res_del is False


# ---------------------------------------------------------------------------
# Tests: Rate Limiter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limiter_allows_and_throttles():
    """RateLimiter allows requests within quota and throws 429 when exceeded."""
    fake_redis = FakeRedisClient()
    limiter = RateLimiter(requests=3, window_seconds=60, scope="test_scope", redis_client=fake_redis)

    scope = {"type": "http", "client": ("127.0.0.1", 12345), "headers": []}
    req = Request(scope)

    # Requests 1, 2, 3 should pass without error
    await limiter(req)
    assert req.state.ratelimit_remaining == 2

    await limiter(req)
    assert req.state.ratelimit_remaining == 1

    await limiter(req)
    assert req.state.ratelimit_remaining == 0

    # 4th request exceeds quota of 3
    with pytest.raises(HTTPException) as exc_info:
        await limiter(req)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_rate_limiter_fail_open_on_redis_error():
    """RateLimiter fails open (permits request) if Redis experiences an outage."""
    fake_redis = FakeRedisClient()
    fake_redis.should_fail = True
    limiter = RateLimiter(requests=5, window_seconds=60, scope="test_scope", redis_client=fake_redis)

    scope = {"type": "http", "client": ("127.0.0.1", 12345), "headers": []}
    req = Request(scope)

    # Must complete without throwing any exception
    await limiter(req)


# ---------------------------------------------------------------------------
# Tests: RedisCursorStore Failover Resilience
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cursor_store_failover_to_memory_on_redis_error():
    """If Redis fails mid-operation, RedisCursorStore fails over to in-memory store."""
    fake_redis = FakeRedisClient()
    fake_redis.should_fail = True

    cursor_store = RedisCursorStore(redis_client=fake_redis, ttl_seconds=3600)

    # Should not raise; fails over to in-memory and returns sequence 1
    seq1 = await cursor_store.advance_cursor("sess_1", "TR-001", max_sequence=10)
    assert seq1 == 1

    seq2 = await cursor_store.advance_cursor("sess_1", "TR-001", max_sequence=10)
    assert seq2 == 2

    cur = await cursor_store.get_cursor("sess_1", "TR-001")
    assert cur == 2


# ---------------------------------------------------------------------------
# Tests: Health Route Live Integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint_includes_redis_status():
    """GET /api/health includes redis status in response payload."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "redis" in body["data"]
        assert "status" in body["data"]["redis"]
