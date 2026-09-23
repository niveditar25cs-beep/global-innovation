"""
Pydantic schemas for the History Reading API.
Supports paginated, sorted historical sensor telemetry retrieval.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HistoryReadingItem(BaseModel):
    """
    Individual historical telemetry record for a transformer.
    Contains actual stored database measurements without ML predictions.
    """

    transformer_id: str = Field(
        ...,
        description="Unique business identifier of the transformer (e.g. TR-001 or T001)",
        examples=["TR-001"],
    )
    voltage: float = Field(..., description="Operating voltage measurement", examples=[132.5])
    current: float = Field(
        ..., description="Operating current measurement in Amperes", examples=[350.0]
    )
    temperature: float = Field(
        ..., description="Operating temperature measurement in degrees Celsius", examples=[65.2]
    )
    sequence: int = Field(..., description="Deterministic sequential reading index", examples=[42])
    timestamp: datetime = Field(
        ..., description="Reading timestamp in ISO-8601 format", examples=["2026-03-15T12:00:00Z"]
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "transformer_id": "TR-001",
                "voltage": 132.5,
                "current": 350.0,
                "temperature": 65.2,
                "sequence": 42,
                "timestamp": "2026-03-15T12:00:00Z",
            }
        },
    )


class PaginationMetadata(BaseModel):
    """
    Metadata describing pagination state for historical queries.
    """

    page: int = Field(..., description="Current page number (1-indexed)", examples=[1])
    limit: int = Field(..., description="Number of records requested per page", examples=[20])
    total_items: int = Field(
        ..., description="Total number of records matching the query filters", examples=[120]
    )
    total_pages: int = Field(..., description="Total number of pages available", examples=[6])
    has_next: bool = Field(
        ...,
        description="Whether another page of records exists after the current page",
        examples=[True],
    )
    has_prev: bool = Field(
        ...,
        description="Whether a preceding page of records exists before the current page",
        examples=[False],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "limit": 20,
                "total_items": 120,
                "total_pages": 6,
                "has_next": True,
                "has_prev": False,
            }
        }
    )


class HistoryReadingApiResponse(BaseModel):
    """
    Standardized API response envelope for reading history.
    """

    success: bool = Field(
        True, description="Boolean status indicating successful retrieval", examples=[True]
    )
    data: list[HistoryReadingItem] = Field(
        default_factory=list,
        description="List of historical telemetry records matching query filters",
    )
    pagination: PaginationMetadata = Field(
        ..., description="Pagination metadata including page counts and navigation flags"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": [
                    {
                        "transformer_id": "TR-001",
                        "voltage": 132.5,
                        "current": 350.0,
                        "temperature": 65.2,
                        "sequence": 42,
                        "timestamp": "2026-03-15T12:00:00Z",
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 20,
                    "total_items": 120,
                    "total_pages": 6,
                    "has_next": True,
                    "has_prev": False,
                },
            }
        }
    )
