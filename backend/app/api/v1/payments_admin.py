"""Admin payment endpoints — list and manual creation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.redis import get_redis
from app.core.security import require_role
from app.schemas.payments import (
    ManualPaymentRequest,
    ManualPaymentResponse,
    PaymentListResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/admin")

ADMIN_MANAGER_ACCOUNTANT = require_role("admin", "manager", "accountant")
ADMIN_ACCOUNTANT = require_role("admin", "accountant")


@router.get(
    "/payments",
    response_model=PaymentListResponse,
    summary="Список платежей",
    responses=error_responses(401, 403),
)
async def list_payments(
    payload: dict[str, Any] = ADMIN_MANAGER_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="pending | succeeded | canceled"),
    product_type: str | None = Query(None, description="entry_fee | subscription | event"),
    user_id: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> PaymentListResponse:
    """Пагинированный список всех платежей с фильтрацией и сводкой (`summary`).

    - **401** — не авторизован
    - **403** — роль не admin/manager/accountant
    """
    svc = SubscriptionService(db, redis)
    return await svc.list_payments(
        limit=limit,
        offset=offset,
        status=status,
        product_type=product_type,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/payments/manual",
    response_model=ManualPaymentResponse,
    status_code=201,
    summary="Ручной платёж",
    responses=error_responses(401, 403, 404, 422),
)
async def create_manual_payment(
    body: ManualPaymentRequest,
    payload: dict[str, Any] = ADMIN_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> ManualPaymentResponse:
    """Создаёт платёж вручную (наличные, перевод). Автоматически
    обновляет подписку/регистрацию.

    - **401** — не авторизован
    - **403** — роль не admin/accountant
    - **404** — пользователь, подписка или регистрация не найдены
    """
    admin_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.create_manual_payment(admin_id, body)
