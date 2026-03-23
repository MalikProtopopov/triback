"""Domain-split FastAPI dependencies (re-exported from ``app.core.dependencies``)."""

from app.core.deps.auth import (
    ACCESS_TOKEN_COOKIE_KEY,
    get_current_user,
    get_current_user_id,
    get_optional_user_id,
    oauth2_scheme,
)
from app.core.deps.pagination import get_pagination

__all__ = [
    "ACCESS_TOKEN_COOKIE_KEY",
    "get_current_user",
    "get_current_user_id",
    "get_optional_user_id",
    "get_pagination",
    "oauth2_scheme",
]
