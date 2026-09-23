"""
Comprehensive test suite for Backend Infrastructure:
1. Database connection (engine connectivity, session transactions, DB disconnect simulation in health check)
2. Redis connection (offline detection, connected state, ping failure handling, lifecycle)
3. API health endpoints (/api/v1/health, /api/health, and / root status)
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.main import app
from app.data_access.database import async_engine, SessionLocal, get_db
from app.state.redis_manager import (
    check_redis_health,
    init_redis_client,
    close_redis_client,
)


@pytest_asyncio.fixture()
async def client():
    """AsyncClient connected to the FastAPI ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. Database Connection Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_database_engine_connection():
    """Verify live PostgreSQL connectivity via the async engine."""
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 AS alive"))
        row = result.fetchone()
        assert row is not None
        assert row[0] == 1


def test_database_sync_session_query():
    """Verify that synchronous SessionLocal operates correctly against PostgreSQL."""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 42 AS answer"))
        val = result.scalar()
        assert val == 42
    finally:
        db.close()


@pytest.mark.asyncio
async def test_health_check_database_connected(client: AsyncClient):
    """
    GET /api/v1/health reports database='connected' when PostgreSQL is responding.
    """
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["database"] == "connected"
    assert "redis" in body["data"]
    assert "timestamp" in body["data"]
    assert "version" in body["data"]


@pytest.mark.asyncio
async def test_health_check_database_disconnected_simulation(client: AsyncClient):
    """
    When PostgreSQL connection fails (simulated), /api/v1/health does not crash with 500,
    but gracefully reports database='disconnected' and overall status='degraded'.
    """
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("Connection to PostgreSQL failed: connection refused")

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["database"] == "disconnected"
        assert data["status"] == "degraded"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# 2. Redis Connection Tests
# ---------------------------------------------------------------------------

class FakeRedisForInfra:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def ping(self):
        if self.should_fail:
            raise ConnectionError("Simulated Redis connection failure")
        return True

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_redis_connection_offline_state():
    """When Redis is not running or disconnected, check_redis_health reports unavailable/degraded."""
    with patch("app.state.redis_manager.is_redis_available", return_value=False):
        health = await check_redis_health()
        assert health["status"] == "unavailable"
        assert "degraded" in health["mode"]


@pytest.mark.asyncio
async def test_redis_connection_online_state():
    """When Redis ping succeeds, check_redis_health reports connected and measures latency."""
    fake_client = FakeRedisForInfra(should_fail=False)
    with patch("app.state.redis_manager.is_redis_available", return_value=True), \
         patch("app.state.redis_manager._client", fake_client):
        health = await check_redis_health()
        assert health["status"] == "connected"
        assert "latency_ms" in health
        assert isinstance(health["latency_ms"], float)


@pytest.mark.asyncio
async def test_redis_connection_ping_error_handled_gracefully():
    """When Redis ping raises an exception, health status degrades without throwing unhandled error."""
    fake_client = FakeRedisForInfra(should_fail=True)
    with patch("app.state.redis_manager.is_redis_available", return_value=True), \
         patch("app.state.redis_manager._client", fake_client):
        health = await check_redis_health()
        assert health["status"] == "disconnected"
        assert "degraded" in health["mode"]
        assert "Simulated Redis connection failure" in health.get("error", "")


@pytest.mark.asyncio
async def test_redis_lifecycle_init_and_close():
    """Verify init_redis_client and close_redis_client run safely without unhandled errors."""
    with patch("app.state.redis_manager.aioredis.ConnectionPool.from_url") as mock_pool_from_url, \
         patch("app.state.redis_manager.aioredis.Redis") as mock_redis_cls:
        mock_instance = AsyncMock()
        mock_instance.ping.return_value = True
        mock_redis_cls.return_value = mock_instance

        client = await init_redis_client()
        assert client is not None

        await close_redis_client()
        mock_instance.aclose.assert_awaited_once()


# ---------------------------------------------------------------------------
# 3. API Health Endpoints Contract
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_health_contract(client: AsyncClient):
    """GET /api/v1/health adheres to the standardized ApiResponse format."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "data" in body
    data = body["data"]
    assert data["service"] == "Transformer Failure Risk Monitoring Backend"
    assert data["version"] == "1.0.0"
    assert data["status"] in ("healthy", "degraded")
    assert data["database"] in ("connected", "disconnected")
    assert isinstance(data["redis"], dict)


@pytest.mark.asyncio
async def test_legacy_api_health_contract(client: AsyncClient):
    """GET /api/health responds identically for legacy backward compatibility."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["service"] == "Transformer Failure Risk Monitoring Backend"


@pytest.mark.asyncio
async def test_root_endpoint_status(client: AsyncClient):
    """GET / returns online status with API version and docs links."""
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "online"
    assert body["api_v1"] == "/api/v1"
    assert body["docs"] == "/docs"
