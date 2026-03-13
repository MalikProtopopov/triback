"""Custom HTTP exceptions and RFC 7807 error format."""

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all error handlers."""

    error: ErrorDetail

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": {
                "code": "NOT_FOUND",
                "message": "Resource not found",
                "details": {},
            }
        }
    })


class AppError(HTTPException):
    """Base application error with RFC 7807-inspired body."""

    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        self.error_code = code
        self.error_message = message
        self.error_details = details or {}
        super().__init__(status_code=status_code, detail=message)

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.error_code,
                "message": self.error_message,
                "details": self.error_details,
            }
        }


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: dict | None = None):
        super().__init__(404, "NOT_FOUND", message, details)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access forbidden", details: dict | None = None):
        super().__init__(403, "FORBIDDEN", message, details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized", details: dict | None = None):
        super().__init__(401, "UNAUTHORIZED", message, details)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", details: dict | None = None):
        super().__init__(409, "CONFLICT", message, details)


class AppValidationError(AppError):
    def __init__(self, message: str = "Validation error", details: dict | None = None):
        super().__init__(422, "VALIDATION_ERROR", message, details)


class NotImplementedAppError(AppError):
    def __init__(self, message: str = "Not implemented", details: dict | None = None):
        super().__init__(501, "NOT_IMPLEMENTED", message, details)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


async def generic_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "details": {},
            }
        },
    )


def register_exception_handlers(app: object) -> None:
    """Register all custom exception handlers on the FastAPI app."""
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, generic_http_exception_handler)  # type: ignore[arg-type]
