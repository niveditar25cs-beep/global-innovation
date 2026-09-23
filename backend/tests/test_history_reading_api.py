"""
Tests for GET /api/v1/readings/history and GET /api/readings/history

Covers:
- Default pagination (page=1, limit=20)
- Transformer ID filtering
- Non-existent transformer 404 handling
- Sorting by timestamp (asc / desc)
- Sorting by sequence (asc / desc)
- Pagination boundaries and navigation flags (total_pages, has_next, has_prev)
- Time-range filtering (start_time, end_time)
- Query validation errors (page < 1, limit > 500, invalid sort_by/order)
- Route alias /api/v1/readings/history compatibility
"""
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.data_access.database import get_async_db
from app.models.transformer import Transformer
from app.models.reading import TransformerReading


# ---------------------------------------------------------------------------
# Test Data Fixtures & Mocks
# ---------------------------------------------------------------------------

class FakeHistoryReadingRepo:
    """Mock repository providing deterministic historical readings."""

    def __init__(self, count_tr1: int = 50, count_tr2: int = 25):
        self.tx1 = Transformer(id=1, transformer_id="TR-001", name="Main Substation Alpha")
        self.tx2 = Transformer(id=2, transformer_id="TR-002", name="Substation Beta")

        base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.readings: List[TransformerReading] = []

        # TR-001 readings
        for i in range(1, count_tr1 + 1):
            r = TransformerReading(
                id=i,
                transformer_id=1,
                reading_sequence=i,
                voltage=230.0 + (i * 0.1),
                current=10.0 + (i * 0.2),
                temperature=60.0 + (i * 0.05),
                timestamp=base_time + timedelta(hours=i),
            )
            r.transformer = self.tx1
            self.readings.append(r)

        # TR-002 readings
        for j in range(1, count_tr2 + 1):
            r = TransformerReading(
                id=count_tr1 + j,
                transformer_id=2,
                reading_sequence=j,
                voltage=110.0 + (j * 0.1),
                current=8.0 + (j * 0.1),
                temperature=55.0 + (j * 0.05),
                timestamp=base_time + timedelta(hours=j * 2),
            )
            r.transformer = self.tx2
            self.readings.append(r)

    async def get_transformer_by_identifier(self, identifier: str) -> Optional[Transformer]:
        cleaned = str(identifier).strip()
        if cleaned in ("TR-001", "1"):
            return self.tx1
        if cleaned in ("TR-002", "2"):
            return self.tx2
        return None

    def _filter_records(
        self,
        transformer_db_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TransformerReading]:
        filtered = self.readings
        if transformer_db_id is not None:
            filtered = [r for r in filtered if r.transformer_id == transformer_db_id]
        if start_time is not None:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        if end_time is not None:
            filtered = [r for r in filtered if r.timestamp <= end_time]
        return filtered

    async def count_history_readings(
        self,
        transformer_db_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        return len(self._filter_records(transformer_db_id, start_time, end_time))

    async def get_history_readings(
        self,
        transformer_db_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sort_by: str = "timestamp",
        order: str = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> List[TransformerReading]:
        records = self._filter_records(transformer_db_id, start_time, end_time)

        key_fn = (
            (lambda r: r.reading_sequence)
            if sort_by == "sequence"
            else (lambda r: r.timestamp)
        )
        reverse = order.lower() == "desc"
        sorted_records = sorted(records, key=key_fn, reverse=reverse)

        return sorted_records[offset: offset + limit]


# ---------------------------------------------------------------------------
# Fixtures & Overrides
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_repo() -> FakeHistoryReadingRepo:
    return FakeHistoryReadingRepo()


@pytest_asyncio.fixture(autouse=True)
async def setup_dependencies(fake_repo: FakeHistoryReadingRepo, monkeypatch):
    async def _fake_async_db():
        yield MagicMock()

    app.dependency_overrides[get_async_db] = _fake_async_db

    monkeypatch.setattr(
        "app.services.history_reading_service.AsyncReadingRepository",
        lambda session: fake_repo
    )

    yield

    app.dependency_overrides.pop(get_async_db, None)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_history_default_pagination(client: AsyncClient):
    """
    Default query should return 20 records (limit=20) with valid pagination metadata.
    """
    resp = await client.get("/api/readings/history")
    assert resp.status_code == 200

    body = resp.json()
    assert body["success"] is True
    assert "data" in body
    assert "pagination" in body

    data = body["data"]
    assert len(data) == 20

    pagination = body["pagination"]
    assert pagination["page"] == 1
    assert pagination["limit"] == 20
    assert pagination["total_items"] == 75  # 50 + 25
    assert pagination["total_pages"] == 4   # ceil(75/20)
    assert pagination["has_next"] is True
    assert pagination["has_prev"] is False


@pytest.mark.asyncio
async def test_get_history_with_transformer_filter(client: AsyncClient):
    """
    Filtering by transformer_id=TR-001 should only return records for TR-001.
    """
    resp = await client.get("/api/readings/history?transformer_id=TR-001&limit=10")
    assert resp.status_code == 200

    body = resp.json()
    data = body["data"]
    pagination = body["pagination"]

    assert len(data) == 10
    for item in data:
        assert item["transformer_id"] == "TR-001"

    assert pagination["total_items"] == 50
    assert pagination["total_pages"] == 5
    assert pagination["has_next"] is True
    assert pagination["has_prev"] is False


@pytest.mark.asyncio
async def test_get_history_invalid_transformer_returns_404(client: AsyncClient):
    """
    Filtering by a non-existent transformer returns HTTP 404.
    """
    resp = await client.get("/api/readings/history?transformer_id=UNKNOWN-999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert "Transformer" in body["error"]["message"]


@pytest.mark.asyncio
async def test_get_history_sorting_by_timestamp(client: AsyncClient):
    """
    Verify ascending and descending ordering by timestamp.
    """
    # Descending (default)
    resp_desc = await client.get("/api/readings/history?transformer_id=TR-001&limit=5&sort_by=timestamp&order=desc")
    assert resp_desc.status_code == 200
    timestamps_desc = [r["timestamp"] for r in resp_desc.json()["data"]]
    assert timestamps_desc == sorted(timestamps_desc, reverse=True)

    # Ascending
    resp_asc = await client.get("/api/readings/history?transformer_id=TR-001&limit=5&sort_by=timestamp&order=asc")
    assert resp_asc.status_code == 200
    timestamps_asc = [r["timestamp"] for r in resp_asc.json()["data"]]
    assert timestamps_asc == sorted(timestamps_asc)


@pytest.mark.asyncio
async def test_get_history_sorting_by_sequence(client: AsyncClient):
    """
    Verify ascending and descending ordering by sequence.
    """
    # Descending
    resp_desc = await client.get("/api/readings/history?transformer_id=TR-001&limit=5&sort_by=sequence&order=desc")
    assert resp_desc.status_code == 200
    seqs_desc = [r["sequence"] for r in resp_desc.json()["data"]]
    assert seqs_desc == [50, 49, 48, 47, 46]

    # Ascending
    resp_asc = await client.get("/api/readings/history?transformer_id=TR-001&limit=5&sort_by=sequence&order=asc")
    assert resp_asc.status_code == 200
    seqs_asc = [r["sequence"] for r in resp_asc.json()["data"]]
    assert seqs_asc == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_get_history_pagination_pages_and_boundaries(client: AsyncClient):
    """
    Verify navigation flags on first, middle, and past-boundary pages.
    """
    # Page 1
    r1 = await client.get("/api/readings/history?transformer_id=TR-001&page=1&limit=20")
    p1 = r1.json()["pagination"]
    assert p1["has_next"] is True
    assert p1["has_prev"] is False

    # Page 2
    r2 = await client.get("/api/readings/history?transformer_id=TR-001&page=2&limit=20")
    p2 = r2.json()["pagination"]
    assert p2["has_next"] is True
    assert p2["has_prev"] is True

    # Page 3 (final page for 50 items with limit=20)
    r3 = await client.get("/api/readings/history?transformer_id=TR-001&page=3&limit=20")
    p3 = r3.json()["pagination"]
    assert p3["has_next"] is False
    assert p3["has_prev"] is True
    assert len(r3.json()["data"]) == 10

    # Page 4 (beyond bounds)
    r4 = await client.get("/api/readings/history?transformer_id=TR-001&page=4&limit=20")
    assert r4.status_code == 200
    p4 = r4.json()["pagination"]
    assert r4.json()["data"] == []
    assert p4["has_next"] is False
    assert p4["has_prev"] is True


@pytest.mark.asyncio
async def test_get_history_time_range_filter(client: AsyncClient):
    """
    Verify date range boundaries filter records.
    """
    start = "2026-01-01T05:00:00Z"
    end = "2026-01-01T10:00:00Z"

    resp = await client.get(
        f"/api/readings/history?transformer_id=TR-001&start_time={start}&end_time={end}&limit=50"
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 6  # Hours 5, 6, 7, 8, 9, 10
    for item in data:
        assert item["sequence"] in range(5, 11)


@pytest.mark.asyncio
async def test_get_history_validation_errors(client: AsyncClient):
    """
    Invalid query parameters should be rejected with 422 Unprocessable Entity.
    """
    # page < 1
    r_page = await client.get("/api/readings/history?page=0")
    assert r_page.status_code == 422

    # limit > 500
    r_limit = await client.get("/api/readings/history?limit=501")
    assert r_limit.status_code == 422

    # invalid sort_by
    r_sort = await client.get("/api/readings/history?sort_by=unsupported_col")
    assert r_sort.status_code == 422

    # invalid order
    r_order = await client.get("/api/readings/history?order=random")
    assert r_order.status_code == 422


@pytest.mark.asyncio
async def test_get_history_v1_alias_route(client: AsyncClient):
    """
    GET /api/v1/readings/history alias must return identical structure to /api/readings/history.
    """
    resp = await client.get("/api/v1/readings/history?transformer_id=TR-001&page=1&limit=5")
    assert resp.status_code == 200
    body = resp.json()

    assert body["success"] is True
    assert len(body["data"]) == 5
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["limit"] == 5
    assert body["pagination"]["total_items"] == 50
    assert body["pagination"]["total_pages"] == 10
    assert body["pagination"]["has_next"] is True
    assert body["pagination"]["has_prev"] is False

    item = body["data"][0]
    expected_keys = {"transformer_id", "voltage", "current", "temperature", "sequence", "timestamp"}
    assert expected_keys.issubset(item.keys())
