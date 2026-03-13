"""Admin endpoints for staff user management (admin/manager/accountant)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.pagination import PaginatedResponse
from app.core.security import require_role
from app.schemas.users_admin import (
    AdminUserCreateRequest,
    AdminUserCreatedResponse,
    AdminUserDetailResponse,
    AdminUserListItem,
    AdminUserUpdateRequest,
)
from app.services.user_admin_service import UserAdminService

router = APIRouter(prefix="/admin")

ADMIN_ONLY = require_role("admin")


@router.get(
    "/users",
    response_model=PaginatedResponse[AdminUserListItem],
    summary="Список сотрудников",
    responses=error_responses(401, 403),
)
async def list_staff_users(
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    role: str | None = Query(None, description="Фильтр по роли: admin, manager, accountant"),
    search: str | None = Query(None, min_length=2, description="Поиск по email"),
) -> PaginatedResponse:
    """Пагинированный список пользователей с ролями admin/manager/accountant.

    - **401** -- не авторизован
    - **403** -- роль не admin
    """
    svc = UserAdminService(db)
    return await svc.list_staff_users(
        limit=limit, offset=offset, role=role, search=search,
    )


@router.post(
    "/users",
    response_model=AdminUserCreatedResponse,
    status_code=201,
    summary="Создать сотрудника",
    responses=error_responses(401, 403, 409, 422),
)
async def create_staff_user(
    body: AdminUserCreateRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> AdminUserCreatedResponse:
    """Создаёт пользователя с ролью admin, manager или accountant.

    - **401** -- не авторизован
    - **403** -- роль не admin
    - **409** -- пользователь с таким email уже существует
    """
    svc = UserAdminService(db)
    return await svc.create_staff_user(body.model_dump())


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    summary="Детали сотрудника",
    responses=error_responses(401, 403, 404),
)
async def get_staff_user(
    user_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> AdminUserDetailResponse:
    """Полная информация о сотруднике (admin/manager/accountant).

    - **404** -- пользователь не найден или не является сотрудником
    """
    svc = UserAdminService(db)
    return await svc.get_staff_user(user_id)


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    summary="Обновить сотрудника",
    responses=error_responses(401, 403, 404, 409, 422),
)
async def update_staff_user(
    user_id: UUID,
    body: AdminUserUpdateRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> AdminUserDetailResponse:
    """Обновляет email, роль или статус активности сотрудника.

    - **404** -- пользователь не найден
    - **409** -- email уже занят
    """
    svc = UserAdminService(db)
    return await svc.update_staff_user(user_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/users/{user_id}",
    status_code=204,
    summary="Удалить сотрудника",
    responses=error_responses(401, 403, 404),
)
async def delete_staff_user(
    user_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Мягкое удаление сотрудника. Нельзя удалить самого себя.

    - **403** -- попытка удалить себя
    - **404** -- пользователь не найден
    """
    admin_id = UUID(payload["sub"])
    svc = UserAdminService(db)
    await svc.delete_staff_user(user_id, admin_id)
    return Response(status_code=204)
