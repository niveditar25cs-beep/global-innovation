"""
Business service for retrieving the currently selected dataset reading.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.async_reading_repo import AsyncReadingRepository
from app.error_handling.exceptions import ResourceNotFoundError
from app.schemas.current_reading import CurrentReadingApiResponse, CurrentReadingData

# Module-level state tracking the currently selected reading sequence per transformer
_SELECTED_SEQUENCES: dict[str, int] = {}


class CurrentReadingService:
    """
    Service coordinating transformer resolution and current reading retrieval.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AsyncReadingRepository(session)

    async def get_current_reading(
        self, transformer_id: str | None = None, sequence: int | None = None
    ) -> CurrentReadingApiResponse:
        """
        Retrieve the currently selected dataset reading from PostgreSQL.

        Selection Logic:
        1. If transformer_id is specified, resolves that transformer;
           otherwise picks the primary default transformer.
        2. If sequence is specified, fetches that exact reading sequence and updates
           the selection state.
        3. If sequence is not specified, uses the currently active sequence cursor
           or defaults to the first reading (sequence 1).
        4. Returns clean, frontend-friendly response with actual stored telemetry.
        """
        # Step 1: Resolve Transformer
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

        # Step 2: Determine and fetch the target reading
        target_seq = sequence if sequence is not None else _SELECTED_SEQUENCES.get(tx_business_id)

        reading = None
        if target_seq is not None:
            reading = await self.repo.get_reading_by_sequence(tx.id, target_seq)

        # Fallback to the first reading in the dataset if no cursor exists or sequence was invalid
        if reading is None:
            if sequence is not None:
                # User explicitly requested a sequence that does not exist
                raise ResourceNotFoundError(
                    resource="TransformerReading",
                    identifier=f"sequence {sequence} for transformer '{tx_business_id}'",
                )
            # Default to first sequential reading
            reading = await self.repo.get_first_reading(tx.id)

        if not reading:
            raise ResourceNotFoundError(
                resource="TransformerReading",
                identifier=f"readings for transformer '{tx_business_id}'",
            )

        # Update active selection state
        _SELECTED_SEQUENCES[tx_business_id] = reading.reading_sequence

        # Step 3: Format clean frontend response
        data = CurrentReadingData(
            transformer_id=tx_business_id,
            voltage=reading.voltage,
            current=reading.current,
            temperature=reading.temperature,
            sequence=reading.reading_sequence,
        )

        return CurrentReadingApiResponse(success=True, data=data)

    @classmethod
    def set_selected_sequence(cls, transformer_id: str, sequence: int) -> None:
        """Programmatically set the selected sequence cursor for a transformer."""
        _SELECTED_SEQUENCES[transformer_id] = sequence

    @classmethod
    def reset_selections(cls) -> None:
        """Reset all selection cursors."""
        _SELECTED_SEQUENCES.clear()
