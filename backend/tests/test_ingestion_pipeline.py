"""
Test suite for the Transformer Dataset Ingestion Pipeline.

Tests:
1. Valid dataset ingestion (valid schema, values, sequence generation, persistence)
2. Missing columns (schema validation rejection)
3. Invalid numerical values (quarantine of non-numeric/corrupted rows while valid rows succeed)
4. Missing values (quarantine of rows with missing core fields without fake imputation)
5. Duplicate records & Idempotence (re-importing same dataset does not duplicate records)
6. Empty dataset (0-byte and header-only files handled gracefully)
"""
import io
import pytest
from datetime import datetime, timezone
from sqlalchemy import select, delete

from app.data_access.database import AsyncSessionLocal
from app.models.transformer import Transformer
from app.models.reading import TransformerReading
from app.ingestion.pipeline import DatasetIngestionPipeline
from app.ingestion.service import DatasetIngestionService


@pytest.fixture
def pipeline():
    return DatasetIngestionPipeline(batch_size=100)


@pytest.fixture
def service():
    return DatasetIngestionService(batch_size=100)


# ---------------------------------------------------------------------------
# 1. Valid Dataset Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_valid_dataset(pipeline):
    """Verify that a well-formed CSV is parsed, sequenced, and stored in PostgreSQL."""
    csv_content = (
        "transformer_id,timestamp,voltage_kv,current_a,oil_temperature_c,vibration_mm_s\n"
        "TEST-VAL-01,2026-09-20T00:00:00,132.5,350.0,65.0,1.2\n"
        "TEST-VAL-01,2026-09-20T01:00:00,133.0,360.5,66.2,1.3\n"
        "TEST-VAL-02,2026-09-20T00:00:00,66.1,210.0,58.0,0.9\n"
    )

    # Clean up prior test data if any
    async with AsyncSessionLocal() as session:
        sub_stmt = select(Transformer.id).where(Transformer.transformer_id.in_(["TEST-VAL-01", "TEST-VAL-02"]))
        tx_ids = (await session.execute(sub_stmt)).scalars().all()
        if tx_ids:
            await session.execute(delete(TransformerReading).where(TransformerReading.transformer_id.in_(tx_ids)))
            await session.execute(delete(Transformer).where(Transformer.id.in_(tx_ids)))
            await session.commit()

    report = await pipeline.ingest_source(
        source=csv_content.encode("utf-8"),
        filename="valid_test.csv"
    )

    assert report.total_raw_rows == 3
    assert report.valid_rows_count == 3
    assert report.inserted_rows_count == 3
    assert report.rejected_rows_count == 0
    assert report.skipped_duplicates_count == 0
    assert set(report.transformers_detected) == {"TEST-VAL-01", "TEST-VAL-02"}

    # Verify database state
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Transformer)
            .where(Transformer.transformer_id == "TEST-VAL-01")
        )
        tx = (await session.execute(stmt)).scalar_one()
        assert tx is not None

        readings_stmt = (
            select(TransformerReading)
            .where(TransformerReading.transformer_id == tx.id)
            .order_by(TransformerReading.reading_sequence)
        )
        readings = (await session.execute(readings_stmt)).scalars().all()
        assert len(readings) == 2
        assert readings[0].reading_sequence == 1
        assert readings[1].reading_sequence == 2
        assert readings[0].voltage == 132.5
        assert readings[0].current == 350.0
        assert readings[0].temperature == 65.0
        assert readings[0].sensor_data.get("vibration_mm_s") == 1.2


# ---------------------------------------------------------------------------
# 2. Missing Columns Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_missing_required_columns(pipeline):
    """Verify that a CSV missing required columns (e.g. voltage) is rejected at schema detection."""
    # Missing 'voltage' column
    csv_missing_voltage = (
        "transformer_id,timestamp,current_a,oil_temperature_c\n"
        "TEST-MC-01,2026-09-20T00:00:00,350.0,65.0\n"
    )

    report = await pipeline.ingest_source(
        source=csv_missing_voltage.encode("utf-8"),
        filename="missing_voltage.csv"
    )

    assert report.total_raw_rows == 1
    assert report.inserted_rows_count == 0
    assert len(report.warnings) > 0
    assert any("voltage" in w.lower() for w in report.warnings)

    # Missing 'transformer_id' column
    csv_missing_tx_id = (
        "timestamp,voltage_kv,current_a,oil_temperature_c\n"
        "2026-09-20T00:00:00,132.0,350.0,65.0\n"
    )

    report2 = await pipeline.ingest_source(
        source=csv_missing_tx_id.encode("utf-8"),
        filename="missing_tx_id.csv"
    )

    assert report2.inserted_rows_count == 0
    assert len(report2.warnings) > 0
    assert any("transformer_id" in w.lower() for w in report2.warnings)


# ---------------------------------------------------------------------------
# 3. Invalid Numerical Values Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invalid_numerical_values(pipeline):
    """Verify that rows with non-numeric / corrupt values are quarantined while valid rows succeed."""
    csv_content = (
        "transformer_id,timestamp,voltage_kv,current_a,oil_temperature_c\n"
        "TEST-NUM-01,2026-09-20T00:00:00,132.0,350.0,65.0\n"
        "TEST-NUM-01,2026-09-20T01:00:00,NOT_A_VOLTAGE,350.0,65.0\n"
        "TEST-NUM-01,2026-09-20T02:00:00,132.0,NaN,65.0\n"
        "TEST-NUM-01,2026-09-20T03:00:00,132.0,350.0,BAD_TEMP\n"
        "TEST-NUM-01,2026-09-20T04:00:00,133.5,355.0,67.0\n"
    )

    # Clean up prior test data
    async with AsyncSessionLocal() as session:
        sub_stmt = select(Transformer.id).where(Transformer.transformer_id == "TEST-NUM-01")
        tx_ids = (await session.execute(sub_stmt)).scalars().all()
        if tx_ids:
            await session.execute(delete(TransformerReading).where(TransformerReading.transformer_id.in_(tx_ids)))
            await session.execute(delete(Transformer).where(Transformer.id.in_(tx_ids)))
            await session.commit()

    report = await pipeline.ingest_source(
        source=csv_content.encode("utf-8"),
        filename="invalid_numbers.csv"
    )

    assert report.total_raw_rows == 5
    assert report.valid_rows_count == 2  # Row 1 and Row 5
    assert report.rejected_rows_count == 3  # Rows 2, 3, 4
    assert report.inserted_rows_count == 2

    # Verify rejection reasons
    reasons = [r.reason for r in report.rejected_records]
    assert any("voltage" in r.lower() for r in reasons)
    assert any("current" in r.lower() for r in reasons)
    assert any("temperature" in r.lower() for r in reasons)


# ---------------------------------------------------------------------------
# 4. Missing Values Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_missing_values_rejected_not_imputed(pipeline):
    """Verify that rows with missing required fields are rejected, never imputed with fake data."""
    csv_content = (
        "transformer_id,timestamp,voltage_kv,current_a,oil_temperature_c\n"
        ",2026-09-20T00:00:00,132.0,350.0,65.0\n"  # missing transformer_id
        "TEST-MISS-01,,132.0,350.0,65.0\n"         # missing timestamp
        "TEST-MISS-01,2026-09-20T02:00:00,,350.0,65.0\n"  # missing voltage
        "TEST-MISS-01,2026-09-20T03:00:00,132.0,,65.0\n"  # missing current
        "TEST-MISS-01,2026-09-20T04:00:00,132.0,350.0,\n"  # missing temperature
        "TEST-MISS-01,2026-09-20T05:00:00,134.0,360.0,66.0\n"  # valid
    )

    # Clean up
    async with AsyncSessionLocal() as session:
        sub_stmt = select(Transformer.id).where(Transformer.transformer_id == "TEST-MISS-01")
        tx_ids = (await session.execute(sub_stmt)).scalars().all()
        if tx_ids:
            await session.execute(delete(TransformerReading).where(TransformerReading.transformer_id.in_(tx_ids)))
            await session.execute(delete(Transformer).where(Transformer.id.in_(tx_ids)))
            await session.commit()

    report = await pipeline.ingest_source(
        source=csv_content.encode("utf-8"),
        filename="missing_values.csv"
    )

    assert report.total_raw_rows == 6
    assert report.rejected_rows_count == 5  # Exactly 5 rows missing required data
    assert report.valid_rows_count == 1     # Only the 6th row is valid
    assert report.inserted_rows_count == 1

    # Verify that the single inserted record has the actual provided values, not hardcoded defaults
    async with AsyncSessionLocal() as session:
        stmt = (
            select(TransformerReading)
            .join(Transformer, Transformer.id == TransformerReading.transformer_id)
            .where(Transformer.transformer_id == "TEST-MISS-01")
        )
        saved = (await session.execute(stmt)).scalars().all()
        assert len(saved) == 1
        assert saved[0].voltage == 134.0
        assert saved[0].current == 360.0
        assert saved[0].temperature == 66.0


# ---------------------------------------------------------------------------
# 5. Duplicate Records & Idempotence Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duplicate_records_and_idempotence(pipeline):
    """Verify that importing the same dataset twice does not duplicate records in PostgreSQL."""
    csv_content = (
        "transformer_id,timestamp,voltage_kv,current_a,oil_temperature_c\n"
        "TEST-IDEMP-01,2026-09-20T00:00:00,130.0,340.0,62.0\n"
        "TEST-IDEMP-01,2026-09-20T01:00:00,131.0,345.0,63.0\n"
        "TEST-IDEMP-01,2026-09-20T02:00:00,132.0,350.0,64.0\n"
    )

    # Clean up
    async with AsyncSessionLocal() as session:
        sub_stmt = select(Transformer.id).where(Transformer.transformer_id == "TEST-IDEMP-01")
        tx_ids = (await session.execute(sub_stmt)).scalars().all()
        if tx_ids:
            await session.execute(delete(TransformerReading).where(TransformerReading.transformer_id.in_(tx_ids)))
            await session.execute(delete(Transformer).where(Transformer.id.in_(tx_ids)))
            await session.commit()

    # Pass 1: Initial import
    report1 = await pipeline.ingest_source(
        source=csv_content.encode("utf-8"),
        filename="idempotence_test.csv"
    )
    assert report1.total_raw_rows == 3
    assert report1.valid_rows_count == 3
    assert report1.inserted_rows_count == 3
    assert report1.skipped_duplicates_count == 0

    # Pass 2: Re-import exact same CSV
    report2 = await pipeline.ingest_source(
        source=csv_content.encode("utf-8"),
        filename="idempotence_test.csv"
    )
    assert report2.total_raw_rows == 3
    assert report2.valid_rows_count == 3
    assert report2.inserted_rows_count == 0  # Zero new records inserted!
    assert report2.skipped_duplicates_count == 3  # All 3 recognized as duplicates

    # Pass 3: Verify PostgreSQL record count is still 3
    async with AsyncSessionLocal() as session:
        stmt = (
            select(TransformerReading)
            .join(Transformer, Transformer.id == TransformerReading.transformer_id)
            .where(Transformer.transformer_id == "TEST-IDEMP-01")
        )
        saved = (await session.execute(stmt)).scalars().all()
        assert len(saved) == 3


# ---------------------------------------------------------------------------
# 6. Empty Dataset Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_empty_dataset_handling(pipeline):
    """Verify that completely empty or header-only datasets are handled gracefully without errors."""
    # 6a: 0-byte content
    report_empty = await pipeline.ingest_source(
        source=b"",
        filename="empty_0byte.csv"
    )
    assert report_empty.total_raw_rows == 0
    assert report_empty.inserted_rows_count == 0
    assert len(report_empty.warnings) > 0

    # 6b: Header only (0 data rows)
    header_only = "transformer_id,timestamp,voltage_kv,current_a,oil_temperature_c\n"
    report_header = await pipeline.ingest_source(
        source=header_only.encode("utf-8"),
        filename="header_only.csv"
    )
    assert report_header.total_raw_rows == 0
    assert report_header.inserted_rows_count == 0
    assert len(report_header.warnings) > 0
