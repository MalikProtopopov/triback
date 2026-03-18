"""Pydantic schemas for admin settings, cities, and subscription plans."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Site Settings ─────────────────────────────────────────────────

class SettingsResponse(BaseModel):
    data: dict[str, Any]


class PublicSettingsResponse(BaseModel):
    """Публичные настройки (контакты, бот) — без авторизации."""

    data: dict[str, Any]


class SettingsUpdateRequest(BaseModel):
    data: dict[str, Any]


# ── Cities ────────────────────────────────────────────────────────

class CityCreateRequest(BaseModel):
    name: str = Field(max_length=255)
    slug: str | None = Field(None, max_length=255)
    sort_order: int = 0


class CityUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    slug: str | None = Field(None, max_length=255)
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
    duration_months: int = Field(ge=0, default=12)
    is_active: bool = True
    sort_order: int = 0
    plan_type: str = Field(default="subscription", pattern=r"^(entry_fee|subscription)$")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "code": "annual",
            "name": "Годовой членский взнос",
            "description": "Ежегодный взнос для членства в ассоциации",
            "price": 15000.0,
            "duration_months": 12,
            "is_active": True,
            "sort_order": 0,
            "plan_type": "subscription",
        }
    })


class PlanUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    price: float | None = Field(None, gt=0)
    duration_months: int | None = Field(None, ge=0)
    is_active: bool | None = None
    sort_order: int | None = None
    plan_type: str | None = Field(None, pattern=r"^(entry_fee|subscription)$")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Годовой членский взнос (обновлённый)",
            "price": 18000.0,
            "is_active": True,
        }
    })


class PlanAdminResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    price: float
    duration_months: int
    is_active: bool
    sort_order: int
    plan_type: str


class CityAdminListResponse(BaseModel):
    data: list[CityAdminResponse]


class PlanAdminListResponse(BaseModel):
    data: list[PlanAdminResponse]
