"""
Security headers and structured request logging middlewares.
Guarantees standard OWASP security posture, request tracking, and zero secret leakage in logs.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.utils.sanitizer import mask_connection_string

logger = logging.getLogger("transformer_backend.access")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects standard security headers into all HTTP responses.
    Mitigates MIME confusion, clickjacking, XSS, and unauthorized feature access.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if settings.ENABLE_SECURITY_HEADERS:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            response.headers["Content-Security-Policy"] = "default-src 'self'"

            if settings.STRICT_TRANSPORT_SECURITY:
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Assigns unique X-Request-ID to every request, measures execution duration,
    and logs request details with sensitive parameters automatically redacted.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate or capture existing request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            client_ip = request.client.host if request.client else "unknown"
            safe_path = mask_connection_string(request.url.path)
            logger.exception(
                f"[{request_id}] {request.method} {safe_path} ERROR {type(e).__name__} "
                f"in {elapsed_ms:.2f}ms (client: {client_ip})"
            )
            from starlette.responses import JSONResponse

            resp = JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": (
                            "An unexpected error occurred while processing your request. "
                            "Please reference the request ID."
                        ),
                        "details": None,
                        "request_id": request_id,
                    },
                },
            )
            resp.headers["X-Request-ID"] = request_id
            resp.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
            return resp

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        client_ip = request.client.host if request.client else "unknown"
        safe_path = mask_connection_string(request.url.path)

        # Attach telemetry headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"

        # Structured access log
        logger.info(
            f"[{request_id}] {request.method} {safe_path} -> {response.status_code} "
            f"({elapsed_ms:.2f}ms) [client: {client_ip}]"
        )

        return response
