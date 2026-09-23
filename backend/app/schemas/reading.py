from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReadingBase(BaseModel):
    voltage_kv: float = Field(..., gt=0, description="Operating voltage in kV")
    current_a: float = Field(..., ge=0, description="Operating current in Amperes")
    load_percentage: float = Field(
        ..., ge=0, le=200, description="Load relative to rated capacity (%)"
    )
    oil_temperature_c: float = Field(
        ..., ge=-40, le=150, description="Top oil temperature in \u00b0C"
    )
    winding_temperature_c: float = Field(
        ..., ge=-40, le=180, description="Hot spot winding temperature in \u00b0C"
    )
    oil_level_pct: float = Field(
        ..., ge=0, le=100, description="Conservator oil level percentage (%)"
    )
    vibration_mm_s: float = Field(..., ge=0, le=50, description="Tank vibration velocity in mm/s")
    dissolved_gas_ppm: float = Field(
        ..., ge=0, description="Total dissolved combustible gases (TDCG) in ppm"
    )
    ambient_temperature_c: float = Field(
        ..., ge=-50, le=60, description="Ambient air temperature in \u00b0C"
    )
    humidity_pct: float = Field(
        ..., ge=0, le=100, description="Ambient relative humidity percentage (%)"
    )


class ReadingCreate(ReadingBase):
    timestamp: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC), description="Timestamp of sensor reading"
    )


class ReadingResponse(ReadingBase):
    id: int
    transformer_id: str
    timestamp: datetime

    @model_validator(mode="before")
    @classmethod
    def extract_reading_data(cls, data: Any):
        if hasattr(data, "voltage") and hasattr(data, "sensor_data"):
            tx = getattr(data, "transformer", None)
            tx_id_str = (
                tx.transformer_id
                if tx and hasattr(tx, "transformer_id")
                else str(getattr(data, "transformer_id", ""))
            )
            return {
                "id": data.id,
                "transformer_id": tx_id_str,
                "timestamp": data.timestamp,
                "voltage_kv": data.voltage,
                "current_a": data.current,
                "oil_temperature_c": data.temperature,
                "winding_temperature_c": data.winding_temperature_c,
                "oil_level_pct": data.oil_level_pct,
                "vibration_mm_s": data.vibration_mm_s,
                "load_percentage": data.load_percentage,
                "ambient_temperature_c": data.ambient_temperature_c,
                "humidity_pct": data.humidity_pct,
                "dissolved_gas_ppm": data.dissolved_gas_ppm,
            }
        return data

    model_config = ConfigDict(from_attributes=True)


class CurrentReadingResponse(BaseModel):
    transformer_id: str
    reading: ReadingResponse | None = None
    is_live: bool = True
    message: str | None = None


class NextReadingResponse(BaseModel):
    transformer_id: str
    reading: ReadingResponse | None = None
    has_next: bool
    cursor_timestamp: datetime | None = None
    remaining_in_dataset: int
    message: str | None = None
