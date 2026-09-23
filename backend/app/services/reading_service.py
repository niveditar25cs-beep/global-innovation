from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.data_access.reading_repo import ReadingRepository
from app.data_access.transformer_repo import TransformerRepository
from app.error_handling.exceptions import ResourceNotFoundError
from app.models.reading import TransformerReading
from app.models.transformer import Transformer
from app.schemas.reading import (
    CurrentReadingResponse,
    NextReadingResponse,
    ReadingCreate,
    ReadingResponse,
)

# Global stream cursor tracker: maps transformer_id -> last_served_reading_id / timestamp
_STREAM_CURSORS: dict[str, datetime] = {}


class ReadingService:
    def __init__(self, db: Session):
        self.db = db
        self.reading_repo = ReadingRepository(db)
        self.transformer_repo = TransformerRepository(db)

    def _ensure_transformer_exists(self, transformer_id: str) -> Transformer:
        transformer = self.transformer_repo.get_by_id(transformer_id)
        if not transformer:
            raise ResourceNotFoundError(resource="Transformer", identifier=transformer_id)
        return transformer

    def get_current_reading(self, transformer_id: str) -> CurrentReadingResponse:
        self._ensure_transformer_exists(transformer_id)
        reading = self.reading_repo.get_latest_reading(transformer_id)
        if not reading:
            return CurrentReadingResponse(
                transformer_id=transformer_id,
                reading=None,
                is_live=False,
                message=f"No readings have been recorded for transformer '{transformer_id}'.",
            )
        return CurrentReadingResponse(
            transformer_id=transformer_id,
            reading=ReadingResponse.model_validate(reading),
            is_live=True,
        )

    def get_next_reading(self, transformer_id: str) -> NextReadingResponse:
        """
        Simulated sensor stream advance.
        Fetches the sequential next reading for the given transformer using a streaming cursor.
        """
        self._ensure_transformer_exists(transformer_id)
        cursor_ts = _STREAM_CURSORS.get(transformer_id)

        if cursor_ts is None:
            # Initialize cursor at the earliest reading in the dataset
            first_reading = self.reading_repo.get_first_reading(transformer_id)
            if not first_reading:
                return NextReadingResponse(
                    transformer_id=transformer_id,
                    reading=None,
                    has_next=False,
                    cursor_timestamp=None,
                    remaining_in_dataset=0,
                    message=f"No readings in dataset for transformer '{transformer_id}'.",
                )
            _STREAM_CURSORS[transformer_id] = first_reading.timestamp
            remaining = (
                self.reading_repo.count_history(transformer_id, start_time=first_reading.timestamp)
                - 1
            )
            return NextReadingResponse(
                transformer_id=transformer_id,
                reading=ReadingResponse.model_validate(first_reading),
                has_next=remaining > 0,
                cursor_timestamp=first_reading.timestamp,
                remaining_in_dataset=max(0, remaining),
                message="Stream initialized with the first sequential reading.",
            )

        # Advance to reading immediately following the current cursor timestamp
        next_reading = self.reading_repo.get_reading_after(transformer_id, cursor_ts)
        if not next_reading:
            # End of stream reached
            return NextReadingResponse(
                transformer_id=transformer_id,
                reading=None,
                has_next=False,
                cursor_timestamp=cursor_ts,
                remaining_in_dataset=0,
                message="End of time-series stream reached. Call reset-stream to replay.",
            )

        _STREAM_CURSORS[transformer_id] = next_reading.timestamp
        remaining = (
            self.reading_repo.count_history(transformer_id, start_time=next_reading.timestamp) - 1
        )

        return NextReadingResponse(
            transformer_id=transformer_id,
            reading=ReadingResponse.model_validate(next_reading),
            has_next=remaining > 0,
            cursor_timestamp=next_reading.timestamp,
            remaining_in_dataset=max(0, remaining),
            message="Sequential next reading retrieved.",
        )

    def reset_stream(self, transformer_id: str) -> dict:
        self._ensure_transformer_exists(transformer_id)
        _STREAM_CURSORS.pop(transformer_id, None)
        return {
            "transformer_id": transformer_id,
            "status": "stream_cursor_reset",
            "message": (
                f"Stream cursor for transformer '{transformer_id}' has been reset to the beginning."
            ),
        }

    def get_history(
        self,
        transformer_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
        order: str = "desc",
    ) -> tuple[list[TransformerReading], int]:
        self._ensure_transformer_exists(transformer_id)
        readings = self.reading_repo.get_history(
            transformer_id=transformer_id,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=limit,
            order=order,
        )
        total = self.reading_repo.count_history(
            transformer_id=transformer_id, start_time=start_time, end_time=end_time
        )
        return readings, total

    def record_reading(self, transformer_id: str, data: ReadingCreate) -> TransformerReading:
        transformer = self._ensure_transformer_exists(transformer_id)
        seq = self.reading_repo.count_history(transformer_id) + 1
        ts = data.timestamp or datetime.now(UTC)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        reading = TransformerReading(
            transformer_id=transformer.id,
            reading_sequence=seq,
            timestamp=ts,
            voltage=data.voltage_kv,
            current=data.current_a,
            temperature=data.oil_temperature_c,
            sensor_data={
                "winding_temperature_c": data.winding_temperature_c,
                "oil_level_pct": data.oil_level_pct,
                "vibration_mm_s": data.vibration_mm_s,
                "load_percentage": data.load_percentage,
                "ambient_temperature_c": data.ambient_temperature_c,
                "humidity_pct": data.humidity_pct,
                "dissolved_gas_ppm": data.dissolved_gas_ppm,
            },
        )
        return self.reading_repo.create(reading)
