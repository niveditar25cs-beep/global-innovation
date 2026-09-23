from datetime import datetime

from sqlalchemy.orm import Session

from app.schemas.common import ApiResponse
from app.schemas.reading import ReadingCreate, ReadingResponse
from app.services.reading_service import ReadingService
from app.utils.response_builder import build_paginated_response, build_response


class ReadingController:
    def __init__(self, db: Session):
        self.service = ReadingService(db)

    def get_current_reading(self, transformer_id: str) -> ApiResponse:
        result = self.service.get_current_reading(transformer_id)
        return build_response(
            data=result.model_dump(), message=f"Current reading for transformer '{transformer_id}'."
        )

    def get_next_reading(self, transformer_id: str) -> ApiResponse:
        result = self.service.get_next_reading(transformer_id)
        return build_response(
            data=result.model_dump(), message=result.message or "Sequential next reading fetched."
        )

    def reset_stream(self, transformer_id: str) -> ApiResponse:
        result = self.service.reset_stream(transformer_id)
        return build_response(data=result, message="Stream playback cursor reset.")

    def get_history(
        self,
        transformer_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
        order: str = "desc",
    ) -> ApiResponse:
        readings, total = self.service.get_history(
            transformer_id=transformer_id,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=limit,
            order=order,
        )
        data = [ReadingResponse.model_validate(r).model_dump() for r in readings]
        return build_paginated_response(
            items=data,
            total=total,
            skip=skip,
            limit=limit,
            message=f"Reading history for transformer '{transformer_id}'.",
        )

    def record_reading(self, transformer_id: str, payload: ReadingCreate) -> ApiResponse:
        reading = self.service.record_reading(transformer_id, payload)
        data = ReadingResponse.model_validate(reading).model_dump()
        return build_response(
            data=data,
            message=f"New reading recorded for transformer '{transformer_id}'.",
            status_code=201,
        )
