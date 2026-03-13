"""Admin notifications router — send notification + list log."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.pagination import PaginatedResponse, PaginationParams
from app.core.security import require_role
from app.models.users import Notification
from app.schemas.notifications import (
    NotificationListItem,
    NotificationResponse,
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
) -> dict:
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

    return {"id": str(last_notif.id), "status": last_notif.status} if last_notif else {"id": "", "status": "failed"}


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
) -> PaginatedResponse:
    """Пагинированный журнал всех отправленных уведомлений.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    q = select(Notification)
    count_q = select(func.count(Notification.id))

    if user_id:
        q = q.where(Notification.user_id == user_id)
        count_q = count_q.where(Notification.user_id == user_id)
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

    data = [
        {
            "id": str(n.id),
            "user_id": n.user_id,
            "template_code": n.template_code,
            "channel": n.channel,
            "title": n.title,
            "status": n.status,
            "sent_at": n.sent_at.isoformat() if n.sent_at else None,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]

    return PaginatedResponse(data=data, total=total, limit=pagination.limit, offset=pagination.offset)
