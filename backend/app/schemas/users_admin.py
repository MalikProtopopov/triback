"""Pydantic schemas for admin user management (admin/manager/accountant)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

STAFF_ROLES = Literal["admin", "manager", "accountant"]

_ROLE_DISPLAY: dict[str, str] = {
    "admin": "Администратор",
    "manager": "Менеджер",
    "accountant": "Бухгалтер",
}


class AdminUserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: STAFF_ROLES

    model_config = {"json_schema_extra": {
        "example": {
            "email": "manager@example.com",
            "password": "SecurePass123!",
            "role": "manager",
        }
    }}


class AdminUserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    role: STAFF_ROLES | None = None
    is_active: bool | None = None


class AdminUserListItem(BaseModel):
    id: UUID
    email: str
    role: str
    role_display: str
    is_active: bool
    created_at: datetime


class AdminUserDetailResponse(BaseModel):
    id: UUID
    email: str
    role: str
    role_display: str
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"json_schema_extra": {
        "example": {
            "id": "01930b4a-0000-7000-8000-000000000001",
            "email": "admin@trichologia.ru",
            "role": "admin",
            "role_display": "Администратор",
            "is_active": True,
            "is_verified": True,
            "last_login_at": "2026-03-10T12:00:00Z",
            "created_at": "2026-01-15T09:30:00Z",
        }
    }}


class AdminUserCreatedResponse(BaseModel):
    id: UUID
    email: str
    role: str
    role_display: str
