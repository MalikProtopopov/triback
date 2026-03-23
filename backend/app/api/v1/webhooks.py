"""Webhook endpoints — YooKassa & Moneta payment notifications."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.enums import PaymentStatus
from app.core.exceptions import ForbiddenError
from app.core.redis import get_redis
from app.models.subscriptions import Payment, Receipt
from app.schemas.payments import WebhookPayload
from app.services.payment_providers.moneta_client import MonetaPaymentProvider
from app.services.payment_webhook_service import PaymentWebhookService
from app.services.subscription_service import SubscriptionService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks")

_DEDUP_TTL = 86400


# ------------------------------------------------------------------
# YooKassa webhook (legacy)
# ------------------------------------------------------------------


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
    """YooKassa payment status notifications (kept for backward compat)."""
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


# ------------------------------------------------------------------
# Moneta — Pay URL (payment notification)
# ------------------------------------------------------------------

async def _collect_moneta_params(request: Request) -> dict[str, str]:
    """Merge GET query params and POST form-data into a single dict."""
    params: dict[str, str] = dict(request.query_params)
    if request.method == "POST":
        content_type = request.headers.get("content-type", "")
        if "form" in content_type:
            form = await request.form()
            params.update({k: str(v) for k, v in form.items()})
    return params


@router.api_route(
    "/moneta",
    methods=["GET", "POST"],
    summary="Moneta Pay URL webhook",
)
async def moneta_pay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> PlainTextResponse:
    """Moneta Pay URL — вызывается Moneta после успешной оплаты.

    Принимает GET или POST с параметрами `MNT_ID`, `MNT_TRANSACTION_ID`,
    `MNT_OPERATION_ID`, `MNT_AMOUNT`, `MNT_SIGNATURE` и др.
    Верифицирует подпись MD5, активирует подписку или регистрацию.
    Возвращает `SUCCESS` или `FAIL` (plain text).
    """
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not client_ip and request.client:
        client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    params = await _collect_moneta_params(request)

    # Log WARNING for empty or malformed requests (once per 24h to avoid spam)
    key_params = ("MNT_SIGNATURE", "MNT_OPERATION_ID", "MNT_TRANSACTION_ID")
    has_key_params = all(params.get(k) for k in key_params)
    if not params or not has_key_params:
        dedup_warn_key = "webhook:moneta:empty_warn"
        should_warn = await redis.set(dedup_warn_key, "1", ex=_DEDUP_TTL, nx=True)
        if should_warn:
            logger.warning(
                "moneta_pay_request_empty_or_malformed",
                method=request.method,
                client_ip=client_ip,
                params_keys=list(params.keys()) if params else [],
                missing=[] if not params else [k for k in key_params if not params.get(k)],
            )

    logger.info(
        "moneta_pay_request",
        method=request.method,
        client_ip=client_ip,
        user_agent=user_agent[:80] if user_agent else None,
        params=params,
    )
    mnt_operation_id = params.get("MNT_OPERATION_ID", "")
    mnt_command = params.get("MNT_COMMAND", "")

    dedup_key = f"webhook:dedup:moneta:{mnt_operation_id}"
    if mnt_operation_id:
        is_new = await redis.set(dedup_key, "1", ex=_DEDUP_TTL, nx=True)
        if not is_new:
            return PlainTextResponse("SUCCESS", media_type="text/plain; charset=utf-8")

    provider = MonetaPaymentProvider()
    try:
        webhook_data = await provider.verify_webhook(params)
    except ValueError as e:
        logger.warning("moneta_signature_invalid", reason=str(e), params=params)
        return PlainTextResponse("FAIL", media_type="text/plain; charset=utf-8")

    if mnt_command in ("CANCELLED_DEBIT", "CANCELLED_CREDIT"):
        try:
            payment_id = UUID(webhook_data.transaction_id)
            result = await db.execute(
                select(Payment).where(Payment.id == payment_id).with_for_update()
            )
            payment = result.scalar_one_or_none()
            if payment:
                svc = PaymentWebhookService(db)
                await svc._handle_payment_canceled(payment)
                logger.info(
                    "moneta_payment_cancelled",
                    payment_id=str(payment_id),
                    mnt_command=mnt_command,
                )
        except Exception:
            logger.exception("moneta_cancelled_webhook_error", mnt_command=mnt_command)
        return PlainTextResponse("SUCCESS", media_type="text/plain; charset=utf-8")

    try:
        payment_id = UUID(webhook_data.transaction_id)
        result = await db.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if not payment:
            logger.warning(
                "moneta_payment_not_found",
                transaction_id=webhook_data.transaction_id,
                mnt_operation_id=mnt_operation_id,
            )
            if mnt_operation_id:
                await redis.delete(dedup_key)
            return PlainTextResponse("FAIL", media_type="text/plain; charset=utf-8")

        payment.moneta_operation_id = webhook_data.external_id

        svc = PaymentWebhookService(db)
        await svc.handle_moneta_payment_succeeded(payment)
    except Exception:
        logger.exception("moneta_webhook_processing_error")
        if mnt_operation_id:
            await redis.delete(dedup_key)
        return PlainTextResponse("FAIL", media_type="text/plain; charset=utf-8")

    return PlainTextResponse("SUCCESS", media_type="text/plain; charset=utf-8")


# ------------------------------------------------------------------
# Moneta — Check URL (pre-payment validation)
# ------------------------------------------------------------------


@router.api_route(
    "/moneta/check",
    methods=["GET", "POST"],
    summary="Moneta Check URL",
)
async def moneta_check_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Moneta Check URL — предварительная проверка заказа перед оплатой.

    Moneta отправляет запрос для валидации: существует ли платёж, корректна ли
    сумма. Возвращает XML-ответ с кодом `200` (OK), `402` (не найден) или `500`
    (ошибка подписи).
    """
    params = await _collect_moneta_params(request)
    mnt_id = params.get("MNT_ID", "")
    mnt_transaction_id = params.get("MNT_TRANSACTION_ID", "")

    logger.info("moneta_check_request", params=params)

    provider = MonetaPaymentProvider()

    try:
        await provider.verify_webhook(params)
    except ValueError:
        logger.warning("moneta_check_signature_invalid", params=params)
        xml = provider.build_check_response(mnt_id, mnt_transaction_id, "500")
        logger.info("moneta_check_response_xml", xml=xml)
        return Response(content=xml, media_type="application/xml; charset=utf-8")

    mnt_operation_id = params.get("MNT_OPERATION_ID", "")

    try:
        payment_id = UUID(mnt_transaction_id)
        result = await db.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
    except (ValueError, Exception):
        payment = None

    if payment and mnt_operation_id and not payment.moneta_operation_id:
        payment.moneta_operation_id = mnt_operation_id
        if not payment.external_payment_id:
            payment.external_payment_id = mnt_operation_id
        await db.commit()

    if payment and payment.status == PaymentStatus.PENDING:
        amount_str = f"{float(payment.amount):.2f}"
        xml = provider.build_check_response(
            mnt_id, mnt_transaction_id, "402", amount=amount_str
        )
    elif payment and payment.status == PaymentStatus.SUCCEEDED:
        xml = provider.build_check_response(mnt_id, mnt_transaction_id, "200")
    else:
        xml = provider.build_check_response(mnt_id, mnt_transaction_id, "500")

    logger.info(
        "moneta_check_response",
        payment_found=payment is not None,
        payment_status=payment.status if payment else None,
        xml=xml,
    )

    return Response(content=xml, media_type="application/xml; charset=utf-8")


# ------------------------------------------------------------------
# Moneta — receipt webhook (54-ФЗ fiscal receipt)
# ------------------------------------------------------------------


@router.post(
    "/moneta/receipt",
    summary="Moneta receipt webhook",
)
async def moneta_receipt_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Moneta receipt webhook — фискальный чек (54-ФЗ).

    Вызывается после формирования чека. Содержит JSON с `operation`
    (ID операции Moneta) и `receipt` (URL чека). Сохраняет `Receipt` в БД
    и отправляет email пользователю со ссылкой на скачивание чека.
    """
    # TODO: add IP whitelist or shared-secret auth when Moneta provides IP ranges
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not client_ip and request.client:
        client_ip = request.client.host

    body = await request.json()
    logger.info("moneta_receipt_webhook", body=body, client_ip=client_ip)

    operation = body.get("operation")
    receipt_url = body.get("receipt")

    if not operation or operation is False:
        return JSONResponse(content={"status": "ok"})

    operation_str = str(operation)
    result = await db.execute(
        select(Payment).where(Payment.moneta_operation_id == operation_str)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        logger.warning("moneta_receipt_payment_not_found", operation=operation_str)
        return JSONResponse(content={"status": "ok"})

    receipt_type = "refund" if body.get("parentid") else "payment"

    existing = await db.execute(
        select(Receipt).where(
            Receipt.payment_id == payment.id,
            Receipt.receipt_type == receipt_type,
        )
    )
    receipt = existing.scalar_one_or_none()
    if receipt:
        if receipt_url and receipt_url is not False:
            receipt.receipt_url = str(receipt_url)
            receipt.status = "succeeded"  # type: ignore[assignment]
    else:
        receipt = Receipt(
            payment_id=payment.id,
            receipt_type=receipt_type,
            receipt_url=str(receipt_url) if receipt_url and receipt_url is not False else None,
            amount=payment.amount,
            status="succeeded",
        )
        db.add(receipt)

    await db.commit()

    final_receipt_url = str(receipt_url) if receipt_url and receipt_url is not False else None
    if final_receipt_url:
        from app.models.users import User

        email_result = await db.execute(
            select(User.email).where(User.id == payment.user_id)
        )
        user_email = email_result.scalar_one_or_none()
        if user_email:
            from app.tasks.email_tasks import send_receipt_available_notification
            from app.tasks.telegram_tasks import notify_user_receipt_available

            await send_receipt_available_notification.kiq(
                user_email, final_receipt_url, float(payment.amount)
            )
            await notify_user_receipt_available.kiq(
                str(payment.user_id), float(payment.amount)
            )

    return JSONResponse(content={"status": "ok"})
