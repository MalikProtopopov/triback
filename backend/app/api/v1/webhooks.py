"""Webhook endpoints — YooKassa payment notifications."""

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import ForbiddenError
from app.core.redis import get_redis
from app.schemas.payments import WebhookPayload
from app.services.subscription_service import SubscriptionService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks")

_DEDUP_TTL = 86400


@router.post(
    "/yookassa",
    summary="YooKassa webhook",
    responses={
        200: {"description": "Webhook обработан успешно"},
        403: {"description": "IP-адрес не в белом списке"},
        500: {"description": "Ошибка обработки (webhook будет повторён)"},
    },
)
async def yookassa_webhook(
    request: Request,
    body: WebhookPayload,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> JSONResponse:
    """Принимает уведомления от YooKassa о статусе платежей.
    Идемпотентность обеспечивается через Redis (dedup key с TTL 24ч).
    Не вызывать напрямую — только для YooKassa.
    """
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not client_ip and request.client:
        client_ip = request.client.host

    payload = body.model_dump()
    event_type = payload.get("event", "")
    external_id = payload.get("object", {}).get("id", "")

    dedup_key = f"webhook:dedup:{event_type}:{external_id}"
    if external_id:
        already = await redis.set(dedup_key, "1", ex=_DEDUP_TTL, nx=True)
        if not already:
            return JSONResponse(content={"status": "ok"})

    svc = SubscriptionService(db, redis)
    try:
        await svc.handle_webhook(payload, client_ip)
    except ForbiddenError:
        logger.warning("webhook_ip_rejected", ip=client_ip)
        return JSONResponse(status_code=403, content={"status": "forbidden"})
    except Exception:
        logger.exception("webhook_processing_error")
        if external_id:
            await redis.delete(dedup_key)
        return JSONResponse(status_code=500, content={"status": "error"})

    return JSONResponse(content={"status": "ok"})
