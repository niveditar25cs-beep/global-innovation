from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DatasetColumnInfo(BaseModel):
    name: str
    data_type: str
    non_null_count: int
    missing_count: int


class DatasetInfoResponse(BaseModel):
    filename: str
    total_records: int
    columns: list[str]
    column_details: list[DatasetColumnInfo]
    transformers_found: list[str]
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    loaded_in_db_records: int


class DatasetPreviewResponse(BaseModel):
    filename: str
    preview_limit: int
    total_records: int
    columns: list[str]
    rows: list[dict[str, Any]]


class DatasetUploadResponse(BaseModel):
    filename: str
    rows_parsed: int
    transformers_registered: int
    readings_stored: int
    warnings: list[str] = []
