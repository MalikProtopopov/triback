"""Admin payment operations — list, manual create, refund."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.enums import PaymentStatus, ProductType
from app.core.exceptions import AppValidationError, NotFoundError
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
from app.services.payment_service import YooKassaClient
from app.services.payment_webhook_service import PaymentWebhookService
from app.tasks.email_tasks import send_payment_succeeded_notification

logger = structlog.get_logger(__name__)


class PaymentAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.yookassa = YooKassaClient()

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
            func.coalesce(func.sum(Payment.amount).filter(Payment.status == PaymentStatus.SUCCEEDED), 0),
            func.count(Payment.id).filter(Payment.status == PaymentStatus.SUCCEEDED),
            func.count(Payment.id).filter(Payment.status == PaymentStatus.PENDING),
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
            status=PaymentStatus.SUCCEEDED,
            subscription_id=body.subscription_id,
            event_registration_id=body.event_registration_id,
            description=body.description,
            paid_at=now,
        )
        self.db.add(payment)
        await self.db.flush()

        if body.product_type in (ProductType.ENTRY_FEE, ProductType.SUBSCRIPTION) and body.subscription_id:
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
                "Cannot refund a manual payment through YooKassa"
            )

        refund_amount = Decimal(str(amount)) if amount else Decimal(str(payment.amount))
        if refund_amount > Decimal(str(payment.amount)):
            raise AppValidationError("Refund amount exceeds payment amount")

        idempotency_key = f"refund-{payment.id}-{refund_amount}"
        yookassa_resp = await self.yookassa.create_refund(
            payment_id=payment.external_payment_id,
            amount=refund_amount,
            description=reason,
            idempotency_key=idempotency_key,
        )

        logger.info(
            "refund_initiated",
            payment_id=str(payment_id),
            refund_id=yookassa_resp.get("id"),
            amount=str(refund_amount),
        )

        return RefundResponse(
            refund_id=yookassa_resp.get("id", ""),
            payment_id=str(payment.external_payment_id),
            status=yookassa_resp.get("status", "pending"),
            amount=float(refund_amount),
        ).model_dump()
