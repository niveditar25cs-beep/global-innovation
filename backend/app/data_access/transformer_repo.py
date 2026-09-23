from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.transformer import Transformer


class TransformerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, transformer_id: str) -> Transformer | None:
        query = self.db.query(Transformer)
        if str(transformer_id).isdigit():
            return query.filter(
                or_(
                    Transformer.transformer_id == str(transformer_id),
                    Transformer.id == int(transformer_id),
                )
            ).first()
        return query.filter(Transformer.transformer_id == str(transformer_id)).first()

    def get_all(
        self, skip: int = 0, limit: int = 100, status: str | None = None, search: str | None = None
    ) -> list[Transformer]:
        query = self.db.query(Transformer)
        if search:
            query = query.filter(
                or_(
                    Transformer.name.ilike(f"%{search}%"),
                    Transformer.transformer_id.ilike(f"%{search}%"),
                )
            )
        return query.offset(skip).limit(limit).all()

    def count(self, status: str | None = None) -> int:
        query = self.db.query(func.count(Transformer.id))
        return query.scalar() or 0

    def create(self, transformer: Transformer) -> Transformer:
        self.db.add(transformer)
        try:
            self.db.commit()
            self.db.refresh(transformer)
            return transformer
        except Exception:
            self.db.rollback()
            raise

    def update(self, transformer: Transformer, update_data: dict[str, Any]) -> Transformer:
        meta = dict(transformer.metadata_payload or {})
        for key, value in update_data.items():
            if key == "name":
                setattr(transformer, key, value)
            elif key == "transformer_id":
                transformer.transformer_id = str(value)
            else:
                meta[key] = value
        transformer.metadata_payload = meta
        try:
            self.db.commit()
            self.db.refresh(transformer)
            return transformer
        except Exception:
            self.db.rollback()
            raise

    def delete(self, transformer: Transformer) -> None:
        self.db.delete(transformer)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def bulk_create_or_ignore(self, transformers: list[Transformer]) -> int:
        added_count = 0
        for tr in transformers:
            tid = (
                tr.transformer_id
                if hasattr(tr, "transformer_id") and tr.transformer_id
                else str(getattr(tr, "id", ""))
            )
            existing = self.get_by_id(tid)
            if not existing:
                self.db.add(tr)
                added_count += 1
        try:
            self.db.commit()
            return added_count
        except Exception:
            self.db.rollback()
            raise
