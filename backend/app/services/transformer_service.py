from sqlalchemy.orm import Session

from app.data_access.transformer_repo import TransformerRepository
from app.error_handling.exceptions import ConflictError, ResourceNotFoundError
from app.models.transformer import Transformer
from app.schemas.transformer import TransformerCreate, TransformerUpdate


class TransformerService:
    def __init__(self, db: Session):
        self.repo = TransformerRepository(db)

    def get_transformer(self, transformer_id: str) -> Transformer:
        transformer = self.repo.get_by_id(transformer_id)
        if not transformer:
            raise ResourceNotFoundError(resource="Transformer", identifier=transformer_id)
        return transformer

    def list_transformers(
        self, skip: int = 0, limit: int = 100, status: str | None = None, search: str | None = None
    ) -> tuple[list[Transformer], int]:
        items = self.repo.get_all(skip=skip, limit=limit, status=status, search=search)
        total = self.repo.count(status=status)
        return items, total

    def create_transformer(self, data: TransformerCreate) -> Transformer:
        existing = self.repo.get_by_id(data.id)
        if existing:
            raise ConflictError(
                f"Transformer with ID '{data.id}' already exists in the system.",
                details={"transformer_id": data.id},
            )

        new_tr = Transformer(
            transformer_id=data.id,
            name=data.name,
            metadata_payload={
                "location": data.location,
                "rating_mva": data.rating_mva,
                "voltage_rating_kv": data.voltage_rating_kv,
                "installation_date": data.installation_date,
                "manufacturer": data.manufacturer,
                "status": data.status or "operational",
            },
        )
        return self.repo.create(new_tr)

    def update_transformer(self, transformer_id: str, data: TransformerUpdate) -> Transformer:
        transformer = self.get_transformer(transformer_id)
        update_dict = data.model_dump(exclude_unset=True)
        return self.repo.update(transformer, update_dict)

    def delete_transformer(self, transformer_id: str) -> None:
        transformer = self.get_transformer(transformer_id)
        self.repo.delete(transformer)
