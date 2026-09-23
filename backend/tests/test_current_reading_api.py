"""
Tests for GET /api/readings/current

Strategy:
- Override the `get_async_db` FastAPI dependency so no real PostgreSQL
  connection is required.
- Patch `CurrentReadingService` in the route module to control responses.
- Use httpx AsyncClient with ASGITransport so the full FastAPI middleware
  and exception-handler stack is exercised.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.data_access.database import get_async_db
from app.schemas.current_reading import CurrentReadingApiResponse, CurrentReadingData
from app.error_handling.exceptions import ResourceNotFoundError


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_response(
    transformer_id: str = "T001",
    voltage: float = 230.0,
    current: float = 12.5,
    temperature: float = 68.0,
    sequence: int = 1,
) -> CurrentReadingApiResponse:
    """Build a fully-populated CurrentReadingApiResponse for mocking."""
    return CurrentReadingApiResponse(
        success=True,
        data=CurrentReadingData(
            transformer_id=transformer_id,
            voltage=voltage,
            current=current,
            temperature=temperature,
            sequence=sequence,
        ),
    )


# ---------------------------------------------------------------------------
# Dependency overrides
# ---------------------------------------------------------------------------

async def _fake_async_db():
    """Yield a mock session so no real DB connection is needed."""
    yield MagicMock()


@pytest_asyncio.fixture(autouse=True)
async def override_deps():
    """Override DB dependency for every test in this module."""
    app.dependency_overrides[get_async_db] = _fake_async_db
    yield
    app.dependency_overrides.pop(get_async_db, None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def client():
    """ASGI test client that speaks directly to the FastAPI application."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_reading_default_transformer(client: AsyncClient):
    """
    GET /api/readings/current with no query params returns 200 with the
    first transformer's first reading.
    """
    mock_response = _make_response()

    with patch(
        "app.routes.reading_routes.CurrentReadingService",
        autospec=True,
    ) as MockService:
        instance = MockService.return_value
        instance.get_current_reading = AsyncMock(return_value=mock_response)

        resp = await client.get("/api/readings/current")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["transformer_id"] == "T001"
    assert data["voltage"] == 230.0
    assert data["current"] == 12.5
    assert data["temperature"] == 68.0
    assert data["sequence"] == 1


@pytest.mark.asyncio
async def test_get_current_reading_specific_transformer(client: AsyncClient):
    """
    GET /api/readings/current?transformer_id=TR-042 resolves the named
    transformer and returns its reading.
    """
    mock_response = _make_response(transformer_id="TR-042", sequence=7)

    with patch(
        "app.routes.reading_routes.CurrentReadingService",
        autospec=True,
    ) as MockService:
        instance = MockService.return_value
        instance.get_current_reading = AsyncMock(return_value=mock_response)

        resp = await client.get("/api/readings/current?transformer_id=TR-042")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["transformer_id"] == "TR-042"
    assert body["data"]["sequence"] == 7

    # Verify the service received the correct arguments
    instance.get_current_reading.assert_awaited_once_with(
        transformer_id="TR-042",
        sequence=None,
    )


@pytest.mark.asyncio
async def test_get_current_reading_with_explicit_sequence(client: AsyncClient):
    """
    GET /api/readings/current?transformer_id=T001&sequence=42 returns
    exactly the requested reading sequence.
    """
    mock_response = _make_response(sequence=42, voltage=415.0)

    with patch(
        "app.routes.reading_routes.CurrentReadingService",
        autospec=True,
    ) as MockService:
        instance = MockService.return_value
        instance.get_current_reading = AsyncMock(return_value=mock_response)

        resp = await client.get(
            "/api/readings/current?transformer_id=T001&sequence=42"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["sequence"] == 42
    assert body["data"]["voltage"] == 415.0

    instance.get_current_reading.assert_awaited_once_with(
        transformer_id="T001",
        sequence=42,
    )


@pytest.mark.asyncio
async def test_get_current_reading_transformer_not_found(client: AsyncClient):
    """
    When the requested transformer does not exist the service raises
    ResourceNotFoundError, which the exception handler maps to a 404.
    """
    with patch(
        "app.routes.reading_routes.CurrentReadingService",
        autospec=True,
    ) as MockService:
        instance = MockService.return_value
        instance.get_current_reading = AsyncMock(
            side_effect=ResourceNotFoundError(
                resource="Transformer",
                identifier="DOES-NOT-EXIST",
            )
        )

        resp = await client.get(
            "/api/readings/current?transformer_id=DOES-NOT-EXIST"
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_current_reading_sequence_not_found(client: AsyncClient):
    """
    When a specific sequence is requested but doesn't exist the service raises
    ResourceNotFoundError with a sequence-scoped identifier → 404.
    """
    with patch(
        "app.routes.reading_routes.CurrentReadingService",
        autospec=True,
    ) as MockService:
        instance = MockService.return_value
        instance.get_current_reading = AsyncMock(
            side_effect=ResourceNotFoundError(
                resource="TransformerReading",
                identifier="sequence 9999 for transformer 'T001'",
            )
        )

        resp = await client.get(
            "/api/readings/current?transformer_id=T001&sequence=9999"
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_current_reading_invalid_sequence_param(client: AsyncClient):
    """
    sequence=0 violates the `ge=1` constraint — FastAPI returns 422
    Unprocessable Entity before the service is called.
    """
    resp = await client.get("/api/readings/current?sequence=0")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_current_reading_response_schema(client: AsyncClient):
    """
    Verify the full response envelope matches the documented schema:
    { "success": true, "data": { transformer_id, voltage, current, temperature, sequence } }
    """
    mock_response = _make_response(
        transformer_id="T002",
        voltage=132.0,
        current=350.0,
        temperature=75.5,
        sequence=5,
    )

    with patch(
        "app.routes.reading_routes.CurrentReadingService",
        autospec=True,
    ) as MockService:
        instance = MockService.return_value
        instance.get_current_reading = AsyncMock(return_value=mock_response)

        resp = await client.get("/api/readings/current?transformer_id=T002")

    assert resp.status_code == 200
    body = resp.json()

    # Exact schema contract
    assert set(body.keys()) == {"success", "data"}
    assert body["success"] is True
    assert set(body["data"].keys()) == {
        "transformer_id", "voltage", "current", "temperature", "sequence"
    }
    assert isinstance(body["data"]["voltage"], float)
    assert isinstance(body["data"]["current"], float)
    assert isinstance(body["data"]["temperature"], float)
    assert isinstance(body["data"]["sequence"], int)
