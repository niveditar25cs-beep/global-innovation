"""
Pydantic schemas for the Current Reading API.
"""

from pydantic import BaseModel, ConfigDict, Field


class CurrentReadingData(BaseModel):
    """
    Frontend-friendly transformer reading data model.
    Contains actual stored database telemetry without ML predictions or risk status.
    """

    transformer_id: str = Field(
        ...,
        description="Unique business identifier of the transformer (e.g. TR-001 or T001)",
        examples=["T001", "TR-001"],
    )
    voltage: float = Field(
        ..., description="Primary operating voltage measurement", examples=[230.0, 132.5]
    )
    current: float = Field(
        ..., description="Primary operating current measurement in Amperes", examples=[12.5, 350.0]
    )
    temperature: float = Field(
        ..., description="Primary temperature measurement in degrees Celsius", examples=[68.0, 65.5]
    )
    sequence: int = Field(..., description="Deterministic reading sequence index", examples=[1, 42])

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "transformer_id": "T001",
                "voltage": 230.0,
                "current": 12.5,
                "temperature": 68.0,
                "sequence": 1,
            }
        },
    )


class CurrentReadingApiResponse(BaseModel):
    """
    Standardized API response envelope for current reading.
    """

    success: bool = Field(
        True, description="Boolean status indicating successful retrieval", examples=[True]
    )
    data: CurrentReadingData = Field(..., description="Currently selected transformer reading data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {
                    "transformer_id": "T001",
                    "voltage": 230.0,
                    "current": 12.5,
                    "temperature": 68.0,
                    "sequence": 1,
                },
            }
        }
    )
