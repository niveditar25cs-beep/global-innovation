from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TransformerBase(BaseModel):
    name: str = Field(
        ..., min_length=2, max_length=100, description="Name or identifier of the transformer"
    )
    location: str | None = Field(
        None, max_length=200, description="Substation or physical location"
    )
    rating_mva: float | None = Field(None, gt=0, description="Rated apparent power capacity in MVA")
    voltage_rating_kv: float | None = Field(None, gt=0, description="Rated primary voltage in kV")
    installation_date: str | None = Field(None, description="Date of commissioning (YYYY-MM-DD)")
    manufacturer: str | None = Field(None, max_length=100, description="Manufacturer name")
    status: str = Field(
        "operational",
        pattern="^(operational|maintenance|offline)$",
        description="Operational status",
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class TransformerCreate(TransformerBase):
    id: str = Field(
        ...,
        min_length=2,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Unique transformer ID (e.g. TR-001)",
    )


class TransformerUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    location: str | None = Field(None, max_length=200)
    rating_mva: float | None = Field(None, gt=0)
    voltage_rating_kv: float | None = Field(None, gt=0)
    installation_date: str | None = None
    manufacturer: str | None = Field(None, max_length=100)
    status: str | None = Field(None, pattern="^(operational|maintenance|offline)$")

    model_config = ConfigDict(str_strip_whitespace=True)


class TransformerResponse(TransformerBase):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def extract_from_orm(cls, data: Any):
        if hasattr(data, "transformer_id"):
            meta = getattr(data, "metadata_payload", {}) or {}
            return {
                "id": str(data.transformer_id),
                "name": data.name or f"Transformer {data.transformer_id}",
                "location": meta.get("location"),
                "rating_mva": meta.get("rating_mva"),
                "voltage_rating_kv": meta.get("voltage_rating_kv"),
                "installation_date": meta.get("installation_date"),
                "manufacturer": meta.get("manufacturer"),
                "status": meta.get("status", "operational"),
                "created_at": getattr(data, "created_at", None),
                "updated_at": getattr(data, "updated_at", None),
            }
        return data

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class TransformerSummary(BaseModel):
    id: str
    name: str
    location: str | None = None
    status: str
    rating_mva: float | None = None
    voltage_rating_kv: float | None = None
    latest_reading_timestamp: datetime | None = None
