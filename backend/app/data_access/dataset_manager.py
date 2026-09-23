import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import settings
from app.utils.csv_loader import DatasetParseResult, parse_and_validate_dataset

logger = logging.getLogger(__name__)


class TransformerDatasetManager:
    """
    Reusable Dataset / Data-Access Service.

    Provides independent, reliable dataset access for all backend services:
    - Loads transformer data from configured project location.
    - Validates dataset schema and structure.
    - Handles malformed/missing records without crashing.
    - Preserves exact Transformer IDs.
    - Parses numerical sensor readings (voltage, current, temperature, etc.).
    - Completely separate from API routes.
    """

    def __init__(self, data_path: Path | str | None = None):
        if data_path:
            self.data_path = Path(data_path)
        else:
            self.data_path = settings.resolved_sample_dataset_path

        self._cached_result: DatasetParseResult | None = None

    def load(self, force_reload: bool = False) -> DatasetParseResult:
        """Load and validate the dataset from the configured file path."""
        if self._cached_result is not None and not force_reload:
            return self._cached_result

        if not self.data_path.exists():
            logger.warning(f"Transformer dataset file does not exist at: {self.data_path}")
            empty_result = DatasetParseResult()
            empty_result.warnings.append(f"File not found at: {self.data_path}")
            self._cached_result = empty_result
            return empty_result

        logger.info(f"Loading transformer dataset from: {self.data_path}")
        result = parse_and_validate_dataset(self.data_path, filename=self.data_path.name)
        self._cached_result = result

        logger.info(
            f"Successfully parsed dataset: {len(result.valid_records)} valid records loaded, "
            f"{len(result.invalid_records)} invalid records quarantined, "
            f"{len(result.transformer_ids)} transformers detected: {result.transformer_ids}"
        )
        return result

    def get_records(
        self, transformer_id: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve clean, parsed dataset records, optionally filtered by transformer."""
        result = self.load()
        records = result.valid_records
        if transformer_id:
            records = [r for r in records if r["transformer_id"] == transformer_id]
        if limit is not None and limit > 0:
            records = records[:limit]
        return records

    def get_transformer_ids(self) -> list[str]:
        """Return list of distinct transformer IDs present in the dataset."""
        result = self.load()
        return result.transformer_ids

    def get_available_fields(self) -> list[str]:
        """Return list of columns/fields present in the loaded dataset."""
        result = self.load()
        return result.available_fields

    def get_record_count(self) -> int:
        """Return count of successfully parsed records."""
        result = self.load()
        return len(result.valid_records)

    def get_invalid_records(self) -> list[dict[str, Any]]:
        """Return audit trail of any malformed records that were safely skipped."""
        result = self.load()
        return result.invalid_records

    def get_summary(self) -> dict[str, Any]:
        """Return a comprehensive summary of the loaded dataset."""
        result = self.load()
        time_range = None
        if result.valid_records:
            timestamps = [r["timestamp"] for r in result.valid_records if r.get("timestamp")]
            if timestamps:
                time_range = {
                    "start": min(timestamps).isoformat(),
                    "end": max(timestamps).isoformat(),
                }

        return {
            "source_path": str(self.data_path),
            "filename": self.data_path.name,
            "total_raw_rows": result.total_raw_rows,
            "valid_records_loaded": len(result.valid_records),
            "invalid_records_count": len(result.invalid_records),
            "imputed_fields_count": result.imputed_fields_count,
            "available_fields": result.available_fields,
            "transformer_ids": result.transformer_ids,
            "time_range": time_range,
            "warnings": result.warnings,
        }

    def to_dataframe(self, transformer_id: str | None = None) -> pd.DataFrame:
        """Export clean dataset as a Pandas DataFrame for downstream consumers."""
        records = self.get_records(transformer_id=transformer_id)
        if not records:
            return pd.DataFrame(columns=self.get_available_fields())
        return pd.DataFrame(records)


# Global singleton instance for convenient cross-module usage
dataset_manager = TransformerDatasetManager()
