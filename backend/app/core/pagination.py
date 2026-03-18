"""Pagination types and helpers used across all list endpoints."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PaginationParams:
    """Reusable FastAPI query dependency for limit/offset pagination."""

    def __init__(
        self,
        limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
        offset: int = Query(0, ge=0, description="Number of items to skip"),
    ) -> None:
        self.limit = limit
        self.offset = offset


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list response.

    All list endpoints return this shape::

        {
            "data": [...],
            "total": 42,
            "limit": 20,
            "offset": 0
        }
    """

    data: list[T]
    total: int
    limit: int
    offset: int


async def paginate(
    db: AsyncSession,
    data_query: Select[Any],
    count_query: Select[Any],
    *,
    offset: int,
    limit: int,
    row_mapper: Callable[..., Any],
    scalars: bool = True,
    unique: bool = False,
) -> dict[str, Any]:
    """Execute a paginated query pair and return the standard envelope.

    Args:
        db: async database session.
        data_query: SELECT for data rows (without offset/limit — they are applied here).
        count_query: SELECT that returns a scalar count.
        offset / limit: pagination window.
        row_mapper: callable applied to each row to produce the output item.
        scalars: if True, call ``.scalars().all()`` on the data result;
                 if False, call ``.all()`` (for multi-column selects).
        unique: if True, call ``.unique()`` before ``.scalars()``
                (needed when eager-loading collections).
    """
    total: int = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(data_query.offset(offset).limit(limit))
    if scalars:
        if unique:
            rows: Sequence[Any] = result.unique().scalars().all()
        else:
            rows = result.scalars().all()
    else:
        rows = result.all()

    return {
        "data": [row_mapper(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
