from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.data_access.reading_repo import ReadingRepository
from app.data_access.transformer_repo import TransformerRepository
from app.error_handling.exceptions import DatasetException
from app.schemas.dataset import (
    DatasetColumnInfo,
    DatasetInfoResponse,
    DatasetPreviewResponse,
    DatasetUploadResponse,
)


class DatasetService:
    def __init__(self, db: Session):
        self.db = db
        self.reading_repo = ReadingRepository(db)
        self.transformer_repo = TransformerRepository(db)

    def get_dataset_info(self) -> DatasetInfoResponse:
        csv_path = settings.resolved_sample_dataset_path
        if not csv_path.exists():
            raise DatasetException(f"Dataset file not found at {csv_path}")

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            raise DatasetException(f"Failed to inspect dataset file: {e!s}") from e

        column_details = []
        for col in df.columns:
            non_null = int(df[col].count())
            missing = int(df[col].isna().sum())
            column_details.append(
                DatasetColumnInfo(
                    name=str(col),
                    data_type=str(df[col].dtype),
                    non_null_count=non_null,
                    missing_count=missing,
                )
            )

        transformers_found = []
        if "transformer_id" in df.columns:
            transformers_found = sorted([str(t) for t in df["transformer_id"].unique()])

        time_start = None
        time_end = None
        if "timestamp" in df.columns:
            ts_series = pd.to_datetime(df["timestamp"], errors="coerce")
            valid_ts = ts_series.dropna()
            if not valid_ts.empty:
                time_start = valid_ts.min().to_pydatetime()
                time_end = valid_ts.max().to_pydatetime()

        loaded_in_db = self.reading_repo.count_total()

        return DatasetInfoResponse(
            filename=csv_path.name,
            total_records=len(df),
            columns=list(df.columns),
            column_details=column_details,
            transformers_found=transformers_found,
            time_range_start=time_start,
            time_range_end=time_end,
            loaded_in_db_records=loaded_in_db,
        )

    def preview_dataset(self, limit: int = 10) -> DatasetPreviewResponse:
        csv_path = settings.resolved_sample_dataset_path
        if not csv_path.exists():
            raise DatasetException(f"Dataset file not found at {csv_path}")

        df = pd.read_csv(csv_path)
        preview_rows = df.head(limit).to_dict(orient="records")

        return DatasetPreviewResponse(
            filename=csv_path.name,
            preview_limit=limit,
            total_records=len(df),
            columns=list(df.columns),
            rows=preview_rows,
        )

    def load_dataset_from_file_or_bytes(
        self, file_source: Any, filename: str
    ) -> DatasetUploadResponse:
        from app.ingestion.service import DatasetIngestionService

        service = DatasetIngestionService()
        report = service.ingest_sync(file_source, filename)
        return DatasetUploadResponse(
            filename=report.filename,
            rows_parsed=report.total_raw_rows,
            transformers_registered=len(report.transformers_detected),
            readings_stored=report.inserted_rows_count,
            warnings=(
                report.warnings
                + [f"Row {r.row_number}: {r.reason}" for r in report.rejected_records[:10]]
            ),
        )

    def seed_sample_if_empty(self) -> DatasetUploadResponse | None:
        total_readings = self.reading_repo.count_total()
        if total_readings > 0:
            return None  # Database already has data

        csv_path = settings.resolved_sample_dataset_path
        if not csv_path.exists():
            return None

        from app.ingestion.service import DatasetIngestionService

        service = DatasetIngestionService()
        report = service.ingest_sync(csv_path, csv_path.name)
        return DatasetUploadResponse(
            filename=report.filename,
            rows_parsed=report.total_raw_rows,
            transformers_registered=len(report.transformers_detected),
            readings_stored=report.inserted_rows_count,
            warnings=report.warnings,
        )

    def clear_dataset(self) -> dict:
        cleared_readings = self.reading_repo.clear_all()
        return {
            "cleared_readings": cleared_readings,
            "status": "dataset_cleared",
            "message": f"Successfully cleared {cleared_readings} sensor readings from database.",
        }
