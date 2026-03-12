"""Subscription service — pay, status, webhook handling, manual payments."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from typing import Any
from uuid import UUID

import structlog
from redis.asyncio import Redis
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.exceptions import (
    AppValidationError,
    ForbiddenError,
    NotFoundError,
)
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Plan, Subscription
from app.schemas.payments import (
    ManualPaymentRequest,
    ManualPaymentResponse,
    PaymentListItem,
    PaymentListResponse,
    PaymentsSummary,
    PaymentUserNested,
)
from app.schemas.subscriptions import (
    CurrentSubscriptionNested,
    PayResponse,
    PlanNested,
    SubscriptionStatusResponse,
)
from app.services.payment_service import YooKassaClient
from app.tasks.email_tasks import (
    send_payment_failed_notification,
    send_payment_succeeded_notification,
)

logger = structlog.get_logger(__name__)

LAPSE_THRESHOLD_DAYS = 90

_YOOKASSA_NETWORKS: list[IPv4Network | IPv6Network] = []


def _get_yookassa_networks() -> list[IPv4Network | IPv6Network]:
    global _YOOKASSA_NETWORKS  # noqa: PLW0603
    if not _YOOKASSA_NETWORKS:
        raw = getattr(settings, "YOOKASSA_IP_WHITELIST", "")
        for cidr in raw.split(","):
            cidr = cidr.strip()
            if cidr:
                _YOOKASSA_NETWORKS.append(ip_network(cidr, strict=False))
    return _YOOKASSA_NETWORKS


def _is_ip_allowed(client_ip: str) -> bool:
    if not client_ip:
        return False
    networks = _get_yookassa_networks()
    if not networks:
        if settings.DEBUG:
            logger.warning("yookassa_ip_whitelist_empty_debug_mode")
            return True
        logger.error("yookassa_ip_whitelist_empty_production")
        return False
    try:
        addr: IPv4Address | IPv6Address = ip_address(client_ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def _build_receipt(
    email: str, description: str, amount: Decimal
) -> dict[str, Any]:
    """Build a 54-FZ compliant receipt payload for YooKassa."""
    return {
        "customer": {"email": email},
        "items": [
            {
                "description": description[:128],
                "quantity": "1",
                "amount": {"value": str(amount), "currency": "RUB"},
                "vat_code": 1,
                "payment_subject": "service",
                "payment_mode": "full_payment",
            }
        ],
    }


class SubscriptionService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:  # type: ignore[type-arg]
        self.db = db
        self.redis = redis
        self.yookassa = YooKassaClient()

    # ── POST /subscriptions/pay ───────────────────────────────────

    async def pay(self, user_id: UUID, plan_id: UUID, idempotency_key: str) -> PayResponse:
        cache_key = f"idempotency:pay:{user_id}:{idempotency_key}"
        cached = await self.redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return PayResponse(**data)

        plan = await self.db.get(Plan, plan_id)
        if not plan or not plan.is_active:
            raise NotFoundError("Plan not found or inactive")

        dp_result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        dp = dp_result.scalar_one_or_none()
        if not dp:
            raise NotFoundError("Doctor profile not found")
        if not dp.has_medical_diploma:
            raise AppValidationError(
                "Оплата невозможна без диплома о высшем медицинском образовании"
            )

        product_type = await self._determine_product_type(user_id)

        sub = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status="pending_payment",
            is_first_year=product_type == "entry_fee",
        )
        self.db.add(sub)
        await self.db.flush()

        payment = Payment(
            user_id=user_id,
            amount=plan.price,
            product_type=product_type,
            payment_provider="yookassa",
            status="pending",
            subscription_id=sub.id,
            idempotency_key=idempotency_key,
            description=f"{plan.name} — Ассоциация трихологов",
        )
        self.db.add(payment)
        await self.db.flush()

        return_url = f"{settings.YOOKASSA_RETURN_URL}?payment_id={payment.id}"

        from app.models.users import User

        user_row = await self.db.execute(select(User.email).where(User.id == user_id))
        user_email = user_row.scalar_one_or_none() or ""

        receipt = _build_receipt(
            email=user_email,
            description=payment.description or plan.name,
            amount=Decimal(str(plan.price)),
        )

        yookassa_resp = await self.yookassa.create_payment(
            amount=Decimal(str(plan.price)),
            description=payment.description or "",
            metadata={
                "internal_payment_id": str(payment.id),
                "product_type": product_type,
                "user_id": str(user_id),
            },
            idempotency_key=idempotency_key,
            return_url=return_url,
            receipt=receipt,
        )

        payment.external_payment_id = yookassa_resp.get("id")
        confirmation = yookassa_resp.get("confirmation", {})
        payment.external_payment_url = confirmation.get("confirmation_url")

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = (
                await self.db.execute(
                    select(Payment).where(
                        Payment.user_id == user_id,
                        Payment.idempotency_key == idempotency_key,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                return PayResponse(
                    payment_id=existing.id,
                    payment_url=existing.external_payment_url or "",
                    amount=float(existing.amount),
                )
            raise

        resp = PayResponse(
            payment_id=payment.id,
            payment_url=payment.external_payment_url or "",
            amount=float(plan.price),
        )

        ttl = getattr(settings, "PAYMENT_IDEMPOTENCY_TTL", 86400)
        await self.redis.set(cache_key, resp.model_dump_json(), ex=ttl)

        return resp

    async def _determine_product_type(self, user_id: UUID) -> str:
        result = await self.db.execute(
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == "active",
                )
            )
            .order_by(Subscription.ends_at.desc())
            .limit(1)
        )
        latest_sub = result.scalar_one_or_none()

        if not latest_sub or latest_sub.ends_at is None:
            has_entry = await self._has_paid_entry_fee(user_id)
            return "subscription" if has_entry else "entry_fee"

        now = datetime.now(UTC)
        if latest_sub.ends_at.tzinfo is None:
            lapse = now.replace(tzinfo=None) - latest_sub.ends_at
        else:
            lapse = now - latest_sub.ends_at

        if lapse > timedelta(days=LAPSE_THRESHOLD_DAYS):
            return "entry_fee"
        return "subscription"

    async def _has_paid_entry_fee(self, user_id: UUID) -> bool:
        result = await self.db.execute(
            select(func.count(Payment.id)).where(
                and_(
                    Payment.user_id == user_id,
                    Payment.product_type == "entry_fee",
                    Payment.status == "succeeded",
                )
            )
        )
        return (result.scalar() or 0) > 0

    # ── GET /subscriptions/status ─────────────────────────────────

    async def get_status(self, user_id: UUID) -> SubscriptionStatusResponse:
        result = await self.db.execute(
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        has_entry = await self._has_paid_entry_fee(user_id)

        if not latest:
            return SubscriptionStatusResponse(
                has_subscription=False,
                has_paid_entry_fee=has_entry,
                can_renew=False,
                next_action="pay_entry_fee" if not has_entry else "pay_subscription",
            )

        now = datetime.now(UTC)
        current: CurrentSubscriptionNested | None = None
        can_renew = False
        next_action: str | None = None

        if latest.status == "active" and latest.ends_at:
            days_remaining = max(0, (latest.ends_at - now).days) if latest.ends_at.tzinfo else max(0, (latest.ends_at - now.replace(tzinfo=None)).days)
            current = CurrentSubscriptionNested(
                id=latest.id,
                plan=PlanNested(code=latest.plan.code, name=latest.plan.name),
                status=latest.status,
                starts_at=latest.starts_at,
                ends_at=latest.ends_at,
                days_remaining=days_remaining,
            )
            if days_remaining < 30:
                can_renew = True
        elif latest.status == "expired":
            next_action = "renew"
        elif latest.status == "pending_payment":
            next_action = "complete_payment"

        return SubscriptionStatusResponse(
            has_subscription=latest.status == "active",
            current_subscription=current,
            has_paid_entry_fee=has_entry,
            can_renew=can_renew,
            next_action=next_action,
        )

    # ── Webhook handling ──────────────────────────────────────────

    async def handle_webhook(self, body: dict[str, Any], client_ip: str) -> None:
        if not _is_ip_allowed(client_ip):
            raise ForbiddenError("IP not in YooKassa whitelist")

        event = body.get("event", "")
        obj = body.get("object", {})
        external_id = obj.get("id")

        if not external_id:
            logger.warning("webhook_missing_external_id", body=body)
            return

        result = await self.db.execute(
            select(Payment)
            .where(Payment.external_payment_id == external_id)
            .with_for_update()
        )
        payment = result.scalar_one_or_none()

        if not payment:
            metadata = obj.get("metadata", {})
            internal_id = metadata.get("internal_payment_id")
            if internal_id:
                result = await self.db.execute(
                    select(Payment)
                    .where(Payment.id == internal_id)
                    .with_for_update()
                )
                payment = result.scalar_one_or_none()

        if not payment:
            logger.warning("webhook_payment_not_found", external_id=external_id)
            return

        if event == "payment.succeeded":
            await self._handle_payment_succeeded(payment, obj)
        elif event == "payment.canceled":
            await self._handle_payment_canceled(payment)
        elif event == "refund.succeeded":
            await self._handle_refund_succeeded(payment)
        else:
            logger.info("webhook_unknown_event", event=event)

    async def _handle_payment_succeeded(
        self, payment: Payment, obj: dict[str, Any]
    ) -> None:
        if payment.status == "succeeded":
            return

        from app.models.subscriptions import Receipt

        now = datetime.now(UTC)
        payment.status = "succeeded"  # type: ignore[assignment]
        payment.paid_at = now

        if payment.product_type in ("entry_fee", "subscription"):
            await self._activate_subscription(payment, now)
        elif payment.product_type == "event":
            await self._confirm_event_registration(payment)

        receipt_reg = obj.get("receipt_registration") or obj.get("receipt")
        if receipt_reg:
            receipt = Receipt(
                payment_id=payment.id,
                receipt_type="payment",
                provider_receipt_id=receipt_reg.get("id") or receipt_reg.get("receipt_id"),
                receipt_url=receipt_reg.get("receipt_url"),
                fiscal_number=receipt_reg.get("fiscal_provider_id"),
                fiscal_document=receipt_reg.get("fiscal_document_number"),
                fiscal_sign=receipt_reg.get("fiscal_sign"),
                receipt_data=receipt_reg,
                amount=payment.amount,
                status="succeeded",
            )
            self.db.add(receipt)

        await self.db.commit()

        from app.models.users import User

        email_result = await self.db.execute(
            select(User.email).where(User.id == payment.user_id)
        )
        email = email_result.scalar_one_or_none()
        if email:
            receipt_url = receipt_reg.get("receipt_url") if receipt_reg else None
            await send_payment_succeeded_notification.kiq(
                email, float(payment.amount), payment.product_type, receipt_url
            )
            from app.tasks.telegram_tasks import notify_admin_payment_received

            await notify_admin_payment_received.kiq(
                email, float(payment.amount), payment.product_type
            )

    async def _activate_subscription(self, payment: Payment, now: datetime) -> None:
        if not payment.subscription_id:
            return

        sub = await self.db.get(Subscription, payment.subscription_id)
        if not sub:
            return

        plan = await self.db.get(Plan, sub.plan_id)
        duration_months = plan.duration_months if plan else 12

        if sub.status != "active":
            sub.status = "active"  # type: ignore[assignment]

        prev_end = sub.ends_at
        if prev_end and prev_end > now:
            sub.starts_at = sub.starts_at or now
        else:
            sub.starts_at = now

        from dateutil.relativedelta import relativedelta

        sub.ends_at = (sub.starts_at or now) + relativedelta(months=duration_months)

        dp_result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == payment.user_id)
        )
        dp = dp_result.scalar_one_or_none()
        if dp and dp.status == "approved":
            dp.status = "active"  # type: ignore[assignment]

    async def _confirm_event_registration(self, payment: Payment) -> None:
        if not payment.event_registration_id:
            return
        from app.models.events import EventRegistration

        reg = await self.db.get(EventRegistration, payment.event_registration_id)
        if reg and reg.status != "confirmed":
            reg.status = "confirmed"  # type: ignore[assignment]

    async def _handle_payment_canceled(self, payment: Payment) -> None:
        if payment.status in ("succeeded", "failed"):
            return
        payment.status = "failed"  # type: ignore[assignment]

        if payment.product_type == "event" and payment.event_registration_id:
            await self._cancel_event_registration(payment)

        await self.db.commit()

        from app.models.users import User

        email_result = await self.db.execute(
            select(User.email).where(User.id == payment.user_id)
        )
        email = email_result.scalar_one_or_none()
        if email:
            await send_payment_failed_notification.kiq(email)

    async def _cancel_event_registration(self, payment: Payment) -> None:
        from app.models.events import EventRegistration, EventTariff

        reg = await self.db.get(EventRegistration, payment.event_registration_id)
        if not reg:
            return
        if reg.status != "cancelled":
            reg.status = "cancelled"  # type: ignore[assignment]
            tariff = await self.db.get(EventTariff, reg.event_tariff_id)
            if tariff and tariff.seats_taken > 0:
                tariff.seats_taken -= 1

    async def _handle_refund_succeeded(self, payment: Payment) -> None:
        if payment.status == "refunded":
            return
        payment.status = "refunded"  # type: ignore[assignment]

        if payment.product_type == "event" and payment.event_registration_id:
            await self._cancel_event_registration(payment)

        await self.db.commit()

    # ── Doctor: list own payments ─────────────────────────────────

    async def list_user_payments(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        from app.schemas.subscriptions import UserPaymentListItem

        base = select(Payment).where(Payment.user_id == user_id)
        count_q = select(func.count(Payment.id)).where(Payment.user_id == user_id)

        total = (await self.db.execute(count_q)).scalar() or 0
        rows = (
            await self.db.execute(
                base.order_by(Payment.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()

        items = [
            UserPaymentListItem(
                id=p.id,
                amount=float(p.amount),
                product_type=p.product_type,
                status=p.status,
                description=p.description,
                paid_at=p.paid_at,
                created_at=p.created_at,
            )
            for p in rows
        ]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    async def get_user_receipt(
        self, user_id: UUID, payment_id: UUID
    ) -> dict[str, Any]:
        from app.models.subscriptions import Receipt

        payment = await self.db.get(Payment, payment_id)
        if not payment or payment.user_id != user_id:
            raise NotFoundError("Payment not found")

        result = await self.db.execute(
            select(Receipt).where(Receipt.payment_id == payment_id)
        )
        receipt = result.scalar_one_or_none()
        if not receipt:
            raise NotFoundError("Receipt not found for this payment")

        return {
            "id": receipt.id,
            "receipt_type": receipt.receipt_type,
            "provider_receipt_id": receipt.provider_receipt_id,
            "receipt_url": receipt.receipt_url,
            "fiscal_number": receipt.fiscal_number,
            "fiscal_document": receipt.fiscal_document,
            "fiscal_sign": receipt.fiscal_sign,
            "amount": float(receipt.amount),
            "status": receipt.status,
        }

    # ── Admin: list payments ──────────────────────────────────────

    async def list_payments(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        product_type: str | None = None,
        user_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PaymentListResponse:
        from app.models.users import User

        base = (
            select(Payment)
            .join(User, Payment.user_id == User.id)
            .options(joinedload(Payment.receipts))
        )
        count_q = select(func.count(Payment.id)).join(User, Payment.user_id == User.id)

        filters: list[Any] = []
        if status:
            filters.append(Payment.status == status)
        if product_type:
            filters.append(Payment.product_type == product_type)
        if user_id:
            filters.append(Payment.user_id == user_id)
        if date_from:
            filters.append(Payment.created_at >= date_from)
        if date_to:
            filters.append(Payment.created_at <= date_to)

        if filters:
            base = base.where(and_(*filters))
            count_q = count_q.where(and_(*filters))

        total = (await self.db.execute(count_q)).scalar() or 0

        sum_q = select(
            func.coalesce(func.sum(Payment.amount).filter(Payment.status == "succeeded"), 0),
            func.count(Payment.id).filter(Payment.status == "succeeded"),
            func.count(Payment.id).filter(Payment.status == "pending"),
        )
        if filters:
            sum_q = sum_q.where(and_(*filters))
        sum_row = (await self.db.execute(sum_q)).one()

        sort_col = Payment.created_at
        base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
        base = base.offset(offset).limit(limit)

        rows = (await self.db.execute(base)).unique().scalars().all()

        pay_user_ids = list({p.user_id for p in rows})
        user_map: dict[UUID, tuple[UUID, str]] = {}
        dp_name_map: dict[UUID, str] = {}
        if pay_user_ids:
            u_q = await self.db.execute(
                select(User.id, User.email).where(User.id.in_(pay_user_ids))
            )
            for uid, email in u_q.all():
                user_map[uid] = (uid, email)
            dp_q = await self.db.execute(
                select(DoctorProfile.user_id, DoctorProfile.first_name, DoctorProfile.last_name)
                .where(DoctorProfile.user_id.in_(pay_user_ids))
            )
            for uid, fn, ln in dp_q.all():
                dp_name_map[uid] = f"{ln} {fn}"

        items: list[PaymentListItem] = []
        for p in rows:
            u_info = user_map.get(p.user_id)
            user_nested = PaymentUserNested(
                id=u_info[0] if u_info else p.user_id,
                email=u_info[1] if u_info else "",
                full_name=dp_name_map.get(p.user_id),
            )
            items.append(
                PaymentListItem(
                    id=p.id,
                    user=user_nested,
                    amount=float(p.amount),
                    product_type=p.product_type,
                    payment_provider=p.payment_provider,
                    status=p.status,
                    description=p.description,
                    has_receipt=bool(p.receipts) if hasattr(p, "receipts") else False,
                    paid_at=p.paid_at,
                    created_at=p.created_at,
                )
            )

        return PaymentListResponse(
            data=items,
            summary=PaymentsSummary(
                total_amount=float(sum_row[0]),
                count_completed=int(sum_row[1]),
                count_pending=int(sum_row[2]),
            ),
            total=total,
            limit=limit,
            offset=offset,
        )

    # ── Admin: manual payment ─────────────────────────────────────

    async def create_manual_payment(
        self, admin_id: UUID, body: ManualPaymentRequest
    ) -> ManualPaymentResponse:
        from app.models.users import User

        user = await self.db.get(User, body.user_id)
        if not user:
            raise NotFoundError("User not found")

        now = datetime.now(UTC)

        payment = Payment(
            user_id=body.user_id,
            amount=body.amount,
            product_type=body.product_type,
            payment_provider="manual",
            status="succeeded",
            subscription_id=body.subscription_id,
            event_registration_id=body.event_registration_id,
            description=body.description,
            paid_at=now,
        )
        self.db.add(payment)
        await self.db.flush()

        if body.product_type in ("entry_fee", "subscription") and body.subscription_id:
            await self._activate_subscription(payment, now)

        await self.db.commit()

        await send_payment_succeeded_notification.kiq(
            user.email, float(body.amount), body.product_type
        )

        return ManualPaymentResponse(
            payment_id=payment.id,
            status="succeeded",
            payment_provider="manual",
        )
