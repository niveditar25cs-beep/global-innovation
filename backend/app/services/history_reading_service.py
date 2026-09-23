"""
Business service for querying paginated, sorted historical sensor telemetry.
"""

import logging
import math
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.async_reading_repo import AsyncReadingRepository
from app.error_handling.exceptions import ResourceNotFoundError
from app.schemas.history_reading import (
    HistoryReadingApiResponse,
    HistoryReadingItem,
    PaginationMetadata,
)

logger = logging.getLogger("transformer_backend.services")


class HistoryReadingService:
    """
    Coordinates historical sensor telemetry queries, filtering, sorting,
    and pagination calculation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AsyncReadingRepository(session)

    async def get_reading_history(
        self,
        transformer_id: str | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "timestamp",
        order: str = "desc",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> HistoryReadingApiResponse:
        """
        Retrieve paginated historical readings with optional filters.

        Steps:
        1. Resolve transformer business ID if specified (raises 404 if not found).
        2. Calculate offset from page and limit.
        3. Query count and records from PostgreSQL.
        4. Calculate pagination metadata (total_pages, has_next, has_prev).
        5. Return structured response.
        """
        transformer_db_id: int | None = None
        target_tx_business_id: str | None = None

        if transformer_id is not None and transformer_id.strip():
            cleaned_id = transformer_id.strip()
            tx = await self.repo.get_transformer_by_identifier(cleaned_id)
            if not tx:
                raise ResourceNotFoundError(resource="Transformer", identifier=cleaned_id)
            transformer_db_id = tx.id
            target_tx_business_id = tx.transformer_id

        # Clamp pagination bounds
        safe_page = max(1, page)
        safe_limit = max(1, min(500, limit))
        offset = (safe_page - 1) * safe_limit

        # Retrieve count
        total_items = await self.repo.count_history_readings(
            transformer_db_id=transformer_db_id, start_time=start_time, end_time=end_time
        )

        total_pages = math.ceil(total_items / safe_limit) if total_items > 0 else 1
        has_next = safe_page < total_pages
        has_prev = safe_page > 1

        # Fetch records if page within range
        if total_items == 0 or offset >= total_items:
            records = []
        else:
            records = await self.repo.get_history_readings(
                transformer_db_id=transformer_db_id,
                start_time=start_time,
                end_time=end_time,
                sort_by=sort_by,
                order=order,
                offset=offset,
                limit=safe_limit,
            )

        items = [
            HistoryReadingItem(
                transformer_id=(
                    reading.transformer.transformer_id
                    if reading.transformer
                    else (target_tx_business_id or str(reading.transformer_id))
                ),
                voltage=float(reading.voltage),
                current=float(reading.current),
                temperature=float(reading.temperature),
                sequence=int(reading.reading_sequence),
                timestamp=reading.timestamp,
            )
            for reading in records
        ]

        pagination = PaginationMetadata(
            page=safe_page,
            limit=safe_limit,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

        return HistoryReadingApiResponse(success=True, data=items, pagination=pagination)
