"""
Alembic env.py for Transformer Failure Risk Monitoring System.
Uses synchronous psycopg2/asyncpg-compatible URL for Alembic migrations.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add the backend directory to sys.path so app modules can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models and Base so Alembic can detect all model metadata
from app.data_access.database import Base
import app.models  # noqa: F401 – ensure all models are registered with Base.metadata

# Load Alembic config object (gives access to alembic.ini values)
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata used for 'autogenerate' support
target_metadata = Base.metadata


def get_sync_url() -> str:
    """
    Return a synchronous database URL.
    Converts postgresql+asyncpg:// → postgresql:// for psycopg2-based Alembic runs.
    """
    from app.config import settings

    url = settings.resolved_sync_database_url
    # Alembic with psycopg2 needs postgresql:// (without driver specifier) or postgresql+psycopg2://
    if url.startswith("postgresql://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return url
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection, just SQL output)."""
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with live DB connection)."""
    # Override sqlalchemy.url in alembic.ini with our dynamically resolved URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_sync_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
