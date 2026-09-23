from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Any | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class ResourceNotFoundError(AppException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} with identifier '{identifier}' was not found.",
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)},
        )


class ConflictError(AppException):
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(
            message=message, code="RESOURCE_CONFLICT", status_code=409, details=details
        )


class ValidationException(AppException):
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422, details=details)


class DatasetException(AppException):
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(
            message=message, code="DATASET_PROCESSING_ERROR", status_code=400, details=details
        )
