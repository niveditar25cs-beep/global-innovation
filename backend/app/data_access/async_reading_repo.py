"""
Asynchronous repository for reading telemetry queries using SQLAlchemy 2.0 Async.
"""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reading import TransformerReading
from app.models.transformer import Transformer


class AsyncReadingRepository:
    """
    Data access layer for async reading operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_default_transformer(self) -> Transformer | None:
        """Fetch the primary / first transformer in the database."""
        stmt = select(Transformer).order_by(Transformer.id.asc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_transformer_by_identifier(self, identifier: str) -> Transformer | None:
        """
        Fetch a transformer by its string business identifier (e.g. TR-001 or T001)
        or by primary key integer id.
        """
        cleaned = str(identifier).strip()
        conditions = [Transformer.transformer_id == cleaned]
        if cleaned.isdigit():
            conditions.append(Transformer.id == int(cleaned))

        stmt = select(Transformer).where(or_(*conditions)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_reading_by_sequence(
        self, transformer_db_id: int, sequence: int
    ) -> TransformerReading | None:
        """Fetch a specific sequence reading for a transformer."""
        stmt = (
            select(TransformerReading)
            .where(
                TransformerReading.transformer_id == transformer_db_id,
                TransformerReading.reading_sequence == sequence,
            )
            .options(selectinload(TransformerReading.transformer))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_first_reading(self, transformer_db_id: int) -> TransformerReading | None:
        """Fetch the first chronological/sequential reading (sequence 1) for a transformer."""
        stmt = (
            select(TransformerReading)
            .where(TransformerReading.transformer_id == transformer_db_id)
            .order_by(TransformerReading.reading_sequence.asc())
            .options(selectinload(TransformerReading.transformer))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_reading(self, transformer_db_id: int) -> TransformerReading | None:
        """Fetch the most recent reading for a transformer."""
        stmt = (
            select(TransformerReading)
            .where(TransformerReading.transformer_id == transformer_db_id)
            .order_by(TransformerReading.reading_sequence.desc())
            .options(selectinload(TransformerReading.transformer))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_max_sequence(self, transformer_db_id: int) -> int | None:
        """Fetch the maximum reading_sequence recorded for a transformer, or None if empty."""
        stmt = select(func.max(TransformerReading.reading_sequence)).where(
            TransformerReading.transformer_id == transformer_db_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_readings_for_transformer(self, transformer_db_id: int) -> int:
        """Fetch the total count of sequential readings for a transformer."""
        stmt = select(func.count(TransformerReading.id)).where(
            TransformerReading.transformer_id == transformer_db_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_history_readings(
        self,
        transformer_db_id: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        sort_by: str = "timestamp",
        order: str = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> list[TransformerReading]:
        """
        Fetch paginated historical telemetry readings with optional filters and sorting.
        """
        stmt = select(TransformerReading).options(selectinload(TransformerReading.transformer))

        conditions = []
        if transformer_db_id is not None:
            conditions.append(TransformerReading.transformer_id == transformer_db_id)
        if start_time is not None:
            conditions.append(TransformerReading.timestamp >= start_time)
        if end_time is not None:
            conditions.append(TransformerReading.timestamp <= end_time)

        if conditions:
            stmt = stmt.where(*conditions)

        # Sorting logic
        sort_col = (
            TransformerReading.reading_sequence
            if sort_by == "sequence"
            else TransformerReading.timestamp
        )
        if order.lower() == "asc":
            stmt = stmt.order_by(sort_col.asc(), TransformerReading.id.asc())
        else:
            stmt = stmt.order_by(sort_col.desc(), TransformerReading.id.desc())

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_history_readings(
        self,
        transformer_db_id: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """
        Count total historical readings matching the specified filter criteria.
        """
        stmt = select(func.count(TransformerReading.id))

        conditions = []
        if transformer_db_id is not None:
            conditions.append(TransformerReading.transformer_id == transformer_db_id)
        if start_time is not None:
            conditions.append(TransformerReading.timestamp >= start_time)
        if end_time is not None:
            conditions.append(TransformerReading.timestamp <= end_time)

        if conditions:
            stmt = stmt.where(*conditions)

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
