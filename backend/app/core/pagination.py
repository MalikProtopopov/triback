"""Pagination types used across all list endpoints."""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

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
    """Standard paginated list response: { data, total, limit, offset }."""

    data: list[T]
    total: int
    limit: int
    offset: int
