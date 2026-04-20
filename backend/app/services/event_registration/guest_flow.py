"""Guest email verification and confirmation."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import EventRegistrationStatus, EventStatus, PaymentStatus
from app.core.exceptions import AppValidationError, ConflictError, NotFoundError
from app.core.logging_privacy import mask_email_for_log
from app.models.events import Event, EventRegistration, EventTariff
from app.models.subscriptions import Payment
from app.schemas.event_registration import (
    ConfirmGuestRegistrationRequest,
    RegisterForEventRequest,
    RegisterForEventResponse,
)
from app.services.event_registration import constants as reg_constants
from app.services.event_registration import payments as reg_payments
from app.services.event_registration import tokens as reg_tokens
from app.services.event_registration.member_flow import reuse_registration
from app.services.event_registration.member_queries import is_association_member
from app.services.event_registration.runtime import EventRegistrationRuntime

logger = structlog.get_logger(__name__)


async def send_verification_code(
    rt: EventRegistrationRuntime,
    event: Event,
    body: RegisterForEventRequest,
    existing_user_id: UUID | None = None,
) -> RegisterForEventResponse:
    email = body.guest_email
    assert email is not None

    send_count_key = f"event_reg_send_count:{email}"
    send_count = int(await rt.redis.get(send_count_key) or 0)
    if send_count >= reg_constants.MAX_SENDS:
        raise AppValidationError(
            "Too many verification codes sent. Please try again later."
        )

    code = f"{secrets.randbelow(1_000_000):06d}"

    verify_key = f"event_reg_verify:{email}"
    payload = json.dumps({
        "code": code,
        "event_id": str(event.id),
        "tariff_id": str(body.tariff_id),
        "existing_user_id": str(existing_user_id) if existing_user_id else None,
    })
    await rt.redis.set(verify_key, payload, ex=reg_constants.VERIFY_TTL)

    await rt.redis.incr(send_count_key)
    await rt.redis.expire(send_count_key, reg_constants.VERIFY_TTL)

    from app.tasks.email_tasks import send_event_verification_code

    await send_event_verification_code.kiq(email, code, event.title)

    logger.info(
        "verification_code_sent",
        email_masked=mask_email_for_log(email),
        event_id=str(event.id),
    )

    action = "verify_existing" if existing_user_id else "verify_new_email"
    return RegisterForEventResponse(
        action=action,
        masked_email=reg_constants.mask_email(email),
    )


async def create_guest_account(
    db: AsyncSession, email: str, event_title: str
) -> UUID:
    from app.core.security import hash_password
    from app.models.users import Role, User, UserRoleAssignment

    email = (email or "").strip().lower()
    existing = (
        await db.execute(select(User).where(func.lower(User.email) == email))
    ).scalar_one_or_none()
    if existing:
        return existing.id

    temp_password = secrets.token_urlsafe(12)
    user = User(
        email=email,
        password_hash=hash_password(temp_password),
    )
    db.add(user)
    await db.flush()

    role = (
        await db.execute(select(Role).where(Role.name == "user"))
    ).scalar_one_or_none()
    if role:
        db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
        await db.flush()

    from app.tasks.email_tasks import send_guest_account_created

    await send_guest_account_created.kiq(
        email, temp_password, event_title, settings.FRONTEND_URL
    )

    logger.info(
        "guest_account_created",
        email_masked=mask_email_for_log(email),
        user_id=str(user.id),
    )
    return user.id


async def confirm_guest_registration(
    rt: EventRegistrationRuntime,
    event_id: UUID,
    body: ConfirmGuestRegistrationRequest,
) -> RegisterForEventResponse:
    db = rt.db
    verify_key = f"event_reg_verify:{body.email}"
    attempts_key = f"event_reg_attempts:{body.email}"

    attempts = int(await rt.redis.get(attempts_key) or 0)
    if attempts >= reg_constants.MAX_ATTEMPTS:
        raise AppValidationError(
            "Too many verification attempts. Please request a new code."
        )

    stored_raw = await rt.redis.get(verify_key)
    if not stored_raw:
        raise AppValidationError(
            "Verification code expired or not found. Please start over."
        )

    stored = json.loads(stored_raw)
    if body.code != stored["code"]:
        await rt.redis.incr(attempts_key)
        await rt.redis.expire(attempts_key, reg_constants.VERIFY_TTL)
        remaining = reg_constants.MAX_ATTEMPTS - attempts - 1
        raise AppValidationError(
            f"Invalid verification code. {remaining} attempt(s) remaining."
        )

    if str(event_id) != stored["event_id"]:
        raise AppValidationError("Event mismatch with verification session.")

    tariff = await db.get(EventTariff, body.tariff_id)
    if not tariff or tariff.event_id != event_id:
        raise NotFoundError("Tariff not found for this event")
    if not tariff.is_active:
        raise AppValidationError("This tariff is no longer available")

    event = await db.get(Event, event_id)
    if not event:
        raise NotFoundError("Event not found")
    if event.status not in (EventStatus.UPCOMING, EventStatus.ONGOING):
        raise AppValidationError("Registration is closed for this event")

    if tariff.seats_limit is not None and tariff.seats_taken >= tariff.seats_limit:
        raise AppValidationError("No seats available for this tariff")

    existing_user_id_str = stored.get("existing_user_id")
    if existing_user_id_str:
        user_id = UUID(existing_user_id_str)
    else:
        user_id = await create_guest_account(db, body.email, event.title)

    await rt.redis.delete(verify_key, attempts_key)

    existing_reg = (
        await db.execute(
            select(EventRegistration)
            .where(
                EventRegistration.user_id == user_id,
                EventRegistration.event_id == event_id,
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
            reuse_body = RegisterForEventRequest(
                tariff_id=body.tariff_id,
                idempotency_key=body.idempotency_key,
                guest_full_name=body.guest_full_name,
                guest_email=body.email,
                guest_workplace=body.guest_workplace,
                guest_specialization=body.guest_specialization,
                fiscal_email=body.fiscal_email,
            )
            return await reuse_registration(
                rt,
                event,
                tariff,
                existing_reg,
                user_id,
                reuse_body,
                increment_seats=True,
                include_tokens=True,
            )

        if existing_reg.status == EventRegistrationStatus.PENDING:
            reuse_body = RegisterForEventRequest(
                tariff_id=body.tariff_id,
                idempotency_key=body.idempotency_key,
                guest_full_name=body.guest_full_name,
                guest_email=body.email,
                guest_workplace=body.guest_workplace,
                guest_specialization=body.guest_specialization,
                fiscal_email=body.fiscal_email,
            )
            return await reuse_registration(
                rt,
                event,
                tariff,
                existing_reg,
                user_id,
                reuse_body,
                increment_seats=False,
                include_tokens=True,
            )

    is_member = await is_association_member(db, user_id)
    applied_price = float(tariff.member_price if is_member else tariff.price)

    reg = EventRegistration(
        user_id=user_id,
        event_id=event_id,
        event_tariff_id=tariff.id,
        applied_price=applied_price,
        is_member_price=is_member,
        status=EventRegistrationStatus.PENDING,
        guest_full_name=body.guest_full_name,
        guest_email=body.email,
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
        body.email,
        body.fiscal_email,
    )

    access_token, refresh_token = await reg_tokens.issue_registration_tokens(
        db, rt.redis, user_id
    )

    await db.commit()

    return RegisterForEventResponse(
        registration_id=reg.id,
        payment_url=payment_url,
        applied_price=applied_price,
        is_member_price=is_member,
        access_token=access_token,
        refresh_token=refresh_token,
    )
