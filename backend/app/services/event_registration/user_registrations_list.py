"""List event registrations for a user with event, tariff, and optional payment."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.events import Event, EventRegistration, EventTariff
from app.models.subscriptions import Payment
from app.schemas.event_registration import (
    UserEventNested,
    UserEventRegistrationListItem,
    UserEventRegistrationNested,
    UserEventRegistrationPaymentNested,
    UserEventTariffNested,
)
from app.schemas.subscriptions import _STATUS_LABELS
from app.services import file_service
from app.services.payment_user_service import _payment_url_if_active


async def list_registrations_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    event_id: UUID | None = None,
) -> dict[str, Any]:
    """Return paginated registrations with joined event/tariff and latest matching payment."""
    conds = [EventRegistration.user_id == user_id]
    if status:
        conds.append(EventRegistration.status == status)
    if event_id:
        conds.append(EventRegistration.event_id == event_id)
    where_clause = and_(*conds)

    count_q = select(func.count(EventRegistration.id)).where(where_clause)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(EventRegistration, Event, EventTariff)
        .join(Event, EventRegistration.event_id == Event.id)
        .join(EventTariff, EventRegistration.event_tariff_id == EventTariff.id)
        .where(where_clause)
        .order_by(EventRegistration.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(q)).all()

    reg_ids = [r[0].id for r in rows]
    pay_by_reg: dict[UUID, Payment] = {}
    if reg_ids:
        pay_rows = (
            await db.execute(
                select(Payment)
                .where(
                    Payment.event_registration_id.in_(reg_ids),
                    Payment.user_id == user_id,
                )
                .order_by(Payment.created_at.desc())
            )
        ).scalars().all()
        for p in pay_rows:
            rid = p.event_registration_id
            if rid and rid not in pay_by_reg:
                pay_by_reg[rid] = p

    items: list[UserEventRegistrationListItem] = []
    for reg, evt, tariff in rows:
        p = pay_by_reg.get(reg.id)
        payment_model: UserEventRegistrationPaymentNested | None = None
        if p:
            payment_model = UserEventRegistrationPaymentNested(
                id=p.id,
                amount=float(p.amount),
                product_type=p.product_type,
                status=p.status,
                status_label=_STATUS_LABELS.get(p.status, p.status),
                description=p.description,
                payment_url=_payment_url_if_active(p),
                paid_at=p.paid_at,
                expires_at=p.expires_at if p.status == "pending" else None,
                created_at=p.created_at,
                external_payment_id=p.external_payment_id,
            )

        items.append(
            UserEventRegistrationListItem(
                registration=UserEventRegistrationNested(
                    id=reg.id,
                    status=reg.status,
                    created_at=reg.created_at,
                    guest_full_name=reg.guest_full_name,
                    guest_email=reg.guest_email,
                    guest_workplace=reg.guest_workplace,
                    guest_specialization=reg.guest_specialization,
                    fiscal_email=reg.fiscal_email,
                ),
                event=UserEventNested(
                    id=evt.id,
                    slug=evt.slug,
                    title=evt.title,
                    event_date=evt.event_date,
                    event_end_date=evt.event_end_date,
                    location=evt.location,
                    status=evt.status,
                    cover_image_url=file_service.build_media_url(evt.cover_image_url),
                ),
                tariff=UserEventTariffNested(
                    id=tariff.id,
                    name=tariff.name,
                    price=float(tariff.price),
                    member_price=float(tariff.member_price),
                    applied_price=float(reg.applied_price),
                    is_member_price=reg.is_member_price,
                ),
                payment=payment_model,
            )
        )

    return {"data": items, "total": total, "limit": limit, "offset": offset}
