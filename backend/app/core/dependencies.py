"""FastAPI dependencies: current user, pagination."""

from typing import Any
from uuid import UUID

from fastapi import Depends, Header, Query
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _extract_token(
    bearer: str | None = Depends(oauth2_scheme),
    x_access_token: str | None = Header(None, alias="X-Access-Token"),
) -> str | None:
    """Get token from Authorization: Bearer or X-Access-Token header."""
    if bearer:
        return bearer
    if x_access_token:
        t = x_access_token.strip()
        return t if t else None
    return None


async def get_current_user(
    token: str | None = Depends(_extract_token),
) -> dict[str, Any]:
    """Return the decoded JWT payload for the current authenticated user."""
    if not token:
        raise UnauthorizedError("Authentication required")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired token")
    return payload


async def get_current_user_id(
    payload: dict[str, Any] = Depends(get_current_user),
) -> UUID:
    """Return the UUID of the currently authenticated user."""
    return UUID(payload["sub"])


async def get_optional_user_id(
    token: str | None = Depends(_extract_token),
) -> UUID | None:
    """Return user UUID if a valid token is present, None otherwise."""
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return UUID(payload["sub"])


def get_pagination(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, int]:
    """Return pagination parameters as a dict."""
    return {"limit": limit, "offset": offset}
