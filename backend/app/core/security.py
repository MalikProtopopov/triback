"""Security utilities: JWT (RS256), Argon2id password hashing, RBAC."""

import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError

_ph = PasswordHasher()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

ALGORITHM = "RS256"

_private_key: str | None = None
_public_key: str | None = None


def _load_private_key() -> str:
    global _private_key
    if _private_key is None:
        _private_key = Path(settings.JWT_PRIVATE_KEY_PATH).read_text()
    return _private_key


def _load_public_key() -> str:
    global _public_key
    if _public_key is None:
        _public_key = Path(settings.JWT_PUBLIC_KEY_PATH).read_text()
    return _public_key


def create_access_token(user_id: UUID, role: str) -> str:
    """Create a short-lived JWT access token signed with RS256."""
    now = datetime.now(tz=UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, _load_private_key(), algorithm=ALGORITHM)


def create_refresh_token(user_id: UUID, jti: str) -> str:
    """Create a long-lived JWT refresh token with a unique jti, signed with RS256."""
    now = datetime.now(tz=UTC)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, _load_private_key(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token using the RS256 public key."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token, _load_public_key(), algorithms=[ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against an Argon2id hash."""
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def require_role(*roles: str) -> Any:
    """FastAPI dependency factory for RBAC role checking."""

    async def _check_role(token: str | None = Depends(oauth2_scheme)) -> dict[str, Any]:
        if not token:
            raise UnauthorizedError("Authentication required")
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            raise UnauthorizedError("Invalid or expired token")
        user_role = payload.get("role", "")
        if user_role not in roles:
            raise ForbiddenError(
                f"Required role(s): {', '.join(roles)}. Your role: {user_role}"
            )
        return payload

    return Depends(_check_role)
