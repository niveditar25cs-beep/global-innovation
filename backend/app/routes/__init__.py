from fastapi import APIRouter

from app.routes.dataset_routes import router as dataset_router
from app.routes.health_routes import router as health_router
from app.routes.network_routes import router as network_router
from app.routes.reading_routes import router as reading_router
from app.routes.transformer_routes import router as transformer_router


def get_api_router() -> APIRouter:
    api_router = APIRouter()
    api_router.include_router(health_router)
    api_router.include_router(transformer_router)
    api_router.include_router(reading_router)
    api_router.include_router(dataset_router)
    api_router.include_router(network_router)
    return api_router


__all__ = ["get_api_router"]
