from sqlalchemy.orm import Session

from app.schemas.common import ApiResponse
from app.schemas.transformer import TransformerCreate, TransformerResponse, TransformerUpdate
from app.services.transformer_service import TransformerService
from app.utils.response_builder import build_paginated_response, build_response


class TransformerController:
    def __init__(self, db: Session):
        self.service = TransformerService(db)

    def list_transformers(
        self, skip: int = 0, limit: int = 100, status: str | None = None, search: str | None = None
    ) -> ApiResponse:
        transformers, total = self.service.list_transformers(
            skip=skip, limit=limit, status=status, search=search
        )
        data = [TransformerResponse.model_validate(t).model_dump() for t in transformers]
        return build_paginated_response(
            items=data,
            total=total,
            skip=skip,
            limit=limit,
            message="Transformers retrieved successfully.",
        )

    def get_transformer(self, transformer_id: str) -> ApiResponse:
        transformer = self.service.get_transformer(transformer_id)
        data = TransformerResponse.model_validate(transformer).model_dump()
        return build_response(
            data=data, message=f"Transformer '{transformer_id}' retrieved successfully."
        )

    def create_transformer(self, payload: TransformerCreate) -> ApiResponse:
        created = self.service.create_transformer(payload)
        data = TransformerResponse.model_validate(created).model_dump()
        return build_response(
            data=data, message=f"Transformer '{created.id}' created successfully.", status_code=201
        )

    def update_transformer(self, transformer_id: str, payload: TransformerUpdate) -> ApiResponse:
        updated = self.service.update_transformer(transformer_id, payload)
        data = TransformerResponse.model_validate(updated).model_dump()
        return build_response(
            data=data, message=f"Transformer '{transformer_id}' updated successfully."
        )

    def delete_transformer(self, transformer_id: str) -> ApiResponse:
        self.service.delete_transformer(transformer_id)
        return build_response(
            data={"id": transformer_id, "deleted": True},
            message=f"Transformer '{transformer_id}' and all associated records deleted.",
        )
