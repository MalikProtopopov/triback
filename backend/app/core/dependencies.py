"""FastAPI dependencies — shim re-exporting ``app.core.deps``."""

from app.core.deps import (
    ACCESS_TOKEN_COOKIE_KEY,
    get_current_user,
    get_current_user_id,
    get_optional_user_id,
    get_pagination,
    oauth2_scheme,
)

__all__ = [
    "ACCESS_TOKEN_COOKIE_KEY",
    "get_current_user",
    "get_current_user_id",
    "get_optional_user_id",
    "get_pagination",
    "oauth2_scheme",
]
