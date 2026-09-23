from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.controllers.reading_controller import ReadingController
from app.data_access.database import get_async_db, get_db
from app.schemas.common import ApiResponse
from app.schemas.current_reading import CurrentReadingApiResponse
from app.schemas.history_reading import HistoryReadingApiResponse
from app.schemas.next_reading import NextReadingApiResponse
from app.schemas.reading import ReadingCreate
from app.services.current_reading_service import CurrentReadingService
from app.services.history_reading_service import HistoryReadingService
from app.services.next_reading_service import NextReadingService
from app.state.cursor_store import CursorStore
from app.state.rate_limiter import RateLimiter
from app.state.store_factory import get_cursor_store

router = APIRouter(tags=["Readings"])


@router.get(
    "/readings/current",
    response_model=CurrentReadingApiResponse,
    summary="Get Current Reading",
    description=(
        "Retrieve the currently selected dataset reading from PostgreSQL. "
        "If no transformer_id is provided, the first registered transformer is used. "
        "If no sequence is provided, the active cursor or sequence 1 is returned."
    ),
    responses={
        200: {"description": "Successfully retrieved current reading"},
        404: {"description": "Transformer or reading not found"},
    },
)
async def get_current_reading(
    transformer_id: str | None = Query(
        None,
        description=(
            "Unique transformer business identifier (e.g. T001, TR-001). "
            "Defaults to the primary transformer."
        ),
    ),
    sequence: int | None = Query(
        None,
        ge=1,
        description=(
            "Specific reading sequence to retrieve. Defaults to the active cursor or sequence 1."
        ),
    ),
    session: AsyncSession = Depends(get_async_db),
) -> CurrentReadingApiResponse:
    """
    Return the currently selected transformer reading.

    - **transformer_id**: Optional business identifier. Uses the first transformer when omitted.
    - **sequence**: Optional sequence index (≥ 1). Uses the active session cursor or falls back to
      sequence 1.
    """
    service = CurrentReadingService(session)
    return await service.get_current_reading(
        transformer_id=transformer_id,
        sequence=sequence,
    )


@router.get(
    "/readings/next",
    response_model=NextReadingApiResponse,
    dependencies=[Depends(RateLimiter(scope="readings_next"))],
    summary="Get Next Sequential Reading",
    description=(
        "Retrieve the next sequential reading from the PostgreSQL dataset. "
        "Advances an isolated per-session reading cursor stored in Redis (or in-memory fallback). "
        "If session_id is omitted, a new UUID session is generated and returned. "
        "When the end of the dataset is reached, returns HTTP 200 with is_end_of_dataset: true."
    ),
    responses={
        200: {
            "description": (
                "Successfully retrieved next sequential reading or reached end of dataset"
            )
        },
        404: {"description": "Transformer not found"},
    },
)
async def get_next_reading_api(
    transformer_id: str | None = Query(
        None,
        description=(
            "Unique transformer business identifier (e.g. TR-001 or T001). "
            "Defaults to the primary transformer."
        ),
    ),
    session_id: str | None = Query(
        None,
        description=(
            "Client session identifier for tracking cursor progression. Generated if omitted."
        ),
    ),
    session: AsyncSession = Depends(get_async_db),
    cursor_store: CursorStore = Depends(get_cursor_store),
) -> NextReadingApiResponse:
    """
    Advance session cursor and retrieve the next sequential transformer reading.

    - **transformer_id**: Optional transformer business identifier. Defaults to first registered
      transformer.
    - **session_id**: Client session UUID. If omitted, a fresh session is initiated and returned.
    """
    service = NextReadingService(session, cursor_store)
    return await service.get_next_reading(
        transformer_id=transformer_id,
        session_id=session_id,
    )


@router.get(
    "/readings/history",
    response_model=HistoryReadingApiResponse,
    summary="Get Reading Telemetry History",
    description=(
        "Retrieve scalable, paginated historical sensor readings from PostgreSQL with async "
        "SQLAlchemy. Supports optional transformer filtering, date range filtering, "
        "sorting by timestamp or sequence, and structured pagination metadata."
    ),
    responses={
        200: {"description": "Successfully retrieved paginated reading history"},
        404: {"description": "Transformer not found"},
    },
)
@router.get(
    "/v1/readings/history",
    response_model=HistoryReadingApiResponse,
    include_in_schema=False,
)
async def get_readings_history_api(
    transformer_id: str | None = Query(
        None,
        description=(
            "Optional business identifier to filter by (e.g. TR-001 or T001). "
            "Omit to query across all transformers."
        ),
    ),
    page: int = Query(1, ge=1, description="1-indexed page number for pagination."),
    limit: int = Query(
        20, ge=1, le=500, description="Number of records per page (1 to 500, default 20)."
    ),
    sort_by: str = Query(
        "timestamp",
        pattern="^(timestamp|sequence)$",
        description="Field to sort by: 'timestamp' or 'sequence' (default 'timestamp').",
    ),
    order: str = Query(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort direction: 'asc' or 'desc' (default 'desc').",
    ),
    start_time: datetime | None = Query(
        None, description="Optional ISO-8601 start timestamp filter."
    ),
    end_time: datetime | None = Query(None, description="Optional ISO-8601 end timestamp filter."),
    session: AsyncSession = Depends(get_async_db),
) -> HistoryReadingApiResponse:
    """
    Retrieve historical sensor telemetry records with pagination, filtering, and sorting.
    """
    service = HistoryReadingService(session)
    return await service.get_reading_history(
        transformer_id=transformer_id,
        page=page,
        limit=limit,
        sort_by=sort_by,
        order=order,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/transformers/{transformer_id}/readings/current", response_model=ApiResponse)
def get_transformer_current_reading(
    transformer_id: str = Path(..., description="Unique transformer identifier"),
    db: Session = Depends(get_db),
):
    """Retrieve the latest sensor reading for a specific transformer."""
    controller = ReadingController(db)
    return controller.get_current_reading(transformer_id)


@router.get("/transformers/{transformer_id}/readings/next", response_model=ApiResponse)
def get_next_reading(
    transformer_id: str = Path(..., description="Unique transformer identifier"),
    db: Session = Depends(get_db),
):
    """
    Simulated sensor stream playback.
    Advances the playback cursor and returns the sequential next reading for the transformer.
    """
    controller = ReadingController(db)
    return controller.get_next_reading(transformer_id)


@router.post("/transformers/{transformer_id}/readings/reset-stream", response_model=ApiResponse)
def reset_stream(
    transformer_id: str = Path(..., description="Unique transformer identifier"),
    db: Session = Depends(get_db),
):
    """Reset the sequential stream cursor for the transformer to the beginning of the dataset."""
    controller = ReadingController(db)
    return controller.reset_stream(transformer_id)


@router.get("/transformers/{transformer_id}/readings/history", response_model=ApiResponse)
def get_reading_history(
    transformer_id: str = Path(..., description="Unique transformer identifier"),
    start_time: datetime | None = Query(None, description="Start timestamp (ISO-8601)"),
    end_time: datetime | None = Query(None, description="End timestamp (ISO-8601)"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order by timestamp"),
    db: Session = Depends(get_db),
):
    """
    Retrieve historical sensor readings for a transformer with time range
    and pagination filters.
    """
    controller = ReadingController(db)
    return controller.get_history(
        transformer_id=transformer_id,
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=limit,
        order=order,
    )


@router.post("/transformers/{transformer_id}/readings", response_model=ApiResponse, status_code=201)
def record_reading(
    payload: ReadingCreate,
    transformer_id: str = Path(..., description="Unique transformer identifier"),
    db: Session = Depends(get_db),
):
    """Append a new sensor reading to the transformer's time-series record."""
    controller = ReadingController(db)
    return controller.record_reading(transformer_id, payload)
