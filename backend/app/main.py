import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.data_access.database import SessionLocal, async_engine, engine, init_db
from app.error_handling.handlers import register_exception_handlers
from app.routes import get_api_router
from app.security.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.services.dataset_service import DatasetService
from app.state.redis_manager import close_redis_client, init_redis_client
from app.state.store_factory import close_cursor_store, init_cursor_store

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("transformer_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database schema and auto-seed sample data if empty
    logger.info("Initializing Transformer Failure Risk Monitoring Backend...")
    init_db()
    db = SessionLocal()
    try:
        dataset_service = DatasetService(db)
        seed_result = dataset_service.seed_sample_if_empty()
        if seed_result:
            logger.info(
                f"Auto-seeded database with sample dataset: "
                f"{seed_result.readings_stored} readings across "
                f"{seed_result.transformers_registered} transformers."
            )
        else:
            logger.info("Database already seeded with transformer sensor records.")
    except Exception as e:
        logger.warning(f"Could not auto-seed sample dataset: {e}")
    finally:
        db.close()

    # Initialize Redis connection pool (graceful fallback if offline)
    await init_redis_client()

    # Initialize stateful reading cursor store (Redis or InMemory fallback)
    await init_cursor_store()

    yield

    # Shutdown: Close cursor store and Redis pool, then dispose DB engines cleanly
    await close_cursor_store()
    await close_redis_client()
    try:
        await async_engine.dispose()
    except Exception as e:
        logger.warning(f"Error disposing async_engine: {e}")
    try:
        engine.dispose()
    except Exception as e:
        logger.warning(f"Error disposing engine: {e}")
    logger.info("Shutting down Transformer Failure Risk Monitoring Backend...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            "Backend Foundation for Transformer Failure Risk Monitoring System "
            "(Backend Member 1).\n\n"
            "Provides dataset management, transformer network registry, "
            "real-time current readings, sequential simulated stream playback "
            "(next reading), historical time-series retrieval, "
            "and network topology data.\n\n"
            "Official API version: **v1** (`/api/v1`)"
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 1. Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
            "X-Request-ID",
            "X-API-Key",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time-Ms",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ],
    )

    # 2. Structured Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # 3. Security Headers Middleware (OWASP posture)
    app.add_middleware(SecurityHeadersMiddleware)

    # Register custom exception handlers
    register_exception_handlers(app)

    # Mount primary versioned API routes under /api/v1
    api_router = get_api_router()
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Backwards-compatible legacy mount under /api (hidden from schema docs)
    app.include_router(api_router, prefix=settings.API_PREFIX, include_in_schema=False)

    @app.get("/", include_in_schema=False)
    def root():
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "api_v1": settings.API_V1_STR,
            "api_prefix": settings.API_PREFIX,
            "status": "online",
        }

    return app


app = create_app()
