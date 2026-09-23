"""
Business service coordinating sequential next reading retrieval and session cursor advancement.
Uses Redis (or an in-memory cursor store fallback) for scalable multi-session state management.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.async_reading_repo import AsyncReadingRepository
from app.error_handling.exceptions import ResourceNotFoundError
from app.schemas.next_reading import NextReadingApiResponse, NextReadingData
from app.state.cursor_store import CursorStore

logger = logging.getLogger("transformer_backend.services")


class NextReadingService:
    """
    Coordinates safe, sequential reading playback across multiple users and sessions.
    Stores and advances cursor state atomically in Redis / CursorStore.
    """

    def __init__(self, session: AsyncSession, cursor_store: CursorStore):
        self.session = session
        self.cursor_store = cursor_store
        self.repo = AsyncReadingRepository(session)

    async def get_next_reading(
        self, transformer_id: str | None = None, session_id: str | None = None
    ) -> NextReadingApiResponse:
        """
        Advance session cursor and retrieve the next sequential sensor reading.

        Workflow:
        1. Resolve session ID (generate fresh UUID if missing or blank).
        2. Resolve transformer identifier (falls back to default/first transformer).
        3. Check dataset boundaries (total readings, max sequence).
        4. Atomically advance cursor in Redis / CursorStore.
        5. Fetch telemetry record from PostgreSQL at advanced sequence.
        6. Return clean frontend payload with has_next and is_end_of_dataset flags.
        """
        # Step 1: Session identification
        clean_session_id = (
            session_id.strip() if (session_id and session_id.strip()) else str(uuid.uuid4())
        )

        # Step 2: Transformer resolution
        if transformer_id:
            tx = await self.repo.get_transformer_by_identifier(transformer_id)
            if not tx:
                raise ResourceNotFoundError(resource="Transformer", identifier=transformer_id)
        else:
            tx = await self.repo.get_default_transformer()
            if not tx:
                raise ResourceNotFoundError(
                    resource="Transformer",
                    identifier="any registered transformer (database has no transformers)",
                )

        tx_business_id = tx.transformer_id
        tx_db_id = tx.id

        # Step 3: Dataset sequence bounds
        total_readings = await self.repo.count_readings_for_transformer(tx_db_id)
        max_sequence = await self.repo.get_max_sequence(tx_db_id) or 0

        if total_readings == 0 or max_sequence == 0:
            logger.info(f"Transformer '{tx_business_id}' has no readings in database.")
            return NextReadingApiResponse(
                success=True,
                data=NextReadingData(
                    transformer_id=tx_business_id,
                    voltage=None,
                    current=None,
                    temperature=None,
                    sequence=None,
                    has_next=False,
                    is_end_of_dataset=True,
                    session_id=clean_session_id,
                    total_readings=0,
                ),
            )

        # Step 4: Atomically advance session cursor
        next_seq = await self.cursor_store.advance_cursor(
            session_id=clean_session_id, transformer_id=tx_business_id, max_sequence=max_sequence
        )

        # Step 5: Check end of dataset
        if next_seq > max_sequence:
            logger.info(
                f"Session '{clean_session_id}' reached end of dataset "
                f"for transformer '{tx_business_id}' "
                f"(next_seq {next_seq} > max_sequence {max_sequence})."
            )
            return NextReadingApiResponse(
                success=True,
                data=NextReadingData(
                    transformer_id=tx_business_id,
                    voltage=None,
                    current=None,
                    temperature=None,
                    sequence=None,
                    has_next=False,
                    is_end_of_dataset=True,
                    session_id=clean_session_id,
                    total_readings=total_readings,
                ),
            )

        # Step 6: Fetch actual reading from database
        reading = await self.repo.get_reading_by_sequence(tx_db_id, next_seq)
        if not reading:
            logger.warning(
                f"Reading sequence {next_seq} missing for transformer "
                f"'{tx_business_id}'. Marking end of dataset."
            )
            return NextReadingApiResponse(
                success=True,
                data=NextReadingData(
                    transformer_id=tx_business_id,
                    voltage=None,
                    current=None,
                    temperature=None,
                    sequence=None,
                    has_next=False,
                    is_end_of_dataset=True,
                    session_id=clean_session_id,
                    total_readings=total_readings,
                ),
            )

        has_next = next_seq < max_sequence

        return NextReadingApiResponse(
            success=True,
            data=NextReadingData(
                transformer_id=tx_business_id,
                voltage=reading.voltage,
                current=reading.current,
                temperature=reading.temperature,
                sequence=reading.reading_sequence,
                has_next=has_next,
                is_end_of_dataset=False,
                session_id=clean_session_id,
                total_readings=total_readings,
            ),
        )

    async def reset_session_cursor(self, transformer_id: str, session_id: str) -> None:
        """Reset the cursor for a specific session and transformer to the start."""
        clean_session_id = session_id.strip() if session_id else ""
        if clean_session_id:
            await self.cursor_store.reset_cursor(clean_session_id, transformer_id)
