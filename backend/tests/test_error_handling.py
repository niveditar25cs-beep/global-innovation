"""
Comprehensive test suite for Backend Error Handling:
1. Invalid Requests (422 Unprocessable Entity, validation schema, error details)
2. Missing Records (404 ResourceNotFoundError, unknown endpoints)
3. Database Failures (500 Internal Server Error with zero leaks of credentials or tracebacks)
4. Redis Failures (Graceful degradation, fail-open rate limiting, in-memory cursor failover)
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.exc import OperationalError

from app.error_handling.exceptions import ResourceNotFoundError
from app.main import app
from app.state.cache_service import CacheService
from app.state.rate_limiter import RateLimiter
from app.state.cursor_store import RedisCursorStore


@pytest_asyncio.fixture()
async def client():
    """AsyncClient connected to the FastAPI application with raise_app_exceptions=False."""
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. Invalid Requests (422 Validation Error Tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_request_sequence_non_numeric(client: AsyncClient):
    """GET /api/v1/readings/current?sequence=abc returns 422 with structured validation error."""
    resp = await client.get("/api/v1/readings/current?sequence=abc")
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "REQUEST_VALIDATION_FAILED"
    assert "details" in body["error"]
    assert any("sequence" in d["field"] for d in body["error"]["details"])
    assert "X-Request-ID" in resp.headers


@pytest.mark.asyncio
async def test_invalid_request_negative_sequence(client: AsyncClient):
    """GET /api/v1/readings/current?sequence=-5 returns 422 (must be >= 1)."""
    resp = await client.get("/api/v1/readings/current?sequence=-5")
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "REQUEST_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_invalid_request_history_pagination_out_of_bounds(client: AsyncClient):
    """GET /api/v1/readings/history with page=0 or limit=501 returns 422."""
    # Page cannot be 0 (ge=1)
    resp_page = await client.get("/api/v1/readings/history?page=0")
    assert resp_page.status_code == 422
    assert resp_page.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"

    # Limit cannot exceed 500
    resp_limit = await client.get("/api/v1/readings/history?limit=501")
    assert resp_limit.status_code == 422
    assert resp_limit.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"

    # Limit cannot be 0
    resp_zero = await client.get("/api/v1/readings/history?limit=0")
    assert resp_zero.status_code == 422
    assert resp_zero.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_invalid_request_history_invalid_sort_params(client: AsyncClient):
    """GET /api/v1/readings/history with invalid sort_by or order returns 422."""
    resp_sort = await client.get("/api/v1/readings/history?sort_by=hack_column")
    assert resp_sort.status_code == 422
    assert resp_sort.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"

    resp_order = await client.get("/api/v1/readings/history?order=sideways")
    assert resp_order.status_code == 422
    assert resp_order.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_invalid_request_dataset_preview_limit(client: AsyncClient):
    """GET /api/v1/dataset/preview with limit=0 or limit=500 returns 422 (max is 100)."""
    resp_zero = await client.get("/api/v1/dataset/preview?limit=0")
    assert resp_zero.status_code == 422
    assert resp_zero.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"

    resp_high = await client.get("/api/v1/dataset/preview?limit=500")
    assert resp_high.status_code == 422
    assert resp_high.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"


# ---------------------------------------------------------------------------
# 2. Missing Records (404 Tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_record_current_reading_unknown_transformer(client: AsyncClient):
    """GET /api/v1/readings/current?transformer_id=NONEXISTENT_999 returns 404."""
    with patch("app.routes.reading_routes.CurrentReadingService") as MockService:
        MockService.return_value.get_current_reading = AsyncMock(
            side_effect=ResourceNotFoundError(resource="Transformer", identifier="NONEXISTENT_999")
        )
        resp = await client.get("/api/v1/readings/current?transformer_id=NONEXISTENT_999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "NONEXISTENT_999" in body["error"]["message"]
    assert "request_id" in body["error"]


@pytest.mark.asyncio
async def test_missing_record_current_reading_unknown_sequence(client: AsyncClient):
    """GET /api/v1/readings/current?sequence=99999999 returns 404."""
    with patch("app.routes.reading_routes.CurrentReadingService") as MockService:
        MockService.return_value.get_current_reading = AsyncMock(
            side_effect=ResourceNotFoundError(resource="TransformerReading", identifier="sequence 99999999")
        )
        resp = await client.get("/api/v1/readings/current?sequence=99999999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_missing_record_next_reading_unknown_transformer(client: AsyncClient):
    """GET /api/v1/readings/next?transformer_id=GHOST_TRANSFORMER returns 404."""
    with patch("app.routes.reading_routes.NextReadingService") as MockService:
        MockService.return_value.get_next_reading = AsyncMock(
            side_effect=ResourceNotFoundError(resource="Transformer", identifier="GHOST_TRANSFORMER")
        )
        resp = await client.get("/api/v1/readings/next?transformer_id=GHOST_TRANSFORMER")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_missing_record_history_unknown_transformer(client: AsyncClient):
    """GET /api/v1/readings/history?transformer_id=UNKNOWN_TX returns 404."""
    with patch("app.routes.reading_routes.HistoryReadingService") as MockService:
        MockService.return_value.get_reading_history = AsyncMock(
            side_effect=ResourceNotFoundError(resource="Transformer", identifier="UNKNOWN_TX")
        )
        resp = await client.get("/api/v1/readings/history?transformer_id=UNKNOWN_TX")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_missing_record_transformer_detail(client: AsyncClient):
    """GET /api/v1/transformers/NONEXISTENT_ID returns 404."""
    with patch("app.routes.transformer_routes.TransformerController") as MockController:
        MockController.return_value.get_transformer.side_effect = ResourceNotFoundError(
            resource="Transformer", identifier="NONEXISTENT_ID"
        )
        resp = await client.get("/api/v1/transformers/NONEXISTENT_ID")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_missing_route_returns_404(client: AsyncClient):
    """Requesting an unmapped URL returns standardized 404."""
    resp = await client.get("/api/v1/unmapped_nonexistent_endpoint")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
    assert "request_id" in body["error"]


# ---------------------------------------------------------------------------
# 3. Database Failures (500 Error Sanitization & No Leaks)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_database_failure_500_sanitized_no_secret_or_traceback_leak(client: AsyncClient):
    """
    When a database operation fails with internal credentials or query details,
    the API returns HTTP 500 without leaking passwords, connection strings, or tracebacks.
    """
    secret_connection_error = (
        "OperationalError: connection to server at '10.0.0.5', port 5432 failed: "
        "FATAL: password authentication failed for user 'postgres' with password 'SuperSecretDBPass123!'. "
        "URI: postgresql+asyncpg://postgres:SuperSecretDBPass123!@10.0.0.5:5432/transformer_prod"
    )

    with patch("app.routes.reading_routes.CurrentReadingService") as MockService:
        instance = MockService.return_value
        instance.get_current_reading = AsyncMock(
            side_effect=OperationalError(statement="SELECT * FROM readings", params={}, orig=Exception(secret_connection_error))
        )

        resp = await client.get("/api/v1/readings/current")

    assert resp.status_code == 500
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"

    raw_text = resp.text
    # STRICT SECURITY ASSERTIONS:
    assert "SuperSecretDBPass123!" not in raw_text
    assert "postgresql+asyncpg://" not in raw_text
    assert "Traceback (most recent call last)" not in raw_text
    assert 'File "' not in raw_text

    # Header and body request_id correlation
    assert "X-Request-ID" in resp.headers
    assert body["error"]["request_id"] == resp.headers["X-Request-ID"]


# ---------------------------------------------------------------------------
# 4. Redis Failures (Fault Resilience & Fallbacks)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_failure_during_next_reading_falls_back_to_memory(client: AsyncClient):
    """
    If Redis throws a ConnectionError during next reading state update,
    RedisCursorStore safely falls back to in-memory store and reading retrieval succeeds.
    """
    mock_redis = MagicMock()
    mock_redis.register_script.return_value = AsyncMock(side_effect=ConnectionError("Redis cluster unreachable"))
    mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis cluster unreachable"))
    mock_redis.set = AsyncMock(side_effect=ConnectionError("Redis cluster unreachable"))

    cursor_store = RedisCursorStore(redis_client=mock_redis)

    # advance_cursor should encounter Redis error and cleanly fall back to in-memory store
    seq = await cursor_store.advance_cursor(session_id="session-test-failover", transformer_id="T001")
    assert seq == 1  # Successfully advanced on in-memory fallback

    # Subsequent advance advances in-memory
    seq2 = await cursor_store.advance_cursor(session_id="session-test-failover", transformer_id="T001")
    assert seq2 == 2

    # Get cursor reflects in-memory value
    current = await cursor_store.get_cursor(session_id="session-test-failover", transformer_id="T001")
    assert current == 2


@pytest.mark.asyncio
async def test_redis_failure_during_cache_fails_safe():
    """CacheService methods safely return None / False without raising when Redis is down."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))
    mock_redis.set = AsyncMock(side_effect=ConnectionError("Redis down"))
    mock_redis.delete = AsyncMock(side_effect=ConnectionError("Redis down"))

    cache = CacheService(redis_client=mock_redis)

    # All cache operations must handle Redis error safely
    assert await cache.get("key1") is None
    assert await cache.set("key1", {"data": 123}) is False
    assert await cache.delete("key1") is False


@pytest.mark.asyncio
async def test_redis_failure_during_rate_limiter_fails_open():
    """RateLimiter fails open (allows request) when Redis fails."""
    mock_pipe = MagicMock()
    mock_pipe.incr = MagicMock()
    mock_pipe.ttl = MagicMock()
    mock_pipe.execute = AsyncMock(side_effect=ConnectionError("Redis connection dropped"))

    mock_redis = MagicMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    limiter = RateLimiter(requests=5, window_seconds=60, scope="test_limiter", redis_client=mock_redis)

    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.state.request_id = "test-req-fail-open"
    mock_request.headers = {}

    # Must not raise HTTPException(429) or 500; returns None gracefully
    await limiter(mock_request)
