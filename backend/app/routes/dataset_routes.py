from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.controllers.dataset_controller import DatasetController
from app.data_access.database import get_db
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/dataset", tags=["Dataset Management"])


@router.get("/info", response_model=ApiResponse)
def get_dataset_info(db: Session = Depends(get_db)):
    """Retrieve metadata and schema information for the dataset."""
    controller = DatasetController(db)
    return controller.get_info()


@router.get("/preview", response_model=ApiResponse)
def preview_dataset(
    limit: int = Query(10, ge=1, le=100, description="Number of sample rows to inspect"),
    db: Session = Depends(get_db),
):
    """Inspect top N sample rows from the transformer sensor dataset."""
    controller = DatasetController(db)
    return controller.preview(limit=limit)


@router.post("/upload", response_model=ApiResponse)
async def upload_dataset(
    file: UploadFile = File(..., description="CSV file containing transformer readings"),
    db: Session = Depends(get_db),
):
    """Upload and ingest a new CSV dataset into the monitoring database."""
    controller = DatasetController(db)
    return await controller.upload(file)


@router.post("/load-sample", response_model=ApiResponse)
def load_sample_dataset(db: Session = Depends(get_db)):
    """Populate the database with the built-in sample transformer dataset."""
    controller = DatasetController(db)
    return controller.load_sample()


@router.delete("/clear", response_model=ApiResponse)
def clear_dataset(db: Session = Depends(get_db)):
    """Clear all ingested sensor readings from the system."""
    controller = DatasetController(db)
    return controller.clear()
