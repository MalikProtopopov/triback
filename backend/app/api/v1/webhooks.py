"""Webhook endpoints — YooKassa & Moneta payment notifications."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.enums import PaymentStatus, ReceiptStatus
from app.core.exceptions import ForbiddenError
from app.core.logging_privacy import (
    moneta_params_for_log,
    moneta_receipt_body_summary,
)
from app.core.rate_limit import limiter
from app.core.redis import get_redis
from app.models.subscriptions import Payment, Receipt
from app.models.users import User
from app.schemas.payments import WebhookPayload
from app.services.kassa_payanyway_fiscal import (
    FiscalRebuildError,
    build_client_json,
    build_inventory_json,
    build_kassa_error_xml,
    build_kassa_fiscal_xml,
    fiscal_seller_from_settings,
    get_payment_by_mnt_transaction_id,
    payment_items_for_fiscal,
)
from app.services.payment_providers.moneta_client import MonetaPaymentProvider
from app.services.payment_utils import is_moneta_receipt_webhook_authorized
from app.services.payment_webhook_routing import (
    YOOKASSA_WEBHOOK_DEDUP_KEY_PREFIX,
    YOOKASSA_WEBHOOK_DEDUP_TTL_SECONDS,
    MonetaCheckResultCode,
)
from app.services.payment_webhook_service import PaymentWebhookService
from app.services.subscription_service import SubscriptionService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks")


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
@limiter.limit("120/minute")
async def yookassa_webhook(
    request: Request,
    body: WebhookPayload,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    """YooKassa payment status notifications (kept for backward compat).

    Security trust model: IP whitelist only (``YOOKASSA_IP_WHITELIST`` env var).
    YooKassa does not issue a per-merchant HMAC secret for webhooks; their official
    recommendation is to restrict incoming connections to their published IP ranges
    (https://yookassa.ru/developers/using-api/webhooks#security).

    Threat vector: if the network-layer IP filtering is bypassed (e.g. misconfigured
    proxy, SSRF), an attacker could inject arbitrary payment events.  Mitigations:
    - Keep ``YOOKASSA_IP_WHITELIST`` up-to-date with the official YooKassa IP list.
    - Validate every ``external_id`` against the YooKassa API before accepting the event
      (optional double-check for critical flows — call ``GET /payments/{id}`` to confirm
      ``status`` server-side before marking payment as succeeded).
    """
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not client_ip and request.client:
        client_ip = request.client.host

    payload = body.model_dump()
    event_type = payload.get("event", "")
    external_id = payload.get("object", {}).get("id", "")

    dedup_key = f"{YOOKASSA_WEBHOOK_DEDUP_KEY_PREFIX}{event_type}:{external_id}"
    if external_id:
        already = await redis.set(
            dedup_key, "1", ex=YOOKASSA_WEBHOOK_DEDUP_TTL_SECONDS, nx=True
        )
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


async def _load_user_email(db: AsyncSession, user_id: UUID) -> str | None:
    row = await db.execute(select(User.email).where(User.id == user_id))
    return row.scalar_one_or_none()


async def _moneta_pay_process(
    db: AsyncSession,
    redis: Redis,
    params: dict[str, str],
) -> Literal["duplicate", "ok", "fail"]:
    """Shared Moneta Pay URL: dedup, verify, cancel or mark succeeded."""
    mnt_operation_id = params.get("MNT_OPERATION_ID", "")
    mnt_command = params.get("MNT_COMMAND", "")
    dedup_key = f"webhook:dedup:moneta:{mnt_operation_id}" if mnt_operation_id else None

    if mnt_operation_id:
        is_new = await redis.set(
            dedup_key, "1", ex=YOOKASSA_WEBHOOK_DEDUP_TTL_SECONDS, nx=True
        )
        if not is_new:
            return "duplicate"

    provider = MonetaPaymentProvider()
    try:
        webhook_data = await provider.verify_webhook(params)
    except ValueError as e:
        logger.warning(
            "moneta_signature_invalid",
            reason=str(e),
            params_safe=moneta_params_for_log(params),
        )
        if mnt_operation_id and dedup_key:
            await redis.delete(dedup_key)
        return "fail"

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
        return "ok"

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
            if mnt_operation_id and dedup_key:
                await redis.delete(dedup_key)
            return "fail"

        payment.moneta_operation_id = webhook_data.external_id

        svc = PaymentWebhookService(db)
        await svc.handle_moneta_payment_succeeded(payment)
    except Exception:
        logger.exception("moneta_webhook_processing_error")
        if mnt_operation_id and dedup_key:
            await redis.delete(dedup_key)
        return "fail"

    return "ok"


async def _kassa_fiscal_xml_for_payment(
    db: AsyncSession,
    payment: Payment,
    params: dict[str, str],
) -> str:
    """Full kassa MNT_RESPONSE XML with INVENTORY/CLIENT (R8)."""
    mnt_id = params.get("MNT_ID", "")
    mnt_transaction_id = params.get("MNT_TRANSACTION_ID", "")
    mnt_amount = Decimal(params.get("MNT_AMOUNT", "0"))
    seller = fiscal_seller_from_settings()
    items = await payment_items_for_fiscal(db, payment)
    inv_json = build_inventory_json(items, seller, mnt_amount)
    email = await _load_user_email(db, payment.user_id)
    client_json = build_client_json(email, None)
    return build_kassa_fiscal_xml(
        mnt_id=mnt_id,
        mnt_transaction_id=mnt_transaction_id,
        result_code="200",
        inventory_json=inv_json,
        client_json=client_json,
        integrity_secret=settings.MONETA_WEBHOOK_SECRET,
        sno=settings.MONETA_FISCAL_SNO,
    )


@router.get(
    "/moneta",
    summary="Moneta Pay URL webhook",
    operation_id="moneta_pay_webhook_get",
)
@router.post(
    "/moneta",
    summary="Moneta Pay URL webhook",
    operation_id="moneta_pay_webhook_post",
)
async def moneta_pay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
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
        should_warn = await redis.set(
            dedup_warn_key, "1", ex=YOOKASSA_WEBHOOK_DEDUP_TTL_SECONDS, nx=True
        )
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
        params_safe=moneta_params_for_log(params),
    )
    outcome = await _moneta_pay_process(db, redis, params)
    if outcome == "fail":
        return PlainTextResponse("FAIL", media_type="text/plain; charset=utf-8")
    return PlainTextResponse("SUCCESS", media_type="text/plain; charset=utf-8")


@router.get(
    "/moneta/kassa",
    summary="Moneta Pay URL for kassa.payanyway.ru (XML INVENTORY/CLIENT)",
    operation_id="moneta_kassa_pay_webhook_get",
)
@router.post(
    "/moneta/kassa",
    summary="Moneta Pay URL for kassa.payanyway.ru (XML INVENTORY/CLIENT)",
    operation_id="moneta_kassa_pay_webhook_post",
)
async def moneta_kassa_pay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> Response:
    """Pay URL после перенаправления с kassa — ответ ``application/xml`` (путь A)."""
    if not settings.MONETA_KASSA_FISCAL_ENABLED:
        raise HTTPException(
            status_code=404,
            detail="Moneta kassa fiscal endpoint is disabled",
        )

    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not client_ip and request.client:
        client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    params = await _collect_moneta_params(request)

    logger.info(
        "moneta_kassa_pay_request",
        method=request.method,
        client_ip=client_ip,
        user_agent=user_agent[:80] if user_agent else None,
        params_safe=moneta_params_for_log(params),
    )

    provider = MonetaPaymentProvider()
    try:
        webhook_data = await provider.verify_webhook(params)
    except ValueError as e:
        logger.warning(
            "moneta_kassa_signature_invalid",
            reason=str(e),
            params_safe=moneta_params_for_log(params),
        )
        xml = build_kassa_error_xml(
            mnt_id=params.get("MNT_ID", ""),
            mnt_transaction_id=params.get("MNT_TRANSACTION_ID", ""),
            result_code="500",
            integrity_secret=settings.MONETA_WEBHOOK_SECRET,
        )
        return Response(content=xml, media_type="application/xml")

    mnt_operation_id = params.get("MNT_OPERATION_ID", "")
    mnt_command = params.get("MNT_COMMAND", "")
    dedup_key = f"webhook:dedup:moneta:{mnt_operation_id}" if mnt_operation_id else None

    if mnt_operation_id:
        is_new = await redis.set(
            dedup_key, "1", ex=YOOKASSA_WEBHOOK_DEDUP_TTL_SECONDS, nx=True
        )
        if not is_new:
            payment = await get_payment_by_mnt_transaction_id(
                db, webhook_data.transaction_id
            )
            if not payment:
                xml = build_kassa_error_xml(
                    mnt_id=params.get("MNT_ID", ""),
                    mnt_transaction_id=params.get("MNT_TRANSACTION_ID", ""),
                    result_code="500",
                    integrity_secret=settings.MONETA_WEBHOOK_SECRET,
                )
                return Response(content=xml, media_type="application/xml")
            try:
                xml = await _kassa_fiscal_xml_for_payment(db, payment, params)
            except FiscalRebuildError as exc:
                logger.warning(
                    "moneta_kassa_fiscal_rebuild_failed",
                    error=str(exc),
                    payment_id=str(payment.id),
                )
                xml = build_kassa_error_xml(
                    mnt_id=params.get("MNT_ID", ""),
                    mnt_transaction_id=params.get("MNT_TRANSACTION_ID", ""),
                    result_code="500",
                    integrity_secret=settings.MONETA_WEBHOOK_SECRET,
                )
                return Response(content=xml, media_type="application/xml")
            return Response(content=xml, media_type="application/xml")

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
        email: str | None = None
        try:
            pid = UUID(webhook_data.transaction_id)
            pr = await db.get(Payment, pid)
            if pr:
                email = await _load_user_email(db, pr.user_id)
        except Exception:
            pass
        client_json = build_client_json(email, None)
        xml = build_kassa_fiscal_xml(
            mnt_id=params.get("MNT_ID", ""),
            mnt_transaction_id=params.get("MNT_TRANSACTION_ID", ""),
            result_code="200",
            inventory_json="[]",
            client_json=client_json,
            integrity_secret=settings.MONETA_WEBHOOK_SECRET,
            sno=settings.MONETA_FISCAL_SNO,
        )
        return Response(content=xml, media_type="application/xml")

    payment: Payment | None = None
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
            if mnt_operation_id and dedup_key:
                await redis.delete(dedup_key)
            xml = build_kassa_error_xml(
                mnt_id=params.get("MNT_ID", ""),
                mnt_transaction_id=params.get("MNT_TRANSACTION_ID", ""),
                result_code="500",
                integrity_secret=settings.MONETA_WEBHOOK_SECRET,
            )
            return Response(content=xml, media_type="application/xml")

        payment.moneta_operation_id = webhook_data.external_id

        svc = PaymentWebhookService(db)
        await svc.handle_moneta_payment_succeeded(payment)
    except Exception:
        logger.exception("moneta_kassa_webhook_processing_error")
        if mnt_operation_id and dedup_key:
            await redis.delete(dedup_key)
        xml = build_kassa_error_xml(
            mnt_id=params.get("MNT_ID", ""),
            mnt_transaction_id=params.get("MNT_TRANSACTION_ID", ""),
            result_code="500",
            integrity_secret=settings.MONETA_WEBHOOK_SECRET,
        )
        return Response(content=xml, media_type="application/xml")

    assert payment is not None
    try:
        xml = await _kassa_fiscal_xml_for_payment(db, payment, params)
    except FiscalRebuildError as exc:
        logger.warning(
            "moneta_kassa_fiscal_rebuild_failed",
            error=str(exc),
            payment_id=str(payment.id),
        )
        xml = build_kassa_error_xml(
            mnt_id=params.get("MNT_ID", ""),
            mnt_transaction_id=params.get("MNT_TRANSACTION_ID", ""),
            result_code="500",
            integrity_secret=settings.MONETA_WEBHOOK_SECRET,
        )
        return Response(content=xml, media_type="application/xml")

    logger.info(
        "moneta_kassa_response_xml",
        payment_id=str(payment.id),
        xml_body=xml,
    )
    return Response(content=xml, media_type="application/xml")


# ------------------------------------------------------------------
# Moneta — Check URL (pre-payment validation)
# ------------------------------------------------------------------


@router.get(
    "/moneta/check",
    summary="Moneta Check URL",
    operation_id="moneta_check_webhook_get",
)
@router.post(
    "/moneta/check",
    summary="Moneta Check URL",
    operation_id="moneta_check_webhook_post",
)
async def moneta_check_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Moneta Check URL — предварительная проверка заказа перед оплатой.

    Коды ответа в XML (``MNT_RESULT_CODE``) по документу MONETA.Assistant, глава 5
    (см. ``docs/new_moneta/MONETA.Assistant.ru__9_.pdf`` и
    ``docs/MONETA_WEBHOOK_TROUBLESHOOTING.md``):

    - ``100`` — в запросе **не было** ``MNT_AMOUNT``; в ответе передаём сумму заказа.
    - ``402`` — заказ создан и готов к оплате (``pending``), в запросе сумма уже была.
    - ``200`` — заказ уже оплачен (``succeeded``).
    - ``500`` — заказ не актуален / не найден; либо неверная подпись входящего запроса.
    """
    params = await _collect_moneta_params(request)
    mnt_id = params.get("MNT_ID", "")
    mnt_transaction_id = params.get("MNT_TRANSACTION_ID", "")

    logger.info("moneta_check_request", params_safe=moneta_params_for_log(params))

    provider = MonetaPaymentProvider()

    try:
        await provider.verify_webhook(params)
    except ValueError:
        logger.warning(
            "moneta_check_signature_invalid",
            params_safe=moneta_params_for_log(params),
        )
        xml = provider.build_check_response(
            mnt_id, mnt_transaction_id, MonetaCheckResultCode.NOT_RELEVANT
        )
        logger.info("moneta_check_response_xml", xml_len=len(xml))
        return Response(content=xml, media_type="application/xml; charset=utf-8")

    mnt_operation_id = params.get("MNT_OPERATION_ID", "")

    payment: Payment | None = None
    try:
        payment_id = UUID(mnt_transaction_id)
    except ValueError:
        payment_id = None

    if payment_id is not None:
        result = await db.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()

    if payment and mnt_operation_id and not payment.moneta_operation_id:
        payment.moneta_operation_id = mnt_operation_id
        if not payment.external_payment_id:
            payment.external_payment_id = mnt_operation_id
        await db.commit()

    if not payment:
        xml = provider.build_check_response(
            mnt_id, mnt_transaction_id, MonetaCheckResultCode.NOT_RELEVANT
        )
    elif payment.status == PaymentStatus.PENDING:
        amount_str = f"{float(payment.amount):.2f}"
        req_amount = (params.get("MNT_AMOUNT") or "").strip()
        if req_amount:
            # Не отклоняем оплату при расхождении суммы (как main-before-refactor):
            # только логируем — Moneta/формат строки могут расходиться с Decimal в БД.
            try:
                req_norm = f"{Decimal(req_amount.replace(',', '.')):.2f}"
                db_norm = f"{Decimal(str(payment.amount)):.2f}"
                if req_norm != db_norm:
                    logger.warning(
                        "moneta_check_amount_mismatch_ignored",
                        mnt_transaction_id=mnt_transaction_id,
                        request_amount=req_amount,
                        payment_amount_db=amount_str,
                    )
            except Exception:
                logger.warning(
                    "moneta_check_amount_parse_failed",
                    mnt_transaction_id=mnt_transaction_id,
                    request_amount=req_amount,
                )
            xml = provider.build_check_response(
                mnt_id,
                mnt_transaction_id,
                MonetaCheckResultCode.READY_FOR_PAYMENT,
                amount=amount_str,
            )
        else:
            # В проверочном запросе не было MNT_AMOUNT — по PDF отвечаем кодом 100 + сумма
            xml = provider.build_check_response(
                mnt_id,
                mnt_transaction_id,
                MonetaCheckResultCode.AMOUNT_REQUIRED,
                amount=amount_str,
            )
    elif payment.status == PaymentStatus.SUCCEEDED:
        xml = provider.build_check_response(
            mnt_id, mnt_transaction_id, MonetaCheckResultCode.ALREADY_PAID
        )
    else:
        xml = provider.build_check_response(
            mnt_id, mnt_transaction_id, MonetaCheckResultCode.NOT_RELEVANT
        )

    logger.info(
        "moneta_check_response",
        payment_found=payment is not None,
        payment_status=str(payment.status)[:32] if payment else None,
        xml_len=len(xml),
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

    Аутентификация: задайте ``MONETA_RECEIPT_WEBHOOK_SECRET`` и передавайте тот же
    токен в заголовке ``X-Moneta-Receipt-Secret``, либо ``MONETA_RECEIPT_IP_ALLOWLIST``
    (CIDR через запятую, как у YooKassa). В ``DEBUG`` без настроек — допускается
    с предупреждением в логах; в production без секрета и allowlist — 403.
    """
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not client_ip and request.client:
        client_ip = request.client.host

    header_secret = request.headers.get("x-moneta-receipt-secret")
    if not is_moneta_receipt_webhook_authorized(
        client_ip=client_ip, header_secret=header_secret
    ):
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Moneta receipt webhook authentication failed",
                    "details": {},
                }
            },
        )

    body = await request.json()
    logger.info(
        "moneta_receipt_webhook",
        body_summary=moneta_receipt_body_summary(body),
        client_ip=client_ip,
    )

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
            receipt.status = ReceiptStatus.SUCCEEDED
    else:
        receipt = Receipt(
            payment_id=payment.id,
            receipt_type=receipt_type,
            receipt_url=str(receipt_url) if receipt_url and receipt_url is not False else None,
            amount=payment.amount,
            status=ReceiptStatus.SUCCEEDED,
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


# ------------------------------------------------------------------
# YooKassa v2 — inbox-based webhook (feature-flagged)
# ------------------------------------------------------------------


@router.post(
    "/yookassa/v2",
    summary="YooKassa webhook v2 (inbox + TaskIQ)",
    include_in_schema=False,
)
@limiter.limit("120/minute")
async def yookassa_webhook_v2(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    """Inbox-based YooKassa webhook handler.

    Pipeline: parse → Redis dedup → persist raw to DB → verify IP → enqueue TaskIQ.

    Only active when ``WEBHOOK_INBOX_ENABLED=true`` in settings.  When the flag
    is off, returns 404 so traffic remains on the legacy endpoint.
    """
    import json
    import uuid as _uuid

    from app.core.config import settings as _settings

    if not _settings.WEBHOOK_INBOX_ENABLED:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    from app.models.payment_webhook_inbox import PaymentWebhookInbox
    from app.services.payment_utils import is_ip_allowed
    from app.tasks.payment_webhook_tasks import process_payment_webhook_inbox

    raw_bytes = await request.body()
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not client_ip and request.client:
        client_ip = request.client.host

    try:
        body = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(status_code=400, content={"status": "bad_request"})

    event_type = body.get("event", "")
    ext_id = (body.get("object") or {}).get("id", "")
    dedup_redis = f"{YOOKASSA_WEBHOOK_DEDUP_KEY_PREFIX}v2:{event_type}:{ext_id}"

    if ext_id:
        already = await redis.set(dedup_redis, "1", ex=YOOKASSA_WEBHOOK_DEDUP_TTL_SECONDS, nx=True)
        if not already:
            return JSONResponse(content={"status": "ok"})

    external_event_key = f"yookassa:{event_type}:{ext_id}"
    row = PaymentWebhookInbox(
        id=_uuid.uuid4(),
        provider="yookassa",
        external_event_key=external_event_key,
        raw_headers=dict(request.headers),
        raw_body=body,
        client_ip=client_ip,
        status="received",
    )
    db.add(row)
    try:
        await db.flush()
        await db.commit()
    except Exception:
        await db.rollback()
        if ext_id:
            await redis.delete(dedup_redis)
        logger.exception("webhook_inbox_persist_failed", provider="yookassa")
        return JSONResponse(status_code=500, content={"status": "error"})

    # IP verification — after persist so the raw payload is always stored.
    if not is_ip_allowed(client_ip):
        logger.warning("webhook_v2_ip_rejected", ip=client_ip)
        row.status = "dead"
        row.verify_error = f"IP not in whitelist: {client_ip}"
        try:
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.warning("webhook_inbox_dead_commit_failed")
        if ext_id:
            await redis.delete(dedup_redis)
        return JSONResponse(status_code=403, content={"status": "forbidden"})

    row.status = "verified"
    try:
        await db.commit()
    except Exception:
        logger.exception("webhook_inbox_verify_update_failed")

    try:
        await process_payment_webhook_inbox.kiq(str(row.id))
    except Exception:
        # Queue unavailable — the cron ``retry_stale_webhook_inbox_rows`` will
        # pick up any ``verified`` rows without a ``next_run_at`` set.
        logger.exception("webhook_inbox_enqueue_failed", inbox_id=str(row.id))

    return JSONResponse(content={"status": "ok"})
