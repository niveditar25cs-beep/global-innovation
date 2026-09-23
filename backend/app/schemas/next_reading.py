"""
Pydantic schemas for the Next Reading API.
"""

from pydantic import BaseModel, ConfigDict, Field


class NextReadingData(BaseModel):
    """
    Frontend-friendly model for sequential next reading telemetry.
    Contains actual stored database readings and stream playback progress.
    """

    transformer_id: str = Field(
        ...,
        description="Unique business identifier of the transformer (e.g. TR-001 or T001)",
        examples=["TR-001"],
    )
    voltage: float | None = Field(
        None,
        description="Operating voltage measurement (None if end of dataset reached)",
        examples=[132.5],
    )
    current: float | None = Field(
        None,
        description="Operating current measurement in Amperes (None if end of dataset reached)",
        examples=[350.0],
    )
    temperature: float | None = Field(
        None,
        description=(
            "Operating temperature measurement in degrees Celsius (None if end of dataset reached)"
        ),
        examples=[65.2],
    )
    sequence: int | None = Field(
        None,
        description="Deterministic sequential reading index (None if end of dataset reached)",
        examples=[5],
    )
    has_next: bool = Field(
        ...,
        description="Whether further readings exist after this sequence in the dataset",
        examples=[True, False],
    )
    is_end_of_dataset: bool = Field(
        ...,
        description="Flag indicating the stream cursor has advanced past all available records",
        examples=[False, True],
    )
    session_id: str = Field(
        ...,
        description="Client session identifier maintaining sequential playback position",
        examples=["f47ac10b-58cc-4372-a567-0e02b2c3d479"],
    )
    total_readings: int = Field(
        ...,
        description=(
            "Total number of sequential readings recorded for this transformer in the database"
        ),
        examples=[120],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "transformer_id": "TR-001",
                "voltage": 132.5,
                "current": 350.0,
                "temperature": 65.2,
                "sequence": 5,
                "has_next": True,
                "is_end_of_dataset": False,
                "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "total_readings": 120,
            }
        },
    )


class NextReadingApiResponse(BaseModel):
    """
    Standardized API response envelope for next reading.
    """

    success: bool = Field(
        True, description="Boolean status indicating successful retrieval", examples=[True]
    )
    data: NextReadingData = Field(
        ..., description="Next sequential reading payload and playback state"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {
                    "transformer_id": "TR-001",
                    "voltage": 132.5,
                    "current": 350.0,
                    "temperature": 65.2,
                    "sequence": 5,
                    "has_next": True,
                    "is_end_of_dataset": False,
                    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    "total_readings": 120,
                },
            }
        }
    )
