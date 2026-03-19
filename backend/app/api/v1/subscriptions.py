"""Subscription endpoints — pay, status, user payments, receipts."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.redis import get_redis
from app.core.security import require_role
from app.schemas.subscriptions import (
    PayRequest,
    PayResponse,
    ReceiptResponse,
    SubscriptionStatusResponse,
    UserPaymentPaginatedResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions")

DOCTOR = require_role("doctor")


@router.post(
    "/pay",
    response_model=PayResponse,
    status_code=201,
    summary="Оплата членского взноса",
    responses=error_responses(401, 403, 404, 409, 422),
)
async def pay_subscription(
    body: PayRequest,
    payload: dict[str, Any] = DOCTOR,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> PayResponse:
    """Создаёт платёж через текущий платёжный провайдер (Moneta / YooKassa)
    и возвращает URL для оплаты.

    При первой оплате (или после длинного перерыва >60 дней) автоматически
    включается вступительный взнос + годовой в один платёж. Повторный вызов
    с тем же `idempotency_key` вернёт тот же результат.

    - **401** — не авторизован
    - **403** — роль не doctor
    - **404** — тарифный план не найден
    - **422** — нет диплома / вступительный взнос не настроен
    """
    user_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.pay(user_id, body.plan_id, body.idempotency_key)


@router.get(
    "/status",
    response_model=SubscriptionStatusResponse,
    summary="Статус подписки",
    responses=error_responses(401, 403),
)
async def subscription_status(
    payload: dict[str, Any] = DOCTOR,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> SubscriptionStatusResponse:
    """Текущий статус подписки: есть ли подписка, когда истекает,
    оплачен ли вступительный взнос, доступно ли продление.

    - **401** — не авторизован
    - **403** — роль не doctor
    """
    user_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.get_status(user_id)


@router.get(
    "/payments",
    response_model=UserPaymentPaginatedResponse,
    summary="История платежей",
    responses=error_responses(401, 403),
)
async def list_my_payments(
    payload: dict[str, Any] = DOCTOR,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """Пагинированный список платежей текущего пользователя.

    - **401** — не авторизован
    - **403** — роль не doctor
    """
    user_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.list_user_payments(user_id, limit=limit, offset=offset)


@router.post(
    "/payments/{payment_id}/check-status",
    summary="Проверка статуса платежа через Moneta API",
    responses=error_responses(401, 403, 404),
)
async def check_payment_status(
    payment_id: UUID,
    payload: dict[str, Any] = DOCTOR,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> dict:
    """Проверяет статус платежа напрямую через Moneta API.

    Используется как fallback когда Pay URL webhook не доставлен.
    Фронтенд вызывает этот endpoint после возврата пользователя
    со страницы оплаты Moneta.

    Если Moneta подтверждает оплату — платёж и подписка активируются.

    - **401** — не авторизован
    - **403** — платёж принадлежит другому пользователю
    - **404** — платёж не найден
    """
    user_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.check_payment_status(user_id, payment_id)


@router.get(
    "/payments/{payment_id}/receipt",
    response_model=ReceiptResponse,
    summary="Чек по платежу",
    responses=error_responses(401, 403, 404),
)
async def get_payment_receipt(
    payment_id: UUID,
    payload: dict[str, Any] = DOCTOR,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> dict:
    """Возвращает данные чека (фискализации) по платежу.

    - **401** — не авторизован
    - **403** — платёж принадлежит другому пользователю
    - **404** — платёж или чек не найден
    """
    user_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.get_user_receipt(user_id, payment_id)
