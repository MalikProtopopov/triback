"""User-facing payment operations — list own payments, view receipts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.subscriptions import Payment


def _payment_url_if_active(p: Payment) -> str | None:
    """Return payment URL only for pending payments whose link hasn't expired."""
    if p.status != "pending" or not p.external_payment_url:
        return None
    if p.expires_at and p.expires_at < datetime.now(UTC):
        return None
    return p.external_payment_url


class PaymentUserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_user_payments(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        from app.schemas.subscriptions import UserPaymentListItem, _STATUS_LABELS

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
                status_label=_STATUS_LABELS.get(p.status, p.status),
                description=p.description,
                payment_url=_payment_url_if_active(p),
                expires_at=p.expires_at if p.status == "pending" else None,
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
