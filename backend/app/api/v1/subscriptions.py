"""Subscription endpoints — pay, status, user payments, receipts."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.redis import get_redis
from app.core.security import require_role
from app.schemas.subscriptions import (
    PayRequest,
    PayResponse,
    ReceiptResponse,
    SubscriptionStatusResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions")

DOCTOR = require_role("doctor")


@router.post("/pay", response_model=PayResponse, status_code=201)
async def pay_subscription(
    body: PayRequest,
    payload: dict[str, Any] = DOCTOR,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> PayResponse:
    user_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.pay(user_id, body.plan_id, body.idempotency_key)


@router.get("/status", response_model=SubscriptionStatusResponse)
async def subscription_status(
    payload: dict[str, Any] = DOCTOR,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> SubscriptionStatusResponse:
    user_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.get_status(user_id)


@router.get("/payments", response_model=dict)
async def list_my_payments(
    payload: dict[str, Any] = DOCTOR,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    user_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.list_user_payments(user_id, limit=limit, offset=offset)


@router.get("/payments/{payment_id}/receipt", response_model=ReceiptResponse)
async def get_payment_receipt(
    payment_id: UUID,
    payload: dict[str, Any] = DOCTOR,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> dict:
    user_id = UUID(payload["sub"])
    svc = SubscriptionService(db, redis)
    return await svc.get_user_receipt(user_id, payment_id)
