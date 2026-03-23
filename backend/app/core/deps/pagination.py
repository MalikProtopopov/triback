"""Common query pagination dependency."""

from fastapi import Query


def get_pagination(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, int]:
    """Return pagination parameters as a dict."""
    return {"limit": limit, "offset": offset}
