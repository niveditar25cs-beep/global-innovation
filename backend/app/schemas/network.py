from pydantic import BaseModel

from app.schemas.reading import ReadingResponse


class NetworkStatusBreakdown(BaseModel):
    operational: int = 0
    maintenance: int = 0
    offline: int = 0


class NetworkSummaryResponse(BaseModel):
    total_transformers: int
    status_breakdown: NetworkStatusBreakdown
    total_historical_readings: int
    unique_locations: list[str]
    average_system_load_pct: float | None = None
    system_status: str = "operational"


class NetworkNode(BaseModel):
    id: str
    name: str
    location: str | None = None
    rating_mva: float | None = None
    voltage_rating_kv: float | None = None
    status: str
    latest_reading: ReadingResponse | None = None


class NetworkTopologyResponse(BaseModel):
    total_nodes: int
    nodes: list[NetworkNode]
