from datetime import datetime

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from app.models.reading import TransformerReading
from app.models.transformer import Transformer


class ReadingRepository:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_transformer_db_id(self, transformer_id: str) -> int | None:
        if str(transformer_id).isdigit():
            tx = (
                self.db.query(Transformer.id)
                .filter(
                    (Transformer.transformer_id == str(transformer_id))
                    | (Transformer.id == int(transformer_id))
                )
                .first()
            )
        else:
            tx = (
                self.db.query(Transformer.id)
                .filter(Transformer.transformer_id == str(transformer_id))
                .first()
            )
        return tx[0] if tx else None

    def get_latest_reading(self, transformer_id: str) -> TransformerReading | None:
        db_id = self._resolve_transformer_db_id(transformer_id)
        if db_id is None:
            return None
        return (
            self.db.query(TransformerReading)
            .filter(TransformerReading.transformer_id == db_id)
            .order_by(desc(TransformerReading.timestamp))
            .first()
        )

    def get_first_reading(self, transformer_id: str) -> TransformerReading | None:
        db_id = self._resolve_transformer_db_id(transformer_id)
        if db_id is None:
            return None
        return (
            self.db.query(TransformerReading)
            .filter(TransformerReading.transformer_id == db_id)
            .order_by(asc(TransformerReading.timestamp))
            .first()
        )

    def get_all_latest_readings(self) -> list[TransformerReading]:
        """Fetch the most recent reading for each transformer in the network."""
        subquery = (
            self.db.query(
                TransformerReading.transformer_id,
                func.max(TransformerReading.timestamp).label("max_ts"),
            )
            .group_by(TransformerReading.transformer_id)
            .subquery()
        )

        return (
            self.db.query(TransformerReading)
            .join(
                subquery,
                (TransformerReading.transformer_id == subquery.c.transformer_id)
                & (TransformerReading.timestamp == subquery.c.max_ts),
            )
            .all()
        )

    def get_history(
        self,
        transformer_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
        order: str = "desc",
    ) -> list[TransformerReading]:
        db_id = self._resolve_transformer_db_id(transformer_id)
        if db_id is None:
            return []
        query = self.db.query(TransformerReading).filter(TransformerReading.transformer_id == db_id)
        if start_time:
            query = query.filter(TransformerReading.timestamp >= start_time)
        if end_time:
            query = query.filter(TransformerReading.timestamp <= end_time)

        if order.lower() == "asc":
            query = query.order_by(asc(TransformerReading.timestamp))
        else:
            query = query.order_by(desc(TransformerReading.timestamp))

        return query.offset(skip).limit(limit).all()

    def count_history(
        self,
        transformer_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        db_id = self._resolve_transformer_db_id(transformer_id)
        if db_id is None:
            return 0
        query = self.db.query(func.count(TransformerReading.id)).filter(
            TransformerReading.transformer_id == db_id
        )
        if start_time:
            query = query.filter(TransformerReading.timestamp >= start_time)
        if end_time:
            query = query.filter(TransformerReading.timestamp <= end_time)
        return query.scalar() or 0

    def get_reading_after(
        self, transformer_id: str, after_timestamp: datetime
    ) -> TransformerReading | None:
        db_id = self._resolve_transformer_db_id(transformer_id)
        if db_id is None:
            return None
        return (
            self.db.query(TransformerReading)
            .filter(
                TransformerReading.transformer_id == db_id,
                TransformerReading.timestamp > after_timestamp,
            )
            .order_by(asc(TransformerReading.timestamp))
            .first()
        )

    def create(self, reading: TransformerReading) -> TransformerReading:
        self.db.add(reading)
        try:
            self.db.commit()
            self.db.refresh(reading)
            return reading
        except Exception:
            self.db.rollback()
            raise

    def bulk_create(self, readings: list[TransformerReading], batch_size: int = 500) -> int:
        if not readings:
            return 0
        total = 0
        for i in range(0, len(readings), batch_size):
            chunk = readings[i : i + batch_size]
            self.db.bulk_save_objects(chunk)
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            total += len(chunk)
        return total

    def count_total(self) -> int:
        return self.db.query(func.count(TransformerReading.id)).scalar() or 0

    def clear_all(self, transformer_id: str | None = None) -> int:
        query = self.db.query(TransformerReading)
        if transformer_id:
            db_id = self._resolve_transformer_db_id(transformer_id)
            if db_id is not None:
                query = query.filter(TransformerReading.transformer_id == db_id)
            else:
                return 0
        count = query.delete(synchronize_session=False)
        try:
            self.db.commit()
            return count
        except Exception:
            self.db.rollback()
            raise
