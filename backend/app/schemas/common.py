from typing import Any, Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str | None = None
    data: DataT | None = None
    meta: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginationMeta(BaseModel):
    total: int
    skip: int
    limit: int
    has_more: bool


class PaginatedData(BaseModel, Generic[DataT]):
    items: list[DataT]
    pagination: PaginationMeta
