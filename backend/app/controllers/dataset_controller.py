from fastapi import UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.schemas.common import ApiResponse
from app.services.dataset_service import DatasetService
from app.utils.response_builder import build_response


class DatasetController:
    def __init__(self, db: Session):
        self.service = DatasetService(db)

    def get_info(self) -> ApiResponse:
        info = self.service.get_dataset_info()
        return build_response(
            data=info.model_dump(), message="Dataset information retrieved successfully."
        )

    def preview(self, limit: int = 10) -> ApiResponse:
        preview_data = self.service.preview_dataset(limit=limit)
        return build_response(
            data=preview_data.model_dump(), message=f"Preview of top {limit} dataset rows."
        )

    async def upload(self, file: UploadFile) -> ApiResponse:
        content = await file.read()
        filename = file.filename or "uploaded.csv"
        result = await run_in_threadpool(
            self.service.load_dataset_from_file_or_bytes, content, filename=filename
        )
        return build_response(
            data=result.model_dump(),
            message=(
                f"Dataset '{file.filename}' processed successfully: "
                f"{result.readings_stored} readings stored."
            ),
        )

    def load_sample(self) -> ApiResponse:
        result = self.service.seed_sample_if_empty()
        if result is None:
            return build_response(
                data={"status": "already_populated"},
                message="Database already contains sensor readings.",
            )
        return build_response(
            data=result.model_dump(), message="Sample transformer dataset loaded into database."
        )

    def clear(self) -> ApiResponse:
        result = self.service.clear_dataset()
        return build_response(data=result, message="Dataset cleared successfully.")
