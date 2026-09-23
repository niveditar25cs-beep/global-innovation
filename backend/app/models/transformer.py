from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.database import Base

if TYPE_CHECKING:
    from app.models.network_connection import NetworkConnection
    from app.models.reading import TransformerReading


class Transformer(Base):
    __tablename__ = "transformers"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Domain / Business Identifier
    transformer_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique identifier for the transformer (e.g. TX-01)",
    )

    # Human-readable name / label
    name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Descriptive name or label for the transformer unit"
    )

    # Flexible metadata (specifications, location, ratings, manufacturer, etc.)
    # In PostgreSQL this maps directly to column 'metadata' of type JSONB
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Extensible transformer metadata including ratings, location, manufacturer",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp with timezone",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last updated timestamp with timezone",
    )

    # Relationships
    readings: Mapped[list["TransformerReading"]] = relationship(
        "TransformerReading",
        back_populates="transformer",
        cascade="all, delete-orphan",
        order_by="TransformerReading.timestamp",
    )

    outgoing_connections: Mapped[list["NetworkConnection"]] = relationship(
        "NetworkConnection",
        foreign_keys="NetworkConnection.source_transformer_id",
        back_populates="source_transformer",
        cascade="all, delete-orphan",
    )

    incoming_connections: Mapped[list["NetworkConnection"]] = relationship(
        "NetworkConnection",
        foreign_keys="NetworkConnection.target_transformer_id",
        back_populates="target_transformer",
        cascade="all, delete-orphan",
    )

    @property
    def status(self) -> str:
        return str((self.metadata_payload or {}).get("status", "operational"))

    @status.setter
    def status(self, val: str):
        if self.metadata_payload is None:
            self.metadata_payload = {}
        self.metadata_payload["status"] = val

    @property
    def location(self) -> str | None:
        return (self.metadata_payload or {}).get("location")

    @location.setter
    def location(self, val: str | None):
        if self.metadata_payload is None:
            self.metadata_payload = {}
        self.metadata_payload["location"] = val

    @property
    def rating_mva(self) -> float | None:
        return (self.metadata_payload or {}).get("rating_mva")

    @rating_mva.setter
    def rating_mva(self, val: float | None):
        if self.metadata_payload is None:
            self.metadata_payload = {}
        self.metadata_payload["rating_mva"] = val

    @property
    def voltage_rating_kv(self) -> float | None:
        return (self.metadata_payload or {}).get("voltage_rating_kv")

    @voltage_rating_kv.setter
    def voltage_rating_kv(self, val: float | None):
        if self.metadata_payload is None:
            self.metadata_payload = {}
        self.metadata_payload["voltage_rating_kv"] = val

    @property
    def installation_date(self) -> str | None:
        return (self.metadata_payload or {}).get("installation_date")

    @installation_date.setter
    def installation_date(self, val: str | None):
        if self.metadata_payload is None:
            self.metadata_payload = {}
        self.metadata_payload["installation_date"] = val

    @property
    def manufacturer(self) -> str | None:
        return (self.metadata_payload or {}).get("manufacturer")

    @manufacturer.setter
    def manufacturer(self, val: str | None):
        if self.metadata_payload is None:
            self.metadata_payload = {}
        self.metadata_payload["manufacturer"] = val

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "transformer_id": self.transformer_id,
            "name": self.name,
            "metadata": self.metadata_payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
