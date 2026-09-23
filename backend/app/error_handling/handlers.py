"""
Standardized, secure exception handlers for FastAPI.
Guarantees clean, uniform error schemas while strictly preventing credential or stack trace leakage.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.error_handling.exceptions import AppException
from app.utils.sanitizer import mask_connection_string, redact_sensitive_data

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            f"[{request_id}] AppException on {request.method} {request.url.path}: {exc.message}"
        )
        safe_message = mask_connection_string(exc.message)
        safe_details = redact_sensitive_data(exc.details) if exc.details else None

        error_payload: dict[str, Any] = {
            "code": exc.code,
            "message": safe_message,
            "details": safe_details,
        }
        if request_id:
            error_payload["request_id"] = request_id

        content = {"success": False, "error": error_payload}
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", None)
        logger.info(
            "[%s] Validation error on %s %s: %s",
            request_id,
            request.method,
            request.url.path,
            exc.errors(),
        )
        formatted_errors = []
        for err in exc.errors():
            loc = " -> ".join(str(part) for part in err.get("loc", []))
            formatted_errors.append(
                {
                    "field": loc,
                    "message": mask_connection_string(err.get("msg", "Invalid value")),
                    "type": err.get("type", "value_error"),
                }
            )

        error_payload: dict[str, Any] = {
            "code": "REQUEST_VALIDATION_FAILED",
            "message": "The request payload or query parameter failed validation.",
            "details": formatted_errors,
        }
        if request_id:
            error_payload["request_id"] = request_id

        content = {"success": False, "error": error_payload}
        return JSONResponse(status_code=422, content=content)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", None)
        code = "HTTP_ERROR"
        if exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 405:
            code = "METHOD_NOT_ALLOWED"
        elif exc.status_code == 429:
            code = "RATE_LIMIT_EXCEEDED"
        elif exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"

        safe_message = mask_connection_string(str(exc.detail))
        error_payload: dict[str, Any] = {
            "code": code,
            "message": safe_message,
            "details": None,
        }
        if request_id:
            error_payload["request_id"] = request_id

        content = {"success": False, "error": error_payload}
        headers = getattr(exc, "headers", None) or {}
        return JSONResponse(status_code=exc.status_code, content=content, headers=headers)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "[%s] Unhandled server error on %s %s: %s",
            request_id,
            request.method,
            request.url.path,
            mask_connection_string(str(exc)),
        )
        error_payload: dict[str, Any] = {
            "code": "INTERNAL_SERVER_ERROR",
            "message": (
                "An unexpected error occurred while processing your request. "
                "Please reference the request ID."
            ),
            "details": None,
        }
        if request_id:
            error_payload["request_id"] = request_id

        content = {"success": False, "error": error_payload}
        return JSONResponse(status_code=500, content=content)
