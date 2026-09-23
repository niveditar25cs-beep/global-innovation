from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.database import Base

if TYPE_CHECKING:
    from app.models.transformer import Transformer


class NetworkConnection(Base):
    __tablename__ = "network_connections"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Directed edge nodes: source and target transformer references
    source_transformer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("transformers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Source transformer node identifier",
    )

    target_transformer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("transformers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target transformer node identifier",
    )

    # Connection metadata (line impedance, reactance, length, capacity MVA, operational status)
    # Mapped directly to PostgreSQL 'metadata' column
    connection_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Connection technical attributes (impedance, length, capacity, status)",
    )

    # Creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp with timezone",
    )

    __table_args__ = (
        # Ensure single directed connection between two transformer nodes
        UniqueConstraint(
            "source_transformer_id",
            "target_transformer_id",
            name="uq_network_connection_edge",
        ),
        # Prevent self-looping connections
        CheckConstraint(
            "source_transformer_id != target_transformer_id",
            name="ck_network_connection_no_self_loop",
        ),
    )

    # Relationships
    source_transformer: Mapped["Transformer"] = relationship(
        "Transformer", foreign_keys=[source_transformer_id], back_populates="outgoing_connections"
    )

    target_transformer: Mapped["Transformer"] = relationship(
        "Transformer", foreign_keys=[target_transformer_id], back_populates="incoming_connections"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_transformer_id": self.source_transformer_id,
            "target_transformer_id": self.target_transformer_id,
            "metadata": self.connection_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
