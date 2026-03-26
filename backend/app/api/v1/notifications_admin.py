"""Admin notifications router — send notification + list log."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import AppValidationError
from app.core.openapi import error_responses
from app.core.pagination import PaginatedResponse, PaginationParams
from app.core.security import require_role
from app.models.profiles import DoctorProfile
from app.models.users import Notification, User
from app.schemas.notifications import (
    NotificationListItem,
    NotificationResponse,
    NotificationUserNested,
    SendNotificationRequest,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin/notifications")


@router.post(
    "/send",
    response_model=NotificationResponse,
    status_code=201,
    summary="Отправить уведомление",
    responses=error_responses(401, 403, 404, 422),
)
async def send_notification(
    body: SendNotificationRequest,
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> NotificationResponse:
    """Отправляет уведомление пользователю через выбранные каналы (email, push, telegram).

    - **401** — не авторизован
    - **403** — роль не admin/manager
    - **404** — пользователь не найден
    """
    svc = NotificationService(db)

    last_notif = None
    for channel in body.channels:
        last_notif = await svc.create_notification(
            user_id=body.user_id,
            template_code=body.type,
            channel=channel,
            title=body.title,
            body=body.body,
        )

    if not last_notif:
        raise AppValidationError("Не удалось отправить уведомление: каналы не указаны или недоступны")

    return NotificationResponse(id=last_notif.id, status=last_notif.status)


@router.get(
    "",
    response_model=PaginatedResponse[NotificationListItem],
    summary="Журнал уведомлений",
    responses=error_responses(401, 403),
)
async def list_notifications(
    pagination: PaginationParams = Depends(),
    user_id: str | None = Query(None, description="Фильтр по UUID пользователя"),
    status: str | None = Query(None, description="sent | failed | pending"),
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[NotificationListItem]:
    """Пагинированный журнал всех отправленных уведомлений.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    q = select(Notification)
    count_q = select(func.count(Notification.id))

    if user_id:
        uid = UUID(user_id)
        q = q.where(Notification.user_id == uid)
        count_q = count_q.where(Notification.user_id == uid)
    if status:
        q = q.where(Notification.status == status)
        count_q = count_q.where(Notification.status == status)

    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(
        q.order_by(Notification.created_at.desc())
        .limit(pagination.limit)
        .offset(pagination.offset)
    )
    notifs = result.scalars().all()

    uid_list = list({n.user_id for n in notifs})
    email_map: dict[UUID, str] = {}
    name_map: dict[UUID, str] = {}
    if uid_list:
        u_rows = (
            await db.execute(select(User.id, User.email).where(User.id.in_(uid_list)))
        ).all()
        for uid, email in u_rows:
            email_map[uid] = email
        dp_rows = (
            await db.execute(
                select(
                    DoctorProfile.user_id,
                    DoctorProfile.first_name,
                    DoctorProfile.last_name,
                ).where(DoctorProfile.user_id.in_(uid_list))
            )
        ).all()
        for uid, fn, ln in dp_rows:
            full = f"{ln or ''} {fn or ''}".strip()
            name_map[uid] = full or None

    data = [
        NotificationListItem(
            id=n.id,
            user_id=n.user_id,
            user=NotificationUserNested(
                id=n.user_id,
                email=email_map.get(n.user_id, ""),
                full_name=name_map.get(n.user_id),
            ),
            template_code=n.template_code,
            channel=n.channel,
            title=n.title,
            status=n.status,
            sent_at=n.sent_at,
            created_at=n.created_at,
        )
        for n in notifs
    ]

    return PaginatedResponse(data=data, total=total, limit=pagination.limit, offset=pagination.offset)
