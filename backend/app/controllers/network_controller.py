from sqlalchemy.orm import Session

from app.schemas.common import ApiResponse
from app.services.network_service import NetworkService
from app.utils.response_builder import build_response


class NetworkController:
    def __init__(self, db: Session):
        self.service = NetworkService(db)

    def get_summary(self) -> ApiResponse:
        summary = self.service.get_network_summary()
        return build_response(
            data=summary.model_dump(), message="Transformer network summary statistics retrieved."
        )

    def get_topology(self) -> ApiResponse:
        topology = self.service.get_network_topology()
        return build_response(
            data=topology.model_dump(), message="Transformer network topology retrieved."
        )
