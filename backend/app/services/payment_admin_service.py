"""Admin payment operations — list, manual create, refund."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.admin_filters import build_name_ilike_filter, normalize_msk_day_range
from app.core.enums import PaymentStatus, ProductType
from app.core.exceptions import AppValidationError, NotFoundError
from app.models.arrears import MembershipArrear
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment
from app.schemas.payments import (
    ManualPaymentRequest,
    ManualPaymentResponse,
    PaymentListItem,
    PaymentListResponse,
    PaymentsSummary,
    PaymentUserNested,
)
from app.services.payment_providers import get_provider
from app.services.payment_user_service import _payment_url_if_active
from app.services.membership_arrears_service import mark_arrear_paid_from_payment
from app.services.payment_webhook_service import PaymentWebhookService
from app.tasks.email_tasks import send_payment_succeeded_notification

logger = structlog.get_logger(__name__)


class PaymentAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.provider = get_provider()

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
        name: str | None = None,
        provider_id: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PaymentListResponse:
        from app.models.users import User

        base = (
            select(Payment)
            .join(User, Payment.user_id == User.id)
            .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
            .options(joinedload(Payment.receipts))
        )
        count_q = (
            select(func.count(Payment.id))
            .join(User, Payment.user_id == User.id)
            .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        )

        filters: list[Any] = []
        if status:
            filters.append(Payment.status == status)
        if product_type:
            filters.append(Payment.product_type == product_type)
        if user_id:
            filters.append(Payment.user_id == user_id)

        lo, hi = normalize_msk_day_range(date_from, date_to)
        if lo is not None:
            filters.append(Payment.created_at >= lo)
        if hi is not None:
            filters.append(Payment.created_at < hi)

        name_clause = build_name_ilike_filter(
            name,
            DoctorProfile.last_name,
            DoctorProfile.first_name,
            DoctorProfile.middle_name,
            User.email,
        )
        if name_clause is not None:
            filters.append(name_clause)

        if provider_id:
            pid = provider_id.strip()
            if pid:
                filters.append(
                    or_(
                        Payment.external_payment_id == pid,
                        Payment.moneta_operation_id == pid,
                    )
                )

        if filters:
            base = base.where(and_(*filters))
            count_q = count_q.where(and_(*filters))

        total = (await self.db.execute(count_q)).scalar() or 0

        sum_q = (
            select(
                func.coalesce(func.sum(Payment.amount).filter(Payment.status == PaymentStatus.SUCCEEDED), 0),
                func.count(Payment.id).filter(Payment.status == PaymentStatus.SUCCEEDED),
                func.count(Payment.id).filter(Payment.status == PaymentStatus.PENDING),
            )
            .join(User, Payment.user_id == User.id)
            .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
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
                select(DoctorProfile.user_id, DoctorProfile.first_name, DoctorProfile.last_name, DoctorProfile.middle_name)
                .where(DoctorProfile.user_id.in_(pay_user_ids))
            )
            for uid, fn, ln, mn in dp_q.all():
                parts = [p for p in [ln, fn, mn] if p]
                dp_name_map[uid] = " ".join(parts)

        from app.schemas.subscriptions import _STATUS_LABELS

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
                    status_label=_STATUS_LABELS.get(p.status, p.status),
                    description=p.description,
                    payment_url=_payment_url_if_active(p),
                    expires_at=p.expires_at if p.status == "pending" else None,
                    has_receipt=bool(p.receipts) if hasattr(p, "receipts") else False,
                    paid_at=p.paid_at,
                    created_at=p.created_at,
                    external_payment_id=p.external_payment_id,
                    moneta_operation_id=p.moneta_operation_id,
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

    async def create_manual_payment(
        self, admin_id: UUID, body: ManualPaymentRequest
    ) -> ManualPaymentResponse:
        from app.models.users import User

        user = await self.db.get(User, body.user_id)
        if not user:
            raise NotFoundError("User not found")

        now = datetime.now(UTC)

        if body.product_type == ProductType.MEMBERSHIP_ARREARS:
            if not body.arrear_id:
                raise AppValidationError("arrear_id обязателен для membership_arrears")
            if body.subscription_id or body.event_registration_id:
                raise AppValidationError(
                    "subscription_id и event_registration_id не используются для задолженности"
                )
            ar = await self.db.get(MembershipArrear, body.arrear_id)
            if not ar or ar.user_id != body.user_id:
                raise NotFoundError("Задолженность не найдена")
            if ar.status != "open":
                raise AppValidationError("Задолженность не в статусе open")
            if Decimal(str(body.amount)) != ar.amount:
                raise AppValidationError("Сумма должна совпадать с задолженностью")
        elif body.arrear_id:
            raise AppValidationError("arrear_id допустим только для membership_arrears")

        payment = Payment(
            user_id=body.user_id,
            amount=body.amount,
            product_type=body.product_type,
            payment_provider="manual",
            status=PaymentStatus.SUCCEEDED,
            subscription_id=body.subscription_id,
            event_registration_id=body.event_registration_id,
            arrear_id=body.arrear_id,
            description=body.description,
            paid_at=now,
        )
        self.db.add(payment)
        await self.db.flush()

        if body.product_type == ProductType.MEMBERSHIP_ARREARS:
            await mark_arrear_paid_from_payment(self.db, payment, now)
        elif body.product_type in (ProductType.ENTRY_FEE, ProductType.SUBSCRIPTION) and body.subscription_id:
            webhook_svc = PaymentWebhookService(self.db)
            await webhook_svc._activate_subscription(payment, now)

        await self.db.commit()

        await send_payment_succeeded_notification.kiq(
            user.email, float(body.amount), body.product_type
        )

        return ManualPaymentResponse(
            payment_id=payment.id,
            status=PaymentStatus.SUCCEEDED,
            payment_provider="manual",
        )

    async def cancel_payment(
        self,
        payment_id: UUID,
        reason: str,
    ) -> dict[str, Any]:
        from app.schemas.payments import CancelPaymentResponse

        payment = await self.db.get(Payment, payment_id)
        if not payment:
            raise NotFoundError("Payment not found")

        if payment.status != PaymentStatus.PENDING:
            raise AppValidationError(
                f"Можно отменить только платёж в статусе 'pending'. "
                f"Текущий статус: '{payment.status}'"
            )

        payment.status = PaymentStatus.FAILED
        payment.description = (
            f"{payment.description or ''} | Отменён администратором: {reason}"
        ).strip(" |")

        cancelled_subscription = False
        cancelled_event_registration = False

        if payment.subscription_id:
            from app.core.enums import SubscriptionStatus
            from app.models.subscriptions import Subscription

            sub = await self.db.get(Subscription, payment.subscription_id)
            if sub and sub.status == SubscriptionStatus.PENDING_PAYMENT:
                sub.status = SubscriptionStatus.CANCELLED
                cancelled_subscription = True

        if payment.event_registration_id:
            webhook_svc = PaymentWebhookService(self.db)
            await webhook_svc._cancel_event_registration(payment)
            cancelled_event_registration = True

        await self.db.commit()

        logger.info(
            "payment_cancelled_by_admin",
            payment_id=str(payment_id),
            reason=reason,
            cancelled_subscription=cancelled_subscription,
            cancelled_event_registration=cancelled_event_registration,
        )

        return CancelPaymentResponse(
            payment_id=payment.id,
            status=PaymentStatus.FAILED,
            cancelled_subscription=cancelled_subscription,
            cancelled_event_registration=cancelled_event_registration,
            message="Платёж отменён. Пользователь может создать новый платёж.",
        ).model_dump()

    async def initiate_refund(
        self,
        payment_id: UUID,
        amount: float | None,
        reason: str,
    ) -> dict[str, Any]:
        from app.schemas.payments import RefundResponse

        payment = await self.db.get(Payment, payment_id)
        if not payment:
            raise NotFoundError("Payment not found")

        if payment.status != PaymentStatus.SUCCEEDED:
            raise AppValidationError(
                f"Cannot refund payment with status '{payment.status}'"
            )
        if not payment.external_payment_id:
            raise AppValidationError(
                "Cannot refund a manual payment — no external payment ID"
            )

        refund_amount = Decimal(str(amount)) if amount else Decimal(str(payment.amount))
        if refund_amount > Decimal(str(payment.amount)):
            raise AppValidationError("Refund amount exceeds payment amount")

        idempotency_key = f"refund-{payment.id}-{refund_amount}"
        try:
            refund_result = await self.provider.create_refund(
                external_payment_id=payment.external_payment_id,
                amount=refund_amount,
                description=reason,
                idempotency_key=idempotency_key,
            )
        except NotImplementedError:
            raise AppValidationError(
                "Возвраты через текущий платёжный провайдер не поддерживаются автоматически. "
                "Используйте ЛК провайдера для оформления возврата."
            ) from None

        logger.info(
            "refund_initiated",
            payment_id=str(payment_id),
            refund_id=refund_result.external_id,
            amount=str(refund_amount),
        )

        return RefundResponse(
            refund_id=refund_result.external_id,
            payment_id=str(payment.external_payment_id),
            status=refund_result.status,
            amount=float(refund_amount),
        ).model_dump()
