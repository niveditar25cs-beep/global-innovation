from typing import Any

from app.schemas.common import ApiResponse, PaginatedData, PaginationMeta


def build_response(
    data: Any = None,
    message: str | None = None,
    meta: dict[str, Any] | None = None,
    status_code: int = 200,
) -> ApiResponse:
    """Build a standard typed ApiResponse envelope."""
    return ApiResponse(success=True, message=message, data=data, meta=meta)


def build_paginated_response(
    items: list[Any], total: int, skip: int, limit: int, message: str | None = None
) -> ApiResponse:
    """Build a standard paginated response envelope."""
    meta = PaginationMeta(total=total, skip=skip, limit=limit, has_more=(skip + len(items)) < total)
    paginated_data = PaginatedData(items=items, pagination=meta)
    return ApiResponse(success=True, message=message, data=paginated_data.model_dump())
