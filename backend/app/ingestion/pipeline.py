"""
Robust dataset ingestion pipeline.

Architecture:
CSV -> Schema Detection -> Validation & Cleaning -> Transformation & Ordering
-> Deduplication -> PostgreSQL

Requirements:
- Detect dataset schema
- Validate required columns
- Validate numerical values (no electrical thresholds)
- Handle missing values safely (no hardcoded readings)
- Detect malformed rows and quarantine them
- Preserve transformer IDs as exact strings
- Preserve dataset ordering
- Generate deterministic reading sequence
- Prevent duplicate imports (idempotent)
- Log rejected records
- Store valid records in PostgreSQL
"""

import io
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.database import AsyncSessionLocal
from app.ingestion.models import IngestionReport, ProcessedReading, RejectedRecord
from app.ingestion.schema import REQUIRED_COLUMNS, detect_and_normalize_columns
from app.ingestion.validator import validate_and_transform_row
from app.models.reading import TransformerReading
from app.models.transformer import Transformer

logger = logging.getLogger(__name__)


class DatasetIngestionPipeline:
    """
    Production-grade, reusable dataset ingestion pipeline.
    """

    def __init__(self, batch_size: int = 500):
        self.batch_size = batch_size

    def read_csv_safely(
        self, source: str | Path | bytes | io.IOBase, filename: str = "dataset.csv"
    ) -> tuple[pd.DataFrame | None, list[str]]:
        """
        Safely load CSV data using multiple encoding fallbacks.
        Never crashes on corrupted encoding or bad lines.
        """
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        warnings: list[str] = []
        df = None
        last_error = None

        for enc in encodings:
            try:
                if isinstance(source, (str, Path)):
                    path = Path(source)
                    if not path.exists():
                        return None, [f"File not found: {path}"]
                    if path.stat().st_size == 0:
                        return pd.DataFrame(), ["Dataset file is empty (0 bytes)."]
                    df = pd.read_csv(path, encoding=enc, on_bad_lines="skip")
                elif isinstance(source, (bytes, bytearray)):
                    if len(source) == 0:
                        return pd.DataFrame(), ["Dataset content is empty (0 bytes)."]
                    df = pd.read_csv(io.BytesIO(source), encoding=enc, on_bad_lines="skip")
                elif hasattr(source, "read"):
                    content = source.read()
                    if isinstance(content, str):
                        if not content.strip():
                            return pd.DataFrame(), ["Dataset stream is empty."]
                        df = pd.read_csv(io.StringIO(content), on_bad_lines="skip")
                    else:
                        if len(content) == 0:
                            return pd.DataFrame(), ["Dataset stream is empty."]
                        df = pd.read_csv(io.BytesIO(content), encoding=enc, on_bad_lines="skip")
                break
            except Exception as e:
                last_error = e

        if df is None:
            err_msg = f"Failed to read CSV with supported encodings: {last_error}"
            logger.error(err_msg)
            return None, [err_msg]

        return df, warnings

    async def ingest_dataframe(
        self, df: pd.DataFrame, filename: str, session: AsyncSession, dry_run: bool = False
    ) -> IngestionReport:
        """
        Ingest a loaded DataFrame through validation, deduplication, and persistence.
        """
        start_time = time.time()
        report = IngestionReport(filename=filename, total_raw_rows=len(df), dry_run=dry_run)

        if df.empty:
            report.warnings.append("Dataset is empty. No records to process.")
            report.duration_seconds = time.time() - start_time
            return report

        # Step 1: Detect schema & map columns
        col_mapping, missing_required = detect_and_normalize_columns(list(df.columns))

        if missing_required:
            report.warnings.append(
                f"Missing required columns: {missing_required}. "
                f"Required schema fields: {sorted(REQUIRED_COLUMNS)}. "
                f"Detected columns: {list(df.columns)}"
            )
            logger.warning(
                f"Ingestion rejected for {filename}: Missing required columns {missing_required}"
            )
            report.duration_seconds = time.time() - start_time
            return report

        # Rename columns to canonical names
        df_normalized = df.rename(columns=col_mapping)

        # Step 2: Validate rows & quarantine malformed/missing records
        valid_readings: list[ProcessedReading] = []

        for idx, row in df_normalized.iterrows():
            row_num = idx + 2  # 1-indexed row in CSV including header
            reading, rejected = validate_and_transform_row(row.to_dict(), row_num)
            if rejected:
                report.rejected_records.append(rejected)
            elif reading:
                valid_readings.append(reading)

        report.valid_rows_count = len(valid_readings)
        report.rejected_rows_count = len(report.rejected_records)

        if not valid_readings:
            report.warnings.append("No valid records found in dataset after validation.")
            report.duration_seconds = time.time() - start_time
            return report

        # Detect distinct transformers
        detected_tr_ids = sorted({r.transformer_id for r in valid_readings})
        report.transformers_detected = detected_tr_ids

        # Step 3: Group by transformer and sort deterministically
        # Sort key preserves timestamp chronology and original dataset row ordering
        readings_by_tx: dict[str, list[ProcessedReading]] = {tr: [] for tr in detected_tr_ids}
        for r in valid_readings:
            readings_by_tx[r.transformer_id].append(r)

        for tr_id in detected_tr_ids:
            readings_by_tx[tr_id].sort(key=lambda x: (x.timestamp, x.original_row_number))

        # Step 4: Database Synchronization (Transformers auto-registration & Deduplication)
        tx_id_map: dict[str, int] = {}

        # Look up existing transformers
        tx_stmt = select(Transformer).where(Transformer.transformer_id.in_(detected_tr_ids))
        existing_txs = (await session.execute(tx_stmt)).scalars().all()
        for tx in existing_txs:
            tx_id_map[tx.transformer_id] = tx.id

        # Register new transformers if not present
        new_tx_created = False
        for tr_id in detected_tr_ids:
            if tr_id not in tx_id_map and not dry_run:
                new_tx = Transformer(
                    transformer_id=tr_id,
                    name=f"Transformer {tr_id}",
                    metadata_payload={"source": "automated_dataset_ingestion"},
                )
                session.add(new_tx)
                new_tx_created = True

        if new_tx_created and not dry_run:
            await session.commit()
            # Refresh mapping
            refreshed_txs = (await session.execute(tx_stmt)).scalars().all()
            for tx in refreshed_txs:
                tx_id_map[tx.transformer_id] = tx.id

        # Step 5: Check existing timestamps per transformer to prevent duplicates (Idempotent)
        readings_to_insert: list[TransformerReading] = []

        for tr_id, tr_readings in readings_by_tx.items():
            db_tx_id = tx_id_map.get(tr_id)

            existing_timestamps: set[datetime] = set()
            current_max_seq = 0

            if db_tx_id is not None:
                # Query timestamps to deduplicate
                # Using batch timestamp check
                ts_list = [r.timestamp for r in tr_readings]
                dup_stmt = (
                    select(TransformerReading.timestamp)
                    .where(TransformerReading.transformer_id == db_tx_id)
                    .where(TransformerReading.timestamp.in_(ts_list))
                )
                existing_res = await session.execute(dup_stmt)
                for row_ts in existing_res.scalars().all():
                    # Normalize to UTC for reliable comparison
                    if row_ts.tzinfo is None:
                        row_ts = row_ts.replace(tzinfo=UTC)
                    else:
                        row_ts = row_ts.astimezone(UTC)
                    existing_timestamps.add(row_ts)

                # Query current maximum sequence
                seq_stmt = select(func.max(TransformerReading.reading_sequence)).where(
                    TransformerReading.transformer_id == db_tx_id
                )
                current_max_seq = (await session.execute(seq_stmt)).scalar() or 0

            # Filter non-duplicate readings and assign deterministic sequence
            non_duplicate_readings: list[ProcessedReading] = []
            for r in tr_readings:
                if r.timestamp in existing_timestamps:
                    report.skipped_duplicates_count += 1
                    report.rejected_records.append(
                        RejectedRecord(
                            row_number=r.original_row_number,
                            reason=(
                                f"Duplicate reading: record for transformer '{r.transformer_id}' "
                                f"at timestamp '{r.timestamp.isoformat()}' "
                                "already exists in database"
                            ),
                            raw_values={
                                "transformer_id": r.transformer_id,
                                "timestamp": r.timestamp.isoformat(),
                                "voltage": r.voltage,
                                "current": r.current,
                                "temperature": r.temperature,
                            },
                        )
                    )
                else:
                    non_duplicate_readings.append(r)

            # Assign deterministic reading_sequence
            for idx_seq, r in enumerate(non_duplicate_readings):
                r.reading_sequence = current_max_seq + 1 + idx_seq

                if not dry_run and db_tx_id is not None:
                    readings_to_insert.append(
                        TransformerReading(
                            transformer_id=db_tx_id,
                            reading_sequence=r.reading_sequence,
                            voltage=r.voltage,
                            current=r.current,
                            temperature=r.temperature,
                            timestamp=r.timestamp,
                            sensor_data=r.sensor_data,
                        )
                    )

        # Step 6: Bulk insert new readings into PostgreSQL
        if not dry_run and readings_to_insert:
            for i in range(0, len(readings_to_insert), self.batch_size):
                chunk = readings_to_insert[i : i + self.batch_size]
                session.add_all(chunk)
                await session.flush()
            await session.commit()
            report.inserted_rows_count = len(readings_to_insert)
        elif dry_run:
            # In dry-run, count what would have been inserted
            report.inserted_rows_count = (
                sum(
                    len([r for r in readings if r.reading_sequence is not None])
                    for readings in readings_by_tx.values()
                )
                - report.skipped_duplicates_count
            )

        report.duration_seconds = time.time() - start_time
        return report

    async def ingest_source(
        self,
        source: str | Path | bytes | io.IOBase,
        filename: str | None = None,
        dry_run: bool = False,
        session: AsyncSession | None = None,
    ) -> IngestionReport:
        """
        High-level ingestion entry point for files, byte buffers, or IO streams.
        """
        if filename is None:
            filename = Path(source).name if isinstance(source, (str, Path)) else "dataset.csv"

        df, warnings = self.read_csv_safely(source, filename)
        if df is None:
            report = IngestionReport(filename=filename, dry_run=dry_run)
            report.warnings.extend(warnings)
            return report

        if session is not None:
            report = await self.ingest_dataframe(df, filename, session, dry_run=dry_run)
            report.warnings.extend(warnings)
            return report
        else:
            async with AsyncSessionLocal() as db_session:
                report = await self.ingest_dataframe(df, filename, db_session, dry_run=dry_run)
                report.warnings.extend(warnings)
                return report
