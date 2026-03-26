"""Admin endpoints for doctor management and moderation."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.pagination import PaginatedResponse
from app.core.redis import get_redis
from app.core.security import require_role
from app.schemas.auth import MessageResponse
from app.schemas.event_registration import UserEventRegistrationsPaginatedResponse
from app.schemas.doctor_admin import (
    AdminCreateDoctorRequest,
    AdminCreateDoctorResponse,
    ApproveDraftRequest,
    DoctorBoardRoleUpdateRequest,
    DoctorDetailResponse,
    DoctorPaymentOverridesRequest,
    DoctorListItemResponse,
    ImportStartResponse,
    ImportStatusResponse,
    ModerateRequest,
    ModerateResponse,
    PortalUserDetailResponse,
    PortalUserListItem,
    SendEmailRequest,
    SendReminderRequest,
    ToggleActiveRequest,
    ToggleActiveResponse,
)
from app.services.doctor_service import DoctorAdminService

router = APIRouter(prefix="/admin")

ADMIN_MANAGER = require_role("admin", "manager")
ADMIN_ONLY = require_role("admin")
ADMIN_ACCOUNTANT = require_role("admin", "accountant")


@router.get(
    "/doctors",
    response_model=PaginatedResponse[DoctorListItemResponse],
    summary="Список врачей",
    responses=error_responses(401, 403),
)
async def list_doctors(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="active | pending_review | rejected | ..."),
    subscription_status: str | None = Query(None, description="active | expired | none"),
    board_role: list[str] | None = Query(None, description="pravlenie, president"),
    city_id: UUID | None = Query(None),
    has_data_changed: bool | None = Query(None, description="Только с изменёнными данными"),
    search: str | None = Query(None, min_length=2),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> dict[str, Any]:
    """Пагинированный список врачей с фильтрацией и сортировкой.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    svc = DoctorAdminService(db)
    return await svc.list_doctors(
        limit=limit,
        offset=offset,
        status=status,
        subscription_status=subscription_status,
        board_role=board_role,
        city_id=city_id,
        has_data_changed=has_data_changed,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/doctors",
    response_model=AdminCreateDoctorResponse,
    status_code=201,
    summary="Создать врача вручную",
    responses=error_responses(401, 403, 409, 422),
)
async def create_doctor(
    body: AdminCreateDoctorRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> AdminCreateDoctorResponse:
    """Создаёт пользователя с ролью doctor и заполненным профилем.

    - **401** — не авторизован
    - **403** — роль не admin
    - **409** — пользователь с таким email уже существует
    """
    svc = DoctorAdminService(db)
    return await svc.create_doctor(body.model_dump())


@router.patch(
    "/doctors/{profile_id}",
    response_model=DoctorDetailResponse,
    summary="Обновить роль в правлении",
    responses=error_responses(401, 403, 404),
)
async def update_doctor_board_role(
    profile_id: UUID,
    body: DoctorBoardRoleUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> DoctorDetailResponse:
    """Обновляет роль врача в правлении (pravlenie | president | null).

    - **404** — профиль не найден
    """
    svc = DoctorAdminService(db)
    return await svc.update_board_role(profile_id, body.board_role)


@router.patch(
    "/doctors/{profile_id}/payment-overrides",
    response_model=DoctorDetailResponse,
    summary="Оверрайды оплаты (вступительный взнос)",
    responses=error_responses(401, 403, 404),
)
async def update_doctor_payment_overrides(
    profile_id: UUID,
    body: DoctorPaymentOverridesRequest,
    payload: dict[str, Any] = ADMIN_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
) -> DoctorDetailResponse:
    """Устанавливает `entry_fee_exempt` для миграции и ручных случаев."""
    svc = DoctorAdminService(db)
    return await svc.update_payment_overrides(profile_id, body)


@router.get(
    "/doctors/{profile_id}",
    response_model=DoctorDetailResponse,
    summary="Детали врача",
    responses=error_responses(401, 403, 404),
)
async def get_doctor(
    profile_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> DoctorDetailResponse:
    """Полная карточка врача с личными данными, документами, подпиской.

    - **404** — профиль не найден
    """
    svc = DoctorAdminService(db)
    return await svc.get_doctor(profile_id)


@router.post(
    "/doctors/{profile_id}/moderate",
    response_model=ModerateResponse,
    summary="Модерация врача",
    responses=error_responses(401, 403, 404, 422),
)
async def moderate_doctor(
    profile_id: UUID,
    body: ModerateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ModerateResponse:
    """Одобряет или отклоняет анкету врача.

    - **404** — профиль не найден
    """
    admin_id = UUID(payload["sub"])
    svc = DoctorAdminService(db)
    new_status = await svc.moderate(profile_id, admin_id, body.action, body.comment)
    msg = "Врач одобрен" if body.action == "approve" else "Врач отклонён"
    return ModerateResponse(moderation_status=new_status, message=msg)


@router.post(
    "/doctors/{profile_id}/approve-draft",
    response_model=MessageResponse,
    summary="Одобрить черновик изменений",
    responses=error_responses(401, 403, 404, 422),
)
async def approve_draft(
    profile_id: UUID,
    body: ApproveDraftRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Одобряет или отклоняет черновые изменения публичного профиля.

    - **404** — профиль или черновик не найден
    """
    admin_id = UUID(payload["sub"])
    svc = DoctorAdminService(db)
    msg = await svc.approve_draft(
        profile_id, admin_id, body.action, body.rejection_reason
    )
    return MessageResponse(message=msg)


@router.post(
    "/doctors/{profile_id}/toggle-active",
    response_model=ToggleActiveResponse,
    summary="Активировать/деактивировать профиль",
    responses=error_responses(401, 403, 404),
)
async def toggle_active(
    profile_id: UUID,
    body: ToggleActiveRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ToggleActiveResponse:
    """Включает/выключает публичную видимость профиля в каталоге.

    - **404** — профиль не найден
    """
    admin_id = UUID(payload["sub"])
    svc = DoctorAdminService(db)
    is_public = await svc.toggle_active(profile_id, admin_id, body.is_public)
    msg = "Профиль активирован" if is_public else "Профиль деактивирован"
    return ToggleActiveResponse(is_public=is_public, message=msg)


@router.post(
    "/doctors/{profile_id}/send-reminder",
    response_model=MessageResponse,
    summary="Отправить напоминание",
    responses=error_responses(401, 403, 404),
)
async def send_reminder(
    profile_id: UUID,
    body: SendReminderRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Отправляет напоминание врачу (email + Telegram при наличии привязки).

    - **404** — профиль не найден
    """
    svc = DoctorAdminService(db)
    telegram_sent = await svc.send_reminder(profile_id, body.message)
    if telegram_sent:
        msg = "Напоминание отправлено в Telegram"
    else:
        msg = "Telegram не привязан, сообщение в Telegram не дойдёт. Напоминание отправлено на email."
    return MessageResponse(message=msg)


@router.post(
    "/doctors/{profile_id}/send-email",
    response_model=MessageResponse,
    summary="Отправить email",
    responses=error_responses(401, 403, 404),
)
async def send_email(
    profile_id: UUID,
    body: SendEmailRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Отправляет email врачу.

    - **404** — профиль не найден
    """
    svc = DoctorAdminService(db)
    await svc.send_email(profile_id, body.subject, body.body)
    return MessageResponse(message="Письмо отправлено")


@router.post(
    "/doctors/import",
    response_model=ImportStartResponse,
    status_code=202,
    summary="Импорт врачей из Excel",
    responses=error_responses(401, 403, 422),
)
async def import_doctors(
    file: UploadFile,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> ImportStartResponse:
    """Запускает фоновый импорт врачей из Excel-файла.
    Статус импорта можно отслеживать через `GET /admin/doctors/import/{task_id}`.

    - **401** — не авторизован
    - **403** — роль не admin
    """
    contents = await file.read()
    svc = DoctorAdminService(db)
    task_id = await svc.start_import(contents, redis)
    return ImportStartResponse(task_id=task_id, message="Импорт запущен")


@router.get(
    "/doctors/import/{task_id}",
    response_model=ImportStatusResponse,
    summary="Статус импорта",
    responses=error_responses(401, 403, 404),
)
async def get_import_status(
    task_id: str,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> ImportStatusResponse:
    """Проверяет статус фонового импорта.

    - **404** — задача не найдена
    """
    svc = DoctorAdminService(db)
    return await svc.get_import_status(task_id, redis)


@router.get(
    "/portal-users/{user_id}",
    response_model=PortalUserDetailResponse,
    summary="Детали пользователя портала",
    responses=error_responses(401, 403, 404),
)
async def get_portal_user(
    user_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> PortalUserDetailResponse:
    """Полная информация о пользователе портала (аккаунт + профиль).

    - **404** — пользователь не найден
    """
    svc = DoctorAdminService(db)
    return await svc.get_portal_user(user_id)


@router.get(
    "/portal-users/{user_id}/event-registrations",
    response_model=UserEventRegistrationsPaginatedResponse,
    summary="Регистрации пользователя на мероприятия (с платежом и тарифом)",
    responses=error_responses(401, 403, 404),
)
async def list_portal_user_event_registrations(
    user_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(
        None, description="pending | confirmed | cancelled",
    ),
    event_id: UUID | None = Query(None, description="Фильтр по мероприятию"),
) -> dict[str, Any]:
    """Список регистраций выбранного пользователя портала — для вкладки «Мероприятия» у врача.

    Тело ответа совпадает с ``GET /api/v1/profile/event-registrations``.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    from app.services.event_registration.user_registrations_list import (
        list_registrations_for_user,
    )

    svc = DoctorAdminService(db)
    await svc.get_portal_user(user_id)

    return await list_registrations_for_user(
        db,
        user_id,
        limit=limit,
        offset=offset,
        status=status,
        event_id=event_id,
    )


@router.get(
    "/portal-users",
    response_model=PaginatedResponse[PortalUserListItem],
    summary="Список пользователей портала",
    responses=error_responses(401, 403),
)
async def list_portal_users(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, min_length=2),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> dict[str, Any]:
    """Пагинированный список всех зарегистрированных пользователей.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    svc = DoctorAdminService(db)
    return await svc.list_portal_users(
        limit=limit,
        offset=offset,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
