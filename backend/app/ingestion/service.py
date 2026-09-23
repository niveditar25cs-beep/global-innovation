"""
Reusable ingestion service for applications, API controllers, and CLI commands.
"""

import asyncio
import io
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.models import IngestionReport
from app.ingestion.pipeline import DatasetIngestionPipeline


class DatasetIngestionService:
    """
    Reusable Service wrapping the dataset ingestion pipeline.
    Provides synchronous and asynchronous methods.
    """

    def __init__(self, batch_size: int = 500):
        self.pipeline = DatasetIngestionPipeline(batch_size=batch_size)

    async def ingest_async(
        self,
        source: str | Path | bytes | io.IOBase,
        filename: str | None = None,
        dry_run: bool = False,
        session: AsyncSession | None = None,
    ) -> IngestionReport:
        """Asynchronously ingest a dataset file or buffer."""
        return await self.pipeline.ingest_source(
            source=source, filename=filename, dry_run=dry_run, session=session
        )

    def ingest_sync(
        self,
        source: str | Path | bytes | io.IOBase,
        filename: str | None = None,
        dry_run: bool = False,
    ) -> IngestionReport:
        """Synchronously ingest a dataset (convenient for CLI and sync workers)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In an already running event loop, create a task or run in thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run, self.ingest_async(source, filename, dry_run=dry_run)
                    ).result()
            else:
                return loop.run_until_complete(self.ingest_async(source, filename, dry_run=dry_run))
        except RuntimeError:
            return asyncio.run(self.ingest_async(source, filename, dry_run=dry_run))

    async def inspect_schema_async(
        self, source: str | Path | bytes | io.IOBase, filename: str | None = None
    ) -> IngestionReport:
        """Validate and inspect dataset schema without writing to database."""
        return await self.ingest_async(source, filename, dry_run=True)
