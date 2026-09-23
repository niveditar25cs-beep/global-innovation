"""
Rate limiting dependency powered by Redis with fail-open resilience.
Enforces request thresholds per client IP without crashing if Redis is offline.
"""

import logging

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

from app.config import settings
from app.state.redis_manager import get_redis_client

logger = logging.getLogger("transformer_backend.ratelimit")


class RateLimiter:
    """
    FastAPI dependency implementing atomic counter-based rate limiting via Redis.
    Fails open (allows traffic) if Redis becomes unavailable.
    """

    def __init__(
        self,
        requests: int | None = None,
        window_seconds: int | None = None,
        scope: str = "global",
        redis_client: aioredis.Redis | None = None,
    ):
        self.requests = requests or settings.REDIS_RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or settings.REDIS_RATE_LIMIT_WINDOW_SECONDS
        self.scope = scope
        self._custom_client = redis_client

    @property
    def client(self) -> aioredis.Redis | None:
        return self._custom_client if self._custom_client is not None else get_redis_client()

    def _resolve_client_identifier(self, request: Request) -> str:
        """Extract client IP address or forwarded identifier."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown_client"

    async def __call__(self, request: Request) -> None:
        """
        Evaluate rate limit for the incoming HTTP request.
        Fails open if rate limiting is disabled or if Redis is unreachable.
        """
        if not settings.REDIS_RATE_LIMIT_ENABLED:
            return

        client = self.client
        if client is None:
            # Redis is offline: Fail-open to preserve system availability
            return

        client_id = self._resolve_client_identifier(request)
        key = f"ratelimit:{self.scope}:{client_id}"

        try:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            results = await pipe.execute()
            current_count = int(results[0])
            ttl = int(results[1])

            # If key was newly created, set expiry window
            if ttl == -1:
                await client.expire(key, self.window_seconds)
                ttl = self.window_seconds

            remaining = max(0, self.requests - current_count)

            # Store headers in request state for middleware or test inspection
            request.state.ratelimit_limit = self.requests
            request.state.ratelimit_remaining = remaining
            request.state.ratelimit_reset = ttl

            if current_count > self.requests:
                logger.warning(
                    f"Rate limit exceeded for client {client_id} on scope '{self.scope}' "
                    f"({current_count}/{self.requests} in {self.window_seconds}s)"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Rate limit exceeded ({self.requests} requests"
                        f" per {self.window_seconds}s). Retry in {ttl}s."
                    ),
                    headers={
                        "Retry-After": str(max(1, ttl)),
                        "X-RateLimit-Limit": str(self.requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(ttl),
                    },
                )

        except HTTPException:
            raise
        except Exception as e:
            # Graceful fail-open: Never block requests because of Redis connection hiccups
            logger.debug(f"Rate limiter encountered Redis error ({e}); failing open.")
            return
