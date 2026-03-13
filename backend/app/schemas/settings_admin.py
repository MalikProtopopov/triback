"""Pydantic schemas for admin settings, cities, and subscription plans."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── Site Settings ─────────────────────────────────────────────────

class SettingsResponse(BaseModel):
    data: dict[str, Any]


class SettingsUpdateRequest(BaseModel):
    data: dict[str, Any]


# ── Cities ────────────────────────────────────────────────────────

class CityCreateRequest(BaseModel):
    name: str = Field(max_length=255)
    sort_order: int = 0


class CityUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    sort_order: int | None = None
    is_active: bool | None = None


class CityAdminResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    sort_order: int
    is_active: bool
    doctors_count: int = 0


# ── Subscription Plans ────────────────────────────────────────────

class PlanCreateRequest(BaseModel):
    code: str = Field(max_length=50)
    name: str = Field(max_length=255)
    description: str | None = None
    price: float = Field(gt=0)
    duration_months: int = Field(gt=0, default=12)
    is_active: bool = True
    sort_order: int = 0


class PlanUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    price: float | None = Field(None, gt=0)
    duration_months: int | None = Field(None, gt=0)
    is_active: bool | None = None
    sort_order: int | None = None


class PlanAdminResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    price: float
    duration_months: int
    is_active: bool
    sort_order: int


class CityAdminListResponse(BaseModel):
    data: list[CityAdminResponse]


class PlanAdminListResponse(BaseModel):
    data: list[PlanAdminResponse]
