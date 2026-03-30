"""Admin endpoints for site settings, cities, subscription plans."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.schemas.settings_admin import (
    CityAdminListResponse,
    CityAdminResponse,
    CityCreateRequest,
    CityUpdateRequest,
    PlanAdminListResponse,
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
# Справочник городов для селектов в админке (в т.ч. бухгалтер)
ADMIN_LIST_CITIES = require_role("admin", "manager", "accountant")


# ══ Site Settings ═════════════════════════════════════════════════

@router.get(
    "/settings",
    response_model=SettingsResponse,
    summary="Получить настройки",
    responses=error_responses(401, 403),
)
async def get_settings(
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> SettingsResponse:
    """Текущие настройки сайта (JSON-объект в `data`). Доступно только admin.

    - **401** — не авторизован
    - **403** — роль не admin
    """
    svc = SettingsAdminService(db)
    data = await svc.get_settings()
    return SettingsResponse(data=data)


@router.patch(
    "/settings",
    response_model=SettingsResponse,
    summary="Обновить настройки",
    responses=error_responses(401, 403, 422),
)
async def update_settings(
    body: SettingsUpdateRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> SettingsResponse:
    """Обновляет настройки сайта (partial merge). Доступно только admin.

    - **401** — не авторизован
    - **403** — роль не admin
    """
    admin_id = UUID(payload["sub"])
    svc = SettingsAdminService(db)
    data = await svc.update_settings(admin_id, body.data)
    return SettingsResponse(data=data)


# ══ Cities ════════════════════════════════════════════════════════

@router.get(
    "/cities",
    response_model=CityAdminListResponse,
    summary="Список городов",
    responses=error_responses(401, 403),
)
async def list_cities(
    payload: dict[str, Any] = ADMIN_LIST_CITIES,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Все города с подсчётом врачей.

    - **401** — не авторизован
    - **403** — роль не admin/manager/accountant
    """
    svc = SettingsAdminService(db)
    items = await svc.list_cities()
    return {"data": items}


@router.post(
    "/cities",
    response_model=CityAdminResponse,
    status_code=201,
    summary="Создать город",
    responses=error_responses(401, 403, 409, 422),
)
async def create_city(
    body: CityCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> CityAdminResponse:
    """Создаёт город. Slug генерируется автоматически.

    - **409** — город с таким именем/slug уже существует
    """
    svc = SettingsAdminService(db)
    return await svc.create_city(body.model_dump())


@router.patch(
    "/cities/{city_id}",
    response_model=CityAdminResponse,
    summary="Обновить город",
    responses=error_responses(401, 403, 404, 422),
)
async def update_city(
    city_id: UUID,
    body: CityUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> CityAdminResponse:
    """Обновляет параметры города.

    - **404** — город не найден
    """
    svc = SettingsAdminService(db)
    return await svc.update_city(city_id, body.model_dump(exclude_none=True))


@router.delete(
    "/cities/{city_id}",
    status_code=204,
    summary="Удалить город",
    responses=error_responses(401, 403, 404),
)
async def delete_city(
    city_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Удаляет город. Доступно только admin.

    - **404** — город не найден
    """
    svc = SettingsAdminService(db)
    await svc.delete_city(city_id)
    return Response(status_code=204)


# ══ Subscription Plans ════════════════════════════════════════════

@router.get(
    "/plans",
    response_model=PlanAdminListResponse,
    summary="Список тарифных планов",
    responses=error_responses(401, 403),
)
async def list_plans(
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Все тарифные планы подписки. Доступно только admin.

    - **401** — не авторизован
    - **403** — роль не admin
    """
    svc = SettingsAdminService(db)
    items = await svc.list_plans()
    return {"data": items}


@router.post(
    "/plans",
    response_model=PlanAdminResponse,
    status_code=201,
    summary="Создать план",
    responses=error_responses(401, 403, 409, 422),
)
async def create_plan(
    body: PlanCreateRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> PlanAdminResponse:
    """Создаёт тарифный план подписки.

    - **409** — план с таким code уже существует
    """
    svc = SettingsAdminService(db)
    return await svc.create_plan(body.model_dump())


@router.patch(
    "/plans/{plan_id}",
    response_model=PlanAdminResponse,
    summary="Обновить план",
    responses=error_responses(401, 403, 404, 422),
)
async def update_plan(
    plan_id: UUID,
    body: PlanUpdateRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> PlanAdminResponse:
    """Обновляет параметры тарифного плана.

    - **404** — план не найден
    """
    svc = SettingsAdminService(db)
    return await svc.update_plan(plan_id, body.model_dump(exclude_none=True))


@router.delete(
    "/plans/{plan_id}",
    status_code=204,
    summary="Удалить план",
    responses=error_responses(401, 403, 404),
)
async def delete_plan(
    plan_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Удаляет тарифный план. Доступно только admin.

    - **404** — план не найден
    """
    svc = SettingsAdminService(db)
    await svc.delete_plan(plan_id)
    return Response(status_code=204)
