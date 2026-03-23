"""Authenticated registration and reuse of pending/cancelled rows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.enums import EventRegistrationStatus, PaymentStatus
from app.core.exceptions import ConflictError
from app.models.events import Event, EventRegistration, EventTariff
from app.models.subscriptions import Payment
from app.schemas.event_registration import RegisterForEventRequest, RegisterForEventResponse
from app.services.event_registration import payments as reg_payments
from app.services.event_registration import tokens as reg_tokens
from app.services.event_registration.member_queries import is_association_member
from app.services.event_registration.runtime import EventRegistrationRuntime


async def register_authenticated(
    rt: EventRegistrationRuntime,
    event: Event,
    tariff: EventTariff,
    user_id: UUID,
    body: RegisterForEventRequest,
) -> RegisterForEventResponse:
    from app.models.users import User

    db = rt.db
    existing_reg = (
        await db.execute(
            select(EventRegistration)
            .where(
                EventRegistration.user_id == user_id,
                EventRegistration.event_id == event.id,
                EventRegistration.event_tariff_id == tariff.id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if existing_reg:
        if existing_reg.status == EventRegistrationStatus.CONFIRMED:
            raise ConflictError(
                "You have already registered for this event with this tariff"
            )

        if existing_reg.status == EventRegistrationStatus.CANCELLED:
            return await reuse_registration(
                rt, event, tariff, existing_reg, user_id, body, increment_seats=True
            )

        if existing_reg.status == EventRegistrationStatus.PENDING:
            return await reuse_registration(
                rt, event, tariff, existing_reg, user_id, body, increment_seats=False
            )

    user = await db.get(User, user_id)
    user_email = user.email if user else None

    is_member = await is_association_member(db, user_id)
    applied_price = float(tariff.member_price if is_member else tariff.price)
    is_member_price = is_member

    reg = EventRegistration(
        user_id=user_id,
        event_id=event.id,
        event_tariff_id=tariff.id,
        applied_price=applied_price,
        is_member_price=is_member_price,
        status=EventRegistrationStatus.PENDING,
        guest_full_name=body.guest_full_name,
        guest_email=body.guest_email,
        guest_workplace=body.guest_workplace,
        guest_specialization=body.guest_specialization,
        fiscal_email=body.fiscal_email,
    )
    try:
        db.add(reg)
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            "You have already registered for this event with this tariff"
        ) from None

    inc_result = await db.execute(
        update(EventTariff)
        .where(
            EventTariff.id == tariff.id,
            or_(
                EventTariff.seats_limit.is_(None),
                EventTariff.seats_taken < EventTariff.seats_limit,
            ),
        )
        .values(seats_taken=EventTariff.seats_taken + 1)
    )
    if inc_result.rowcount == 0:
        raise ConflictError("No seats available")
    await db.flush()

    payment = Payment(
        user_id=user_id,
        amount=applied_price,
        product_type="event",
        payment_provider=settings.PAYMENT_PROVIDER,
        status=PaymentStatus.PENDING,
        event_registration_id=reg.id,
        idempotency_key=body.idempotency_key,
        description=f"{event.title} — {tariff.name}",
        expires_at=datetime.now(UTC)
        + timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS),
    )
    db.add(payment)
    await db.flush()

    payment_url = await reg_payments.process_event_registration_payment(
        db,
        rt.provider,
        payment,
        event,
        tariff,
        reg,
        applied_price,
        user_email or body.guest_email or "",
        body.fiscal_email,
    )
    await db.commit()

    return RegisterForEventResponse(
        registration_id=reg.id,
        payment_url=payment_url,
        applied_price=applied_price,
        is_member_price=is_member_price,
    )


async def reuse_registration(
    rt: EventRegistrationRuntime,
    event: Event,
    tariff: EventTariff,
    reg: EventRegistration,
    user_id: UUID,
    body: RegisterForEventRequest,
    *,
    increment_seats: bool,
    include_tokens: bool = False,
) -> RegisterForEventResponse:
    """Reuse a CANCELLED or PENDING registration for a new payment."""
    from app.models.users import User

    db = rt.db
    user = await db.get(User, user_id)
    user_email = user.email if user else None

    is_member = await is_association_member(db, user_id)
    applied_price = float(tariff.member_price if is_member else tariff.price)
    is_member_price = is_member

    reg.status = EventRegistrationStatus.PENDING
    reg.applied_price = applied_price
    reg.is_member_price = is_member_price
    reg.guest_full_name = body.guest_full_name
    reg.guest_email = body.guest_email
    reg.guest_workplace = body.guest_workplace
    reg.guest_specialization = body.guest_specialization
    reg.fiscal_email = body.fiscal_email
    await db.flush()

    if increment_seats:
        inc_result = await db.execute(
            update(EventTariff)
            .where(
                EventTariff.id == tariff.id,
                or_(
                    EventTariff.seats_limit.is_(None),
                    EventTariff.seats_taken < EventTariff.seats_limit,
                ),
            )
            .values(seats_taken=EventTariff.seats_taken + 1)
        )
        if inc_result.rowcount == 0:
            raise ConflictError("No seats available")
        await db.flush()

    payment = Payment(
        user_id=user_id,
        amount=applied_price,
        product_type="event",
        payment_provider=settings.PAYMENT_PROVIDER,
        status=PaymentStatus.PENDING,
        event_registration_id=reg.id,
        idempotency_key=body.idempotency_key,
        description=f"{event.title} — {tariff.name}",
        expires_at=datetime.now(UTC)
        + timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS),
    )
    db.add(payment)
    await db.flush()

    payment_url = await reg_payments.process_event_registration_payment(
        db,
        rt.provider,
        payment,
        event,
        tariff,
        reg,
        applied_price,
        user_email or body.guest_email or "",
        body.fiscal_email,
    )
    await db.commit()

    resp = RegisterForEventResponse(
        registration_id=reg.id,
        payment_url=payment_url,
        applied_price=applied_price,
        is_member_price=is_member_price,
    )
    if include_tokens:
        access_token, refresh_token = await reg_tokens.issue_registration_tokens(
            db, rt.redis, user_id
        )
        resp.access_token = access_token
        resp.refresh_token = refresh_token
    return resp
