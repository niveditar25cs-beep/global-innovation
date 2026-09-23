from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, Double, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.database import Base

if TYPE_CHECKING:
    from app.models.transformer import Transformer


class TransformerReading(Base):
    __tablename__ = "transformer_readings"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key to Transformer
    transformer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("transformers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing transformers.id",
    )

    # Reading sequence or stream index
    reading_sequence: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Sequential reading number or index per transformer"
    )

    # Primary Electrical Metrics
    voltage: Mapped[float] = mapped_column(
        Double, nullable=False, comment="Primary voltage measurement (e.g. kV)"
    )
    current: Mapped[float] = mapped_column(
        Double, nullable=False, comment="Primary current measurement (e.g. A)"
    )

    # Thermal Metric
    temperature: Mapped[float] = mapped_column(
        Double,
        nullable=False,
        comment="Primary temperature measurement (e.g. top oil or winding °C)",
    )

    # Telemetry Timestamp (actual or simulated)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Actual or simulated reading timestamp",
    )

    # Record insertion timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="System creation timestamp with timezone",
    )

    # Extensible payload for multi-modal sensor telemetry
    # (vibration, DGA gas ppm, acoustic, humidity, oil levels, etc.)
    sensor_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Extensible JSONB container for future IoT and edge sensor metrics",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Guarantee reading sequence is unique per transformer
        UniqueConstraint("transformer_id", "reading_sequence", name="uq_transformer_reading_seq"),
        # Composite index for optimized time-series range queries and windowing
        Index("ix_transformer_reading_lookup", "transformer_id", "timestamp"),
    )

    # Relationships
    transformer: Mapped["Transformer"] = relationship("Transformer", back_populates="readings")

    @property
    def voltage_kv(self) -> float:
        return self.voltage

    @property
    def current_a(self) -> float:
        return self.current

    @property
    def oil_temperature_c(self) -> float:
        return self.temperature

    @property
    def winding_temperature_c(self) -> float:
        return float((self.sensor_data or {}).get("winding_temperature_c", self.temperature))

    @property
    def oil_level_pct(self) -> float:
        return float((self.sensor_data or {}).get("oil_level_pct", 85.0))

    @property
    def vibration_mm_s(self) -> float:
        return float((self.sensor_data or {}).get("vibration_mm_s", 1.0))

    @property
    def load_percentage(self) -> float:
        return float((self.sensor_data or {}).get("load_percentage", 70.0))

    @property
    def ambient_temperature_c(self) -> float:
        return float((self.sensor_data or {}).get("ambient_temperature_c", 25.0))

    @property
    def humidity_pct(self) -> float:
        return float((self.sensor_data or {}).get("humidity_pct", 60.0))

    @property
    def dissolved_gas_ppm(self) -> float:
        return float((self.sensor_data or {}).get("dissolved_gas_ppm", 45.0))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "transformer_id": self.transformer_id,
            "reading_sequence": self.reading_sequence,
            "voltage": self.voltage,
            "current": self.current,
            "temperature": self.temperature,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sensor_data": self.sensor_data,
        }
