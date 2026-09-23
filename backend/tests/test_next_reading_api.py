"""
Tests for GET /api/readings/next

Covers:
- First reading generation (creates session, returns sequence 1)
- Strict sequential advance across multiple calls
- End-of-dataset graceful handling (200 with is_end_of_dataset: true)
- Unknown / expired session starting fresh
- Invalid transformer returning 404
- Concurrent requests within the same session (atomic, non-overlapping sequences)
- Full response schema validation
- Independent session cursors isolation
"""
import asyncio
from typing import Optional
from unittest.mock import MagicMock
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.data_access.database import get_async_db
from app.state.store_factory import get_cursor_store
from app.state.cursor_store import InMemoryCursorStore
from app.models.transformer import Transformer
from app.models.reading import TransformerReading


# ---------------------------------------------------------------------------
# Test Data Fixtures & Mocks
# ---------------------------------------------------------------------------

class FakeReadingRepo:
    """Mock repository providing deterministic transformer readings."""

    def __init__(self, max_readings: int = 5):
        self.max_readings = max_readings
        self.tx1 = Transformer(id=1, transformer_id="TR-001", name="Main Substation Alpha")
        self.tx2 = Transformer(id=2, transformer_id="TR-002", name="Substation Beta")

    async def get_default_transformer(self) -> Optional[Transformer]:
        return self.tx1

    async def get_transformer_by_identifier(self, identifier: str) -> Optional[Transformer]:
        cleaned = str(identifier).strip()
        if cleaned in ("TR-001", "1"):
            return self.tx1
        if cleaned in ("TR-002", "2"):
            return self.tx2
        return None

    async def count_readings_for_transformer(self, transformer_db_id: int) -> int:
        if transformer_db_id == 1:
            return self.max_readings
        if transformer_db_id == 2:
            return 0
        return 0

    async def get_max_sequence(self, transformer_db_id: int) -> Optional[int]:
        if transformer_db_id == 1:
            return self.max_readings
        return None

    async def get_reading_by_sequence(
        self,
        transformer_db_id: int,
        sequence: int
    ) -> Optional[TransformerReading]:
        if transformer_db_id == 1 and 1 <= sequence <= self.max_readings:
            reading = TransformerReading(
                id=sequence,
                transformer_id=transformer_db_id,
                reading_sequence=sequence,
                voltage=230.0 + (sequence * 1.5),
                current=12.0 + (sequence * 0.5),
                temperature=60.0 + (sequence * 0.8),
            )
            reading.transformer = self.tx1
            return reading
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cursor_store() -> InMemoryCursorStore:
    """Provide a fresh in-memory cursor store for each test."""
    return InMemoryCursorStore()


@pytest.fixture
def fake_repo() -> FakeReadingRepo:
    """Provide a fake reading repository with 5 readings for TR-001."""
    return FakeReadingRepo(max_readings=5)


@pytest_asyncio.fixture(autouse=True)
async def setup_dependencies(cursor_store: InMemoryCursorStore, fake_repo: FakeReadingRepo, monkeypatch):
    """Override FastAPI dependencies and patch AsyncReadingRepository in next_reading_service."""
    app.dependency_overrides[get_cursor_store] = lambda: cursor_store

    async def _fake_async_db():
        yield MagicMock()

    app.dependency_overrides[get_async_db] = _fake_async_db

    # Patch AsyncReadingRepository instantiation in NextReadingService
    monkeypatch.setattr(
        "app.services.next_reading_service.AsyncReadingRepository",
        lambda session: fake_repo
    )

    yield

    app.dependency_overrides.pop(get_cursor_store, None)
    app.dependency_overrides.pop(get_async_db, None)


@pytest_asyncio.fixture
async def client():
    """ASGI async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_reading_generates_session_and_sequence_1(client: AsyncClient):
    """
    Calling GET /api/readings/next without a session_id should generate a session,
    initialize cursor, and return sequence 1.
    """
    resp = await client.get("/api/readings/next")
    assert resp.status_code == 200

    body = resp.json()
    assert body["success"] is True
    data = body["data"]

    assert data["transformer_id"] == "TR-001"
    assert data["sequence"] == 1
    assert data["voltage"] == 231.5
    assert data["current"] == 12.5
    assert data["temperature"] == 60.8
    assert data["has_next"] is True
    assert data["is_end_of_dataset"] is False
    assert data["total_readings"] == 5
    assert isinstance(data["session_id"], str) and len(data["session_id"]) > 0


@pytest.mark.asyncio
async def test_sequential_advance_same_session(client: AsyncClient):
    """
    Subsequent calls with the same session_id should strictly advance 1 -> 2 -> 3.
    """
    # First call - start session
    resp1 = await client.get("/api/readings/next?transformer_id=TR-001")
    assert resp1.status_code == 200
    session_id = resp1.json()["data"]["session_id"]
    assert resp1.json()["data"]["sequence"] == 1

    # Second call
    resp2 = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_id}")
    assert resp2.status_code == 200
    assert resp2.json()["data"]["sequence"] == 2
    assert resp2.json()["data"]["has_next"] is True

    # Third call
    resp3 = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_id}")
    assert resp3.status_code == 200
    assert resp3.json()["data"]["sequence"] == 3
    assert resp3.json()["data"]["has_next"] is True


@pytest.mark.asyncio
async def test_end_of_dataset_returns_200_and_flag(client: AsyncClient):
    """
    Advancing past max_readings (5) should return HTTP 200 with is_end_of_dataset=True,
    has_next=False, and null telemetry fields.
    """
    session_id = "test-session-end"

    # Consume readings 1 to 5
    for expected_seq in range(1, 6):
        resp = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["sequence"] == expected_seq
        if expected_seq == 5:
            assert resp.json()["data"]["has_next"] is False

    # 6th call should hit end of dataset
    resp_end = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_id}")
    assert resp_end.status_code == 200
    body = resp_end.json()
    assert body["success"] is True
    data = body["data"]

    assert data["is_end_of_dataset"] is True
    assert data["has_next"] is False
    assert data["sequence"] is None
    assert data["voltage"] is None
    assert data["current"] is None
    assert data["temperature"] is None
    assert data["total_readings"] == 5

    # 7th call remains pinned at end of dataset
    resp_again = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_id}")
    assert resp_again.status_code == 200
    assert resp_again.json()["data"]["is_end_of_dataset"] is True


@pytest.mark.asyncio
async def test_unknown_session_starts_fresh(client: AsyncClient):
    """
    An unknown or fresh session_id should start at sequence 1.
    """
    resp = await client.get("/api/readings/next?transformer_id=TR-001&session_id=brand-new-uuid-12345")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["session_id"] == "brand-new-uuid-12345"
    assert data["sequence"] == 1


@pytest.mark.asyncio
async def test_invalid_transformer_returns_404(client: AsyncClient):
    """
    Querying an invalid transformer identifier returns HTTP 404.
    """
    resp = await client.get("/api/readings/next?transformer_id=UNKNOWN-999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert "Transformer" in body["error"]["message"]


@pytest.mark.asyncio
async def test_concurrent_requests_same_session(client: AsyncClient):
    """
    Multiple concurrent requests for the same session should all receive
    distinct, monotonically increasing sequences without collisions or race conditions.
    """
    session_id = "concurrent-session-id"

    # Launch 5 concurrent calls
    tasks = [
        client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_id}")
        for _ in range(5)
    ]
    responses = await asyncio.gather(*tasks)

    for resp in responses:
        assert resp.status_code == 200

    sequences = [resp.json()["data"]["sequence"] for resp in responses]
    assert sorted(sequences) == [1, 2, 3, 4, 5], f"Expected [1, 2, 3, 4, 5] but got {sorted(sequences)}"


@pytest.mark.asyncio
async def test_independent_sessions_do_not_interfere(client: AsyncClient):
    """
    Two independent sessions advance their own cursors without interfering.
    """
    session_a = "session-alice"
    session_b = "session-bob"

    # Alice advances to 1 and 2
    r_a1 = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_a}")
    assert r_a1.json()["data"]["sequence"] == 1
    r_a2 = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_a}")
    assert r_a2.json()["data"]["sequence"] == 2

    # Bob starts fresh at 1
    r_b1 = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_b}")
    assert r_b1.json()["data"]["sequence"] == 1

    # Alice advances to 3
    r_a3 = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_a}")
    assert r_a3.json()["data"]["sequence"] == 3

    # Bob advances to 2
    r_b2 = await client.get(f"/api/readings/next?transformer_id=TR-001&session_id={session_b}")
    assert r_b2.json()["data"]["sequence"] == 2


@pytest.mark.asyncio
async def test_empty_transformer_returns_end_of_dataset(client: AsyncClient):
    """
    A transformer with 0 readings returns is_end_of_dataset=True and total_readings=0.
    """
    resp = await client.get("/api/readings/next?transformer_id=TR-002")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["transformer_id"] == "TR-002"
    assert data["is_end_of_dataset"] is True
    assert data["has_next"] is False
    assert data["total_readings"] == 0
    assert data["sequence"] is None


@pytest.mark.asyncio
async def test_response_schema_format(client: AsyncClient):
    """
    Validate the full response envelope structure and datatypes.
    """
    resp = await client.get("/api/readings/next?transformer_id=TR-001")
    assert resp.status_code == 200
    body = resp.json()

    assert "success" in body
    assert body["success"] is True
    assert "data" in body

    data = body["data"]
    required_keys = {
        "transformer_id",
        "voltage",
        "current",
        "temperature",
        "sequence",
        "has_next",
        "is_end_of_dataset",
        "session_id",
        "total_readings"
    }
    assert required_keys.issubset(data.keys())
    assert isinstance(data["transformer_id"], str)
    assert isinstance(data["voltage"], float)
    assert isinstance(data["current"], float)
    assert isinstance(data["temperature"], float)
    assert isinstance(data["sequence"], int)
    assert isinstance(data["has_next"], bool)
    assert isinstance(data["is_end_of_dataset"], bool)
    assert isinstance(data["session_id"], str)
    assert isinstance(data["total_readings"], int)
