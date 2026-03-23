"""OpenAPI helpers for consistent error response documentation."""

from typing import Any

from app.core.exceptions import ErrorResponse

_ERROR_MAP: dict[int, tuple[str, str, str]] = {
    401: ("Unauthorized — JWT отсутствует или невалиден", "UNAUTHORIZED", "Не авторизован"),
    403: ("Forbidden — недостаточно прав", "FORBIDDEN", "Нет доступа"),
    404: ("Not Found — ресурс не найден", "NOT_FOUND", "Ресурс не найден"),
    409: ("Conflict — конфликт данных (дубликат и т.д.)", "CONFLICT", "Конфликт данных"),
    422: ("Validation Error — ошибка валидации запроса", "VALIDATION_ERROR", "Ошибка валидации"),
    429: ("Rate Limited — слишком много запросов", "RATE_LIMITED", "Слишком много запросов"),
}


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Build ``responses`` dict for FastAPI route decorator.

    Usage::

        @router.get("/items/{id}", responses=error_responses(404))
        @router.post("/items", responses=error_responses(401, 409, 422))
    """
    result: dict[int | str, dict[str, Any]] = {}
    for code in codes:
        if code not in _ERROR_MAP:
            continue
        desc, err_code, msg = _ERROR_MAP[code]
        result[code] = {
            "description": desc,
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": {"code": err_code, "message": msg, "details": {}}
                    }
                }
            },
        }
    return result
