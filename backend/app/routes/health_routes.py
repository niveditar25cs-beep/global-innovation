from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.data_access.database import get_db
from app.schemas.common import ApiResponse
from app.state.redis_manager import check_redis_health
from app.utils.response_builder import build_response

router = APIRouter(prefix="", tags=["Health"])


@router.get("/health", response_model=ApiResponse)
async def health_check(db: Session = Depends(get_db)):
    """Backend service health check reporting DB and Redis status."""
    db_healthy = True
    try:
        await run_in_threadpool(db.execute, text("SELECT 1"))
    except Exception:
        db_healthy = False

    redis_info = await check_redis_health()
    overall_status = "healthy" if db_healthy else "degraded"

    return build_response(
        data={
            "status": overall_status,
            "database": "connected" if db_healthy else "disconnected",
            "redis": redis_info,
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "Transformer Failure Risk Monitoring Backend",
            "version": "1.0.0",
        },
        message="Backend service is operational.",
    )
