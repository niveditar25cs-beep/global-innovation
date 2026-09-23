"""
Comprehensive test suite for the Network API and NetworkService.

Tests:
1. Network summary retrieval (populated network with status breakdown and load)
2. Network topology retrieval (nodes with specifications and latest reading snapshot)
3. Empty network handling (zero transformers returns 0 nodes and None load without error)
4. Degraded network status detection (offline/maintenance transformers degrade system status)
5. Invalid/corrupted reading data handling (None load percentage, missing readings handled gracefully)
6. Legacy API prefix backward compatibility (/api/network/summary & /api/network/topology)
"""
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.data_access.database import get_db
from app.services.network_service import NetworkService
from app.schemas.network import (
    NetworkSummaryResponse,
    NetworkStatusBreakdown,
    NetworkTopologyResponse,
    NetworkNode,
)
from app.schemas.reading import ReadingResponse


# ---------------------------------------------------------------------------
# Dependency Overrides & Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def override_db_dependency():
    """Mock get_db for all network tests."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture()
async def client():
    """AsyncClient wired directly to the FastAPI ASGI application."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def _mock_summary_response(
    total: int = 3,
    operational: int = 2,
    maintenance: int = 1,
    offline: int = 0,
    avg_load: float = 72.5,
    system_status: str = "operational",
) -> NetworkSummaryResponse:
    return NetworkSummaryResponse(
        total_transformers=total,
        status_breakdown=NetworkStatusBreakdown(
            operational=operational,
            maintenance=maintenance,
            offline=offline,
        ),
        total_historical_readings=150,
        unique_locations=["Substation Alpha", "Substation Beta"],
        average_system_load_pct=avg_load,
        system_status=system_status,
    )


from datetime import datetime

def _mock_topology_response(total_nodes: int = 2) -> NetworkTopologyResponse:
    nodes = [
        NetworkNode(
            id="T001",
            name="Main Feeder Alpha",
            location="Substation Alpha",
            rating_mva=25.0,
            voltage_rating_kv=132.0,
            status="operational",
            latest_reading=ReadingResponse(
                id=1,
                transformer_id="T001",
                timestamp=datetime(2026, 9, 20, 0, 0, 0),
                voltage_kv=132.5,
                current_a=350.0,
                load_percentage=70.0,
                oil_temperature_c=65.0,
                winding_temperature_c=72.0,
                oil_level_pct=90.0,
                vibration_mm_s=1.2,
                dissolved_gas_ppm=15.0,
                ambient_temperature_c=25.0,
                humidity_pct=55.0,
            ),
        ),
        NetworkNode(
            id="T002",
            name="Secondary Feeder Beta",
            location="Substation Beta",
            rating_mva=15.0,
            voltage_rating_kv=66.0,
            status="operational",
            latest_reading=None,
        ),
    ]
    return NetworkTopologyResponse(
        total_nodes=total_nodes,
        nodes=nodes[:total_nodes],
    )


# ---------------------------------------------------------------------------
# 1. Network Summary Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_network_summary_populated(client: AsyncClient):
    """GET /api/v1/network/summary returns 200 with complete summary statistics."""
    mock_summary = _mock_summary_response()

    with patch.object(NetworkService, "get_network_summary", return_value=mock_summary):
        resp = await client.get("/api/v1/network/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["total_transformers"] == 3
    assert data["status_breakdown"]["operational"] == 2
    assert data["status_breakdown"]["maintenance"] == 1
    assert data["status_breakdown"]["offline"] == 0
    assert data["average_system_load_pct"] == 72.5
    assert data["system_status"] == "operational"
    assert "Substation Alpha" in data["unique_locations"]


@pytest.mark.asyncio
async def test_get_network_summary_legacy_route(client: AsyncClient):
    """GET /api/network/summary returns backward-compatible 200 response."""
    mock_summary = _mock_summary_response()

    with patch.object(NetworkService, "get_network_summary", return_value=mock_summary):
        resp = await client.get("/api/network/summary")

    assert resp.status_code == 200
    assert resp.json()["success"] is True


# ---------------------------------------------------------------------------
# 2. Network Topology Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_network_topology_populated(client: AsyncClient):
    """GET /api/v1/network/topology returns 200 with node list and latest readings."""
    mock_topology = _mock_topology_response(total_nodes=2)

    with patch.object(NetworkService, "get_network_topology", return_value=mock_topology):
        resp = await client.get("/api/v1/network/topology")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["total_nodes"] == 2
    assert len(data["nodes"]) == 2

    # Node 1 has a latest reading
    node1 = data["nodes"][0]
    assert node1["id"] == "T001"
    assert node1["rating_mva"] == 25.0
    assert node1["latest_reading"]["voltage_kv"] == 132.5

    # Node 2 has None for latest reading
    node2 = data["nodes"][1]
    assert node2["id"] == "T002"
    assert node2["latest_reading"] is None


@pytest.mark.asyncio
async def test_get_network_topology_legacy_route(client: AsyncClient):
    """GET /api/network/topology returns backward-compatible 200 response."""
    mock_topology = _mock_topology_response(total_nodes=1)

    with patch.object(NetworkService, "get_network_topology", return_value=mock_topology):
        resp = await client.get("/api/network/topology")

    assert resp.status_code == 200
    assert resp.json()["success"] is True


# ---------------------------------------------------------------------------
# 3. Empty Network Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_network_empty_state_summary(client: AsyncClient):
    """When the database has 0 transformers, summary returns 0s and None load without error."""
    mock_db = MagicMock()
    service = NetworkService(mock_db)

    # Mock repos returning 0 entities
    service.transformer_repo.get_all = MagicMock(return_value=[])
    service.reading_repo.count_total = MagicMock(return_value=0)
    service.reading_repo.get_all_latest_readings = MagicMock(return_value=[])

    with patch("app.controllers.network_controller.NetworkService", return_value=service):
        resp = await client.get("/api/v1/network/summary")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_transformers"] == 0
    assert data["status_breakdown"] == {"operational": 0, "maintenance": 0, "offline": 0}
    assert data["total_historical_readings"] == 0
    assert data["unique_locations"] == []
    assert data["average_system_load_pct"] is None
    assert data["system_status"] == "operational"


@pytest.mark.asyncio
async def test_network_empty_state_topology(client: AsyncClient):
    """When the database has 0 transformers, topology returns 0 nodes."""
    mock_db = MagicMock()
    service = NetworkService(mock_db)

    service.transformer_repo.get_all = MagicMock(return_value=[])
    service.reading_repo.get_all_latest_readings = MagicMock(return_value=[])

    with patch("app.controllers.network_controller.NetworkService", return_value=service):
        resp = await client.get("/api/v1/network/topology")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_nodes"] == 0
    assert data["nodes"] == []


# ---------------------------------------------------------------------------
# 4. Degraded Network Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_network_degraded_when_offline_transformers(client: AsyncClient):
    """Network summary reports system_status='degraded' when at least one transformer is offline."""
    mock_summary = _mock_summary_response(
        total=5,
        operational=3,
        maintenance=1,
        offline=1,
        system_status="degraded",
    )

    with patch.object(NetworkService, "get_network_summary", return_value=mock_summary):
        resp = await client.get("/api/v1/network/summary")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["system_status"] == "degraded"
    assert data["status_breakdown"]["offline"] == 1


# ---------------------------------------------------------------------------
# 5. Invalid / Partial Data Resilience in NetworkService
# ---------------------------------------------------------------------------

def test_network_service_handles_none_loads_and_missing_locations():
    """
    Direct service unit test:
    - Transformers with None location must not crash unique_locations.
    - Readings with load_percentage = None must not cause ZeroDivisionError.
    """
    mock_db = MagicMock()
    service = NetworkService(mock_db)

    # 2 transformers: one with None location, one offline
    t1 = MagicMock()
    t1.id = 1
    t1.transformer_id = "TX-01"
    t1.name = "TX-01"
    t1.location = None  # None location
    t1.status = "operational"

    t2 = MagicMock()
    t2.id = 2
    t2.transformer_id = "TX-02"
    t2.name = "TX-02"
    t2.location = "Grid Zone 3"
    t2.status = "offline"

    # Readings: one with None load, one with 80.0 load
    r1 = MagicMock()
    r1.transformer_id = 1
    r1.load_percentage = None  # None load

    r2 = MagicMock()
    r2.transformer_id = 2
    r2.load_percentage = 80.0

    service.transformer_repo.get_all = MagicMock(return_value=[t1, t2])
    service.reading_repo.count_total = MagicMock(return_value=2)
    service.reading_repo.get_all_latest_readings = MagicMock(return_value=[r1, r2])

    summary = service.get_network_summary()
    assert summary.total_transformers == 2
    assert summary.unique_locations == ["Grid Zone 3"]
    assert summary.average_system_load_pct == 80.0
    assert summary.system_status == "degraded"


def test_network_service_all_none_loads_returns_none_avg():
    """When all latest readings have load_percentage = None, avg_load is None."""
    mock_db = MagicMock()
    service = NetworkService(mock_db)

    t1 = MagicMock()
    t1.id = 1
    t1.transformer_id = "TX-01"
    t1.location = "Site A"
    t1.status = "operational"

    r1 = MagicMock()
    r1.transformer_id = 1
    r1.load_percentage = None

    service.transformer_repo.get_all = MagicMock(return_value=[t1])
    service.reading_repo.count_total = MagicMock(return_value=1)
    service.reading_repo.get_all_latest_readings = MagicMock(return_value=[r1])

    summary = service.get_network_summary()
    assert summary.average_system_load_pct is None
    assert summary.system_status == "operational"
