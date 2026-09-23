"""
Ingestion models and data structures.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RejectedRecord(BaseModel):
    """Details of a record rejected during ingestion."""

    row_number: int
    reason: str
    raw_values: dict[str, Any] = Field(default_factory=dict)


class ProcessedReading(BaseModel):
    """Clean, validated transformer reading ready for persistence."""

    transformer_id: str
    timestamp: datetime
    voltage: float
    current: float
    temperature: float
    reading_sequence: int | None = None
    sensor_data: dict[str, Any] = Field(default_factory=dict)
    original_row_number: int


class IngestionReport(BaseModel):
    """Comprehensive summary of an ingestion run."""

    filename: str
    total_raw_rows: int = 0
    valid_rows_count: int = 0
    inserted_rows_count: int = 0
    skipped_duplicates_count: int = 0
    rejected_rows_count: int = 0
    transformers_detected: list[str] = Field(default_factory=list)
    rejected_records: list[RejectedRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    dry_run: bool = False
    duration_seconds: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.rejected_rows_count == 0 and len(self.warnings) == 0

    def summary_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "total_raw_rows": self.total_raw_rows,
            "valid_rows": self.valid_rows_count,
            "inserted_rows": self.inserted_rows_count,
            "skipped_duplicates": self.skipped_duplicates_count,
            "rejected_rows": self.rejected_rows_count,
            "transformers": self.transformers_detected,
            "dry_run": self.dry_run,
            "duration_seconds": round(self.duration_seconds, 3),
            "warnings_count": len(self.warnings),
        }
