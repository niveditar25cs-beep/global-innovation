from sqlalchemy.orm import Session

from app.data_access.reading_repo import ReadingRepository
from app.data_access.transformer_repo import TransformerRepository
from app.schemas.network import (
    NetworkNode,
    NetworkStatusBreakdown,
    NetworkSummaryResponse,
    NetworkTopologyResponse,
)
from app.schemas.reading import ReadingResponse


class NetworkService:
    def __init__(self, db: Session):
        self.db = db
        self.transformer_repo = TransformerRepository(db)
        self.reading_repo = ReadingRepository(db)

    def get_network_summary(self) -> NetworkSummaryResponse:
        transformers = self.transformer_repo.get_all(limit=1000)
        total_transformers = len(transformers)

        operational_count = sum(1 for t in transformers if t.status == "operational")
        maintenance_count = sum(1 for t in transformers if t.status == "maintenance")
        offline_count = sum(1 for t in transformers if t.status == "offline")

        locations = sorted({t.location for t in transformers if t.location})
        total_readings = self.reading_repo.count_total()

        # Calculate average system load across the latest readings
        latest_readings = self.reading_repo.get_all_latest_readings()
        avg_load = None
        if latest_readings:
            loads = [r.load_percentage for r in latest_readings if r.load_percentage is not None]
            if loads:
                avg_load = round(sum(loads) / len(loads), 2)

        return NetworkSummaryResponse(
            total_transformers=total_transformers,
            status_breakdown=NetworkStatusBreakdown(
                operational=operational_count, maintenance=maintenance_count, offline=offline_count
            ),
            total_historical_readings=total_readings,
            unique_locations=locations,
            average_system_load_pct=avg_load,
            system_status="operational" if offline_count == 0 else "degraded",
        )

    def get_network_topology(self) -> NetworkTopologyResponse:
        transformers = self.transformer_repo.get_all(limit=1000)
        latest_readings = self.reading_repo.get_all_latest_readings()
        readings_map = {r.transformer_id: r for r in latest_readings}

        nodes: list[NetworkNode] = []
        for tr in transformers:
            reading_orm = readings_map.get(tr.id)
            latest_reading_dto = (
                ReadingResponse.model_validate(reading_orm) if reading_orm else None
            )

            nodes.append(
                NetworkNode(
                    id=str(tr.transformer_id),
                    name=tr.name or str(tr.transformer_id),
                    location=tr.location,
                    rating_mva=tr.rating_mva,
                    voltage_rating_kv=tr.voltage_rating_kv,
                    status=tr.status,
                    latest_reading=latest_reading_dto,
                )
            )

        return NetworkTopologyResponse(total_nodes=len(nodes), nodes=nodes)
