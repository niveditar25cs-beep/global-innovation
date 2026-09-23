"""
Initial migration: Create transformer monitoring database schema.

Tables created:
- transformers
- transformer_readings
- network_connections
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── transformers ─────────────────────────────────────────────────────────
    op.create_table(
        "transformers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "transformer_id",
            sa.String(length=100),
            nullable=False,
            comment="Unique identifier for the transformer (e.g. TX-01)",
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=True,
            comment="Descriptive name or label for the transformer unit",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Extensible transformer metadata including ratings, location, manufacturer",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Creation timestamp with timezone",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Last updated timestamp with timezone",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transformers"),
    )
    # Unique index on business identifier
    op.create_index(
        "uq_transformer_id",
        "transformers",
        ["transformer_id"],
        unique=True,
    )
    # GIN index for JSONB metadata queries
    op.create_index(
        "ix_transformers_metadata_gin",
        "transformers",
        ["metadata"],
        postgresql_using="gin",
    )

    # ─── transformer_readings ─────────────────────────────────────────────────
    op.create_table(
        "transformer_readings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "transformer_id",
            sa.BigInteger(),
            nullable=False,
            comment="Foreign key referencing transformers.id",
        ),
        sa.Column(
            "reading_sequence",
            sa.BigInteger(),
            nullable=False,
            comment="Sequential reading number or index per transformer",
        ),
        sa.Column(
            "voltage",
            sa.Double(),
            nullable=False,
            comment="Primary voltage measurement (e.g. kV)",
        ),
        sa.Column(
            "current",
            sa.Double(),
            nullable=False,
            comment="Primary current measurement (e.g. A)",
        ),
        sa.Column(
            "temperature",
            sa.Double(),
            nullable=False,
            comment="Primary temperature measurement (e.g. top oil or winding °C)",
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Actual or simulated reading timestamp",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="System creation timestamp with timezone",
        ),
        sa.Column(
            "sensor_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Extensible JSONB container for future IoT and edge sensor metrics",
        ),
        sa.ForeignKeyConstraint(
            ["transformer_id"],
            ["transformers.id"],
            name="fk_transformer_readings_transformer_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transformer_readings"),
        sa.UniqueConstraint(
            "transformer_id",
            "reading_sequence",
            name="uq_transformer_reading_seq",
        ),
    )
    # Index for FK lookups
    op.create_index(
        "ix_transformer_readings_transformer_id",
        "transformer_readings",
        ["transformer_id"],
    )
    # Composite index for time-series range queries and windowing
    op.create_index(
        "ix_transformer_reading_lookup",
        "transformer_readings",
        ["transformer_id", "timestamp"],
    )
    # Index on timestamp alone for global time range scans
    op.create_index(
        "ix_transformer_readings_timestamp",
        "transformer_readings",
        ["timestamp"],
    )
    # GIN index on extensible sensor_data JSONB
    op.create_index(
        "ix_transformer_readings_sensor_data_gin",
        "transformer_readings",
        ["sensor_data"],
        postgresql_using="gin",
    )

    # ─── network_connections ─────────────────────────────────────────────────
    op.create_table(
        "network_connections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "source_transformer_id",
            sa.BigInteger(),
            nullable=False,
            comment="Source transformer node identifier",
        ),
        sa.Column(
            "target_transformer_id",
            sa.BigInteger(),
            nullable=False,
            comment="Target transformer node identifier",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Connection technical attributes (impedance, length, capacity, status)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Creation timestamp with timezone",
        ),
        sa.ForeignKeyConstraint(
            ["source_transformer_id"],
            ["transformers.id"],
            name="fk_network_connections_source",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_transformer_id"],
            ["transformers.id"],
            name="fk_network_connections_target",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_network_connections"),
        sa.UniqueConstraint(
            "source_transformer_id",
            "target_transformer_id",
            name="uq_network_connection_edge",
        ),
        sa.CheckConstraint(
            "source_transformer_id != target_transformer_id",
            name="ck_network_connection_no_self_loop",
        ),
    )
    # Indexes on both FK columns
    op.create_index(
        "ix_network_connections_source",
        "network_connections",
        ["source_transformer_id"],
    )
    op.create_index(
        "ix_network_connections_target",
        "network_connections",
        ["target_transformer_id"],
    )
    # GIN index on connection metadata JSONB
    op.create_index(
        "ix_network_connections_metadata_gin",
        "network_connections",
        ["metadata"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_table("network_connections")
    op.drop_table("transformer_readings")
    op.drop_table("transformers")
