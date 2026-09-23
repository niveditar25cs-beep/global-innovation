from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.controllers.transformer_controller import TransformerController
from app.data_access.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.transformer import TransformerCreate, TransformerUpdate
from app.state.cache_service import CacheService, get_cache_service
from app.state.rate_limiter import RateLimiter

router = APIRouter(prefix="/transformers", tags=["Transformers"])


@router.get(
    "", response_model=ApiResponse, dependencies=[Depends(RateLimiter(scope="transformers_list"))]
)
async def list_transformers(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    status: str | None = Query(
        None,
        pattern="^(operational|maintenance|offline)$",
        description="Filter by status",
    ),
    search: str | None = Query(None, description="Search term for name, location, or ID"),
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
):
    """Retrieve a paginated list of transformers in the grid network (cached in Redis)."""
    cache_key = f"list:{skip}:{limit}:{status}:{search}"
    cached = await cache.get(cache_key, prefix="transformers")
    if cached is not None:
        return ApiResponse.model_validate(cached)

    controller = TransformerController(db)
    response = await run_in_threadpool(
        controller.list_transformers, skip=skip, limit=limit, status=status, search=search
    )
    await cache.set(cache_key, response.model_dump(), prefix="transformers", ttl=60)
    return response


@router.get("/{transformer_id}", response_model=ApiResponse)
async def get_transformer(
    transformer_id: str = Path(..., description="Unique transformer identifier"),
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
):
    """Retrieve detailed metadata for a specific transformer (cached in Redis)."""
    cache_key = f"item:{transformer_id}"
    cached = await cache.get(cache_key, prefix="transformers")
    if cached is not None:
        return ApiResponse.model_validate(cached)

    controller = TransformerController(db)
    response = await run_in_threadpool(controller.get_transformer, transformer_id)
    await cache.set(cache_key, response.model_dump(), prefix="transformers", ttl=60)
    return response


@router.post("", response_model=ApiResponse, status_code=201)
async def create_transformer(
    payload: TransformerCreate,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
):
    """Register a new transformer in the network and invalidate cache."""
    controller = TransformerController(db)
    response = await run_in_threadpool(controller.create_transformer, payload)
    await cache.delete_prefix("transformers")
    return response


@router.put("/{transformer_id}", response_model=ApiResponse)
async def update_transformer(
    payload: TransformerUpdate,
    transformer_id: str = Path(..., description="Unique transformer identifier"),
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
):
    """Update metadata for an existing transformer and invalidate cache."""
    controller = TransformerController(db)
    response = await run_in_threadpool(controller.update_transformer, transformer_id, payload)
    await cache.delete_prefix("transformers")
    return response


@router.delete("/{transformer_id}", response_model=ApiResponse)
async def delete_transformer(
    transformer_id: str = Path(..., description="Unique transformer identifier"),
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
):
    """Decommission and remove a transformer and invalidate cache."""
    controller = TransformerController(db)
    response = await run_in_threadpool(controller.delete_transformer, transformer_id)
    await cache.delete_prefix("transformers")
    return response
