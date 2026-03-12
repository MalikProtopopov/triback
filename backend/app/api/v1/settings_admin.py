"""Admin endpoints for site settings, cities, subscription plans."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_role
from app.schemas.settings_admin import (
    CityAdminResponse,
    CityCreateRequest,
    CityUpdateRequest,
    PlanAdminResponse,
    PlanCreateRequest,
    PlanUpdateRequest,
    SettingsResponse,
    SettingsUpdateRequest,
)
from app.services.settings_service import SettingsAdminService

router = APIRouter(prefix="/admin")

ADMIN_ONLY = require_role("admin")
ADMIN_MANAGER = require_role("admin", "manager")


# ══ Site Settings ═════════════════════════════════════════════════

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> SettingsResponse:
    svc = SettingsAdminService(db)
    data = await svc.get_settings()
    return SettingsResponse(data=data)


@router.patch("/settings", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> SettingsResponse:
    admin_id = UUID(payload["sub"])
    svc = SettingsAdminService(db)
    data = await svc.update_settings(admin_id, body.data)
    return SettingsResponse(data=data)


# ══ Cities ════════════════════════════════════════════════════════

@router.get("/cities")
async def list_cities(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = SettingsAdminService(db)
    items = await svc.list_cities()
    return {"data": items}


@router.post("/cities", response_model=CityAdminResponse, status_code=201)
async def create_city(
    body: CityCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> CityAdminResponse:
    svc = SettingsAdminService(db)
    return await svc.create_city(body.model_dump())


@router.patch("/cities/{city_id}", response_model=CityAdminResponse)
async def update_city(
    city_id: UUID,
    body: CityUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> CityAdminResponse:
    svc = SettingsAdminService(db)
    return await svc.update_city(city_id, body.model_dump(exclude_none=True))


@router.delete("/cities/{city_id}", status_code=204)
async def delete_city(
    city_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = SettingsAdminService(db)
    await svc.delete_city(city_id)
    return Response(status_code=204)


# ══ Subscription Plans ════════════════════════════════════════════

@router.get("/plans")
async def list_plans(
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = SettingsAdminService(db)
    items = await svc.list_plans()
    return {"data": items}


@router.post("/plans", response_model=PlanAdminResponse, status_code=201)
async def create_plan(
    body: PlanCreateRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> PlanAdminResponse:
    svc = SettingsAdminService(db)
    return await svc.create_plan(body.model_dump())


@router.patch("/plans/{plan_id}", response_model=PlanAdminResponse)
async def update_plan(
    plan_id: UUID,
    body: PlanUpdateRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> PlanAdminResponse:
    svc = SettingsAdminService(db)
    return await svc.update_plan(plan_id, body.model_dump(exclude_none=True))


@router.delete("/plans/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = SettingsAdminService(db)
    await svc.delete_plan(plan_id)
    return Response(status_code=204)
