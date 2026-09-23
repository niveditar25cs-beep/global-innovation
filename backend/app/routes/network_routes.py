from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.network_controller import NetworkController
from app.data_access.database import get_db
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/network", tags=["Network Data"])


@router.get("/summary", response_model=ApiResponse)
def get_network_summary(db: Session = Depends(get_db)):
    """Retrieve grid network health summary, counts, and aggregate load."""
    controller = NetworkController(db)
    return controller.get_summary()


@router.get("/topology", response_model=ApiResponse)
def get_network_topology(db: Session = Depends(get_db)):
    """Retrieve all transformer nodes in the network along with their latest reading."""
    controller = NetworkController(db)
    return controller.get_topology()
