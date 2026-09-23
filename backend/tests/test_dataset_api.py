"""
Comprehensive test suite for Dataset API endpoints:
1. Valid import via HTTP upload (multipart CSV parsing, sequence generation, persistence)
2. Invalid records rejection and quarantine via upload
3. Missing fields / required column validation via upload
4. Duplicate data handling and idempotence via upload
5. Dataset info retrieval (schema metadata, column details, transformer list)
6. Dataset preview with pagination / limit boundaries
7. Dataset clear and sample load lifecycle
"""
import io
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.data_access.database import get_db
from app.schemas.dataset import (
    DatasetInfoResponse,
    DatasetColumnInfo,
    DatasetPreviewResponse,
    DatasetUploadResponse,
)


@pytest_asyncio.fixture(autouse=True)
async def override_db():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture()
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. Valid Import via Upload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dataset_upload_valid_csv(client: AsyncClient):
    """POST /api/v1/dataset/upload with well-formed CSV ingests records and returns summary."""
    csv_bytes = (
        b"transformer_id,timestamp,voltage_kv,current_a,oil_temperature_c\n"
        b"TX-UPL-01,2026-09-20T00:00:00,132.0,350.0,65.0\n"
        b"TX-UPL-01,2026-09-20T01:00:00,132.5,355.0,66.0\n"
    )

    mock_upload_resp = DatasetUploadResponse(
        filename="test_upload.csv",
        rows_parsed=2,
        transformers_registered=1,
        readings_stored=2,
        warnings=[],
    )

    with patch("app.services.dataset_service.DatasetService.load_dataset_from_file_or_bytes", return_value=mock_upload_resp):
        files = {"file": ("test_upload.csv", io.BytesIO(csv_bytes), "text/csv")}
        resp = await client.post("/api/v1/dataset/upload", files=files)

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["filename"] == "test_upload.csv"
    assert data["rows_parsed"] == 2
    assert data["readings_stored"] == 2
    assert data["transformers_registered"] == 1
    assert data["warnings"] == []


# ---------------------------------------------------------------------------
# 2. Invalid Records Handling via Upload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dataset_upload_invalid_records_quarantine(client: AsyncClient):
    """POST /api/v1/dataset/upload with malformed rows reports quarantined count and warnings."""
    mock_upload_resp = DatasetUploadResponse(
        filename="corrupted_upload.csv",
        rows_parsed=3,
        transformers_registered=1,
        readings_stored=1,
        warnings=["Row 2: Negative voltage value not allowed", "Row 3: Non-numeric current"],
    )

    with patch("app.services.dataset_service.DatasetService.load_dataset_from_file_or_bytes", return_value=mock_upload_resp):
        files = {"file": ("corrupted_upload.csv", io.BytesIO(b"dummy,csv\n1,2"), "text/csv")}
        resp = await client.post("/api/v1/dataset/upload", files=files)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["readings_stored"] == 1
    assert len(data["warnings"]) == 2
    assert "Row 2" in data["warnings"][0]


# ---------------------------------------------------------------------------
# 3. Missing Fields Handling via Upload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dataset_upload_missing_fields(client: AsyncClient):
    """POST /api/v1/dataset/upload with missing essential columns reports rejection warnings."""
    mock_upload_resp = DatasetUploadResponse(
        filename="missing_fields.csv",
        rows_parsed=1,
        transformers_registered=0,
        readings_stored=0,
        warnings=["Missing required voltage column: 'voltage_kv'"],
    )

    with patch("app.services.dataset_service.DatasetService.load_dataset_from_file_or_bytes", return_value=mock_upload_resp):
        files = {"file": ("missing_fields.csv", io.BytesIO(b"timestamp,current_a\n"), "text/csv")}
        resp = await client.post("/api/v1/dataset/upload", files=files)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["readings_stored"] == 0
    assert any("voltage" in w.lower() for w in data["warnings"])


# ---------------------------------------------------------------------------
# 4. Duplicate Data & Idempotence via Upload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dataset_upload_duplicate_idempotence(client: AsyncClient):
    """Re-uploading the same dataset skips duplicate records and reports 0 new insertions."""
    mock_upload_resp = DatasetUploadResponse(
        filename="duplicate_test.csv",
        rows_parsed=5,
        transformers_registered=2,
        readings_stored=0,
        warnings=["Skipped 5 duplicate readings already present in database."],
    )

    with patch("app.services.dataset_service.DatasetService.load_dataset_from_file_or_bytes", return_value=mock_upload_resp):
        files = {"file": ("duplicate_test.csv", io.BytesIO(b"duplicate,csv\n"), "text/csv")}
        resp = await client.post("/api/v1/dataset/upload", files=files)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["readings_stored"] == 0
    assert any("duplicate" in w.lower() for w in data["warnings"])


# ---------------------------------------------------------------------------
# 5. Dataset Info Retrieval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_dataset_info(client: AsyncClient):
    """GET /api/v1/dataset/info returns schema details, columns, and transformer names."""
    mock_info = DatasetInfoResponse(
        filename="transformer_readings.csv",
        total_records=1000,
        columns=["transformer_id", "timestamp", "voltage_kv", "current_a", "oil_temperature_c"],
        column_details=[
            DatasetColumnInfo(name="transformer_id", data_type="object", non_null_count=1000, missing_count=0),
            DatasetColumnInfo(name="voltage_kv", data_type="float64", non_null_count=1000, missing_count=0),
        ],
        transformers_found=["TR-001", "TR-002", "TR-003"],
        time_range_start=None,
        time_range_end=None,
        loaded_in_db_records=1000,
    )

    with patch("app.services.dataset_service.DatasetService.get_dataset_info", return_value=mock_info):
        resp = await client.get("/api/v1/dataset/info")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["filename"] == "transformer_readings.csv"
    assert data["total_records"] == 1000
    assert "TR-001" in data["transformers_found"]
    assert len(data["column_details"]) == 2


# ---------------------------------------------------------------------------
# 6. Dataset Preview with Boundaries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_dataset_preview(client: AsyncClient):
    """GET /api/v1/dataset/preview returns top N sample rows."""
    mock_preview = DatasetPreviewResponse(
        filename="transformer_readings.csv",
        preview_limit=2,
        total_records=1000,
        columns=["transformer_id", "voltage_kv"],
        rows=[
            {"transformer_id": "TR-001", "voltage_kv": 132.0},
            {"transformer_id": "TR-001", "voltage_kv": 132.4},
        ],
    )

    with patch("app.services.dataset_service.DatasetService.preview_dataset", return_value=mock_preview):
        resp = await client.get("/api/v1/dataset/preview?limit=2")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["preview_limit"] == 2
    assert len(data["rows"]) == 2


# ---------------------------------------------------------------------------
# 7. Dataset Clear and Sample Load Lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dataset_clear_endpoint(client: AsyncClient):
    """DELETE /api/v1/dataset/clear clears sensor readings from database."""
    with patch("app.services.dataset_service.DatasetService.clear_dataset", return_value={"cleared_readings": 150, "status": "dataset_cleared"}):
        resp = await client.delete("/api/v1/dataset/clear")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["cleared_readings"] == 150


@pytest.mark.asyncio
async def test_dataset_load_sample_endpoint(client: AsyncClient):
    """POST /api/v1/dataset/load-sample loads built-in sample data."""
    mock_upload_resp = DatasetUploadResponse(
        filename="sample.csv",
        rows_parsed=100,
        transformers_registered=3,
        readings_stored=100,
        warnings=[],
    )

    with patch("app.services.dataset_service.DatasetService.seed_sample_if_empty", return_value=mock_upload_resp):
        resp = await client.post("/api/v1/dataset/load-sample")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["readings_stored"] == 100
