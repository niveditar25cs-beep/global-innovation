from app.data_access.database import (
    AsyncSessionLocal,
    Base,
    SessionLocal,
    async_engine,
    engine,
    get_async_db,
    get_db,
    init_db,
)

# Repos are imported lazily here to avoid circular imports at module initialization.
# Models import from app.data_access.database directly; repos import models.
# Importing repos at the top of this __init__ would create a circular dependency.


def __getattr__(name: str):
    if name == "TransformerRepository":
        from app.data_access.transformer_repo import TransformerRepository

        return TransformerRepository
    if name == "ReadingRepository":
        from app.data_access.reading_repo import ReadingRepository

        return ReadingRepository
    if name in ("TransformerDatasetManager", "dataset_manager"):
        from app.data_access.dataset_manager import TransformerDatasetManager, dataset_manager

        if name == "TransformerDatasetManager":
            return TransformerDatasetManager
        return dataset_manager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AsyncSessionLocal",
    "Base",
    "ReadingRepository",
    "SessionLocal",
    "TransformerDatasetManager",
    "TransformerRepository",
    "async_engine",
    "dataset_manager",
    "engine",
    "get_async_db",
    "get_db",
    "init_db",
]
