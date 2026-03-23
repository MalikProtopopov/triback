"""Event registration service — register, pay, manage seats."""

from __future__ import annotations

import json
import random
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import structlog
from redis.asyncio import Redis
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import EventRegistrationStatus, EventStatus, PaymentStatus, SubscriptionStatus
from app.core.exceptions import AppValidationError, ConflictError, NotFoundError
from app.models.events import Event, EventRegistration, EventTariff
from app.models.subscriptions import Payment, Subscription
from app.schemas.event_registration import (
    ConfirmGuestRegistrationRequest,
    RegisterForEventRequest,
    RegisterForEventResponse,
)
from app.services.payment_providers import PaymentItem, get_provider

logger = structlog.get_logger(__name__)

_VERIFY_TTL = 600
_MAX_ATTEMPTS = 5
_MAX_SENDS = 3


def _mask_email(email: str) -> str:
    local, domain = email.split("@", 1)
    masked_local = local if len(local) <= 1 else local[0] + "***"
    return f"{masked_local}@{domain}"


class EventRegistrationService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:  # type: ignore[type-arg]
        self.db = db
        self.redis = redis
        self.provider = get_provider()

    async def register(
        self,
        event_id: UUID,
        user_id: UUID | None,
        body: RegisterForEventRequest,
    ) -> RegisterForEventResponse:
        tariff = await self.db.get(EventTariff, body.tariff_id)
        if not tariff or tariff.event_id != event_id:
            raise NotFoundError("Tariff not found for this event")
        if not tariff.is_active:
            raise AppValidationError("This tariff is no longer available")

        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")
        if event.status not in (EventStatus.UPCOMING, EventStatus.ONGOING):
            raise AppValidationError("Registration is closed for this event")

        if tariff.seats_limit is not None and tariff.seats_taken >= tariff.seats_limit:
            raise AppValidationError("No seats available for this tariff")

        if user_id:
            return await self._register_authenticated(event, tariff, user_id, body)

        if not body.guest_email:
            raise AppValidationError("Email is required for guest registration")

        from app.models.users import User

        existing = (
            await self.db.execute(select(User).where(User.email == body.guest_email))
        ).scalar_one_or_none()

        if existing:
            return await self._send_verification_code(
                event, body, existing_user_id=existing.id,
            )

        return await self._send_verification_code(event, body)

    async def confirm_guest_registration(
        self,
        event_id: UUID,
        body: ConfirmGuestRegistrationRequest,
    ) -> RegisterForEventResponse:
        verify_key = f"event_reg_verify:{body.email}"
        attempts_key = f"event_reg_attempts:{body.email}"

        attempts = int(await self.redis.get(attempts_key) or 0)
        if attempts >= _MAX_ATTEMPTS:
            raise AppValidationError(
                "Too many verification attempts. Please request a new code."
            )

        stored_raw = await self.redis.get(verify_key)
        if not stored_raw:
            raise AppValidationError(
                "Verification code expired or not found. Please start over."
            )

        stored = json.loads(stored_raw)
        if body.code != stored["code"]:
            await self.redis.incr(attempts_key)
            await self.redis.expire(attempts_key, _VERIFY_TTL)
            remaining = _MAX_ATTEMPTS - attempts - 1
            raise AppValidationError(
                f"Invalid verification code. {remaining} attempt(s) remaining."
            )

        if str(event_id) != stored["event_id"]:
            raise AppValidationError("Event mismatch with verification session.")

        tariff = await self.db.get(EventTariff, body.tariff_id)
        if not tariff or tariff.event_id != event_id:
            raise NotFoundError("Tariff not found for this event")
        if not tariff.is_active:
            raise AppValidationError("This tariff is no longer available")

        event = await self.db.get(Event, event_id)
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
            user_id = await self._create_guest_account(body.email, event.title)

        await self.redis.delete(verify_key, attempts_key)

        existing_reg = (
            await self.db.execute(
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
            raise ConflictError("You have already registered for this event with this tariff")

        is_member = await self._is_association_member(user_id)
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
            self.db.add(reg)
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("You have already registered for this event with this tariff")

        inc_result = await self.db.execute(
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
        await self.db.flush()

        payment = Payment(
            user_id=user_id,
            amount=applied_price,
            product_type="event",
            payment_provider=settings.PAYMENT_PROVIDER,
            status=PaymentStatus.PENDING,
            event_registration_id=reg.id,
            idempotency_key=body.idempotency_key,
            description=f"{event.title} — {tariff.name}",
            expires_at=datetime.now(UTC) + timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS),
        )
        self.db.add(payment)
        await self.db.flush()

        payment_url = await self._process_payment(
            payment, event, tariff, reg, applied_price, body.email, body.fiscal_email
        )

        access_token, refresh_token = await self._issue_tokens(user_id)

        await self.db.commit()

        return RegisterForEventResponse(
            registration_id=reg.id,
            payment_url=payment_url,
            applied_price=applied_price,
            is_member_price=is_member,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    # -- private helpers -------------------------------------------------------

    async def _register_authenticated(
        self,
        event: Event,
        tariff: EventTariff,
        user_id: UUID,
        body: RegisterForEventRequest,
    ) -> RegisterForEventResponse:
        from app.models.users import User

        existing_reg = (
            await self.db.execute(
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
            raise ConflictError("You have already registered for this event with this tariff")

        user = await self.db.get(User, user_id)
        user_email = user.email if user else None

        is_member = await self._is_association_member(user_id)
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
            self.db.add(reg)
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("You have already registered for this event with this tariff")

        inc_result = await self.db.execute(
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
        await self.db.flush()

        payment = Payment(
            user_id=user_id,
            amount=applied_price,
            product_type="event",
            payment_provider=settings.PAYMENT_PROVIDER,
            status=PaymentStatus.PENDING,
            event_registration_id=reg.id,
            idempotency_key=body.idempotency_key,
            description=f"{event.title} — {tariff.name}",
            expires_at=datetime.now(UTC) + timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS),
        )
        self.db.add(payment)
        await self.db.flush()

        payment_url = await self._process_payment(
            payment,
            event,
            tariff,
            reg,
            applied_price,
            user_email or body.guest_email or "",
            body.fiscal_email,
        )
        await self.db.commit()

        return RegisterForEventResponse(
            registration_id=reg.id,
            payment_url=payment_url,
            applied_price=applied_price,
            is_member_price=is_member_price,
        )

    async def _process_payment(
        self,
        payment: Payment,
        event: Event,
        tariff: EventTariff,
        reg: EventRegistration,
        applied_price: float,
        receipt_email: str,
        fiscal_email: str | None,
    ) -> str | None:
        if applied_price <= 0:
            payment.status = PaymentStatus.SUCCEEDED  # type: ignore[assignment]
            reg.status = EventRegistrationStatus.CONFIRMED  # type: ignore[assignment]
            return None

        email_for_receipt = fiscal_email or receipt_email
        description = f"{event.title} — {tariff.name}"
        items = [PaymentItem(name=description, price=Decimal(str(applied_price)))]

        if settings.PAYMENT_PROVIDER == "moneta":
            return_url = settings.MONETA_RETURN_URL or settings.MONETA_SUCCESS_URL
        else:
            return_url = settings.YOOKASSA_RETURN_URL
        result = await self.provider.create_payment(
            transaction_id=str(payment.id),
            items=items,
            total_amount=Decimal(str(applied_price)),
            description=payment.description or description,
            customer_email=email_for_receipt,
            return_url=return_url,
            idempotency_key=payment.idempotency_key or "",
            metadata={
                "product_type": "event",
                "user_id": str(payment.user_id),
                "event_id": str(event.id),
                "registration_id": str(reg.id),
            },
        )
        payment.external_payment_id = result.external_id
        payment.external_payment_url = result.payment_url
        if settings.PAYMENT_PROVIDER == "moneta":
            payment.moneta_operation_id = result.external_id
        return payment.external_payment_url

    async def _send_verification_code(
        self,
        event: Event,
        body: RegisterForEventRequest,
        existing_user_id: UUID | None = None,
    ) -> RegisterForEventResponse:
        email = body.guest_email
        assert email is not None

        send_count_key = f"event_reg_send_count:{email}"
        send_count = int(await self.redis.get(send_count_key) or 0)
        if send_count >= _MAX_SENDS:
            raise AppValidationError(
                "Too many verification codes sent. Please try again later."
            )

        code = f"{random.randint(0, 999999):06d}"  # noqa: S311

        verify_key = f"event_reg_verify:{email}"
        payload = json.dumps({
            "code": code,
            "event_id": str(event.id),
            "tariff_id": str(body.tariff_id),
            "existing_user_id": str(existing_user_id) if existing_user_id else None,
        })
        await self.redis.set(verify_key, payload, ex=_VERIFY_TTL)

        await self.redis.incr(send_count_key)
        await self.redis.expire(send_count_key, _VERIFY_TTL)

        from app.tasks.email_tasks import send_event_verification_code

        await send_event_verification_code.kiq(email, code, event.title)

        logger.info("verification_code_sent", email=email, event_id=str(event.id))

        action = "verify_existing" if existing_user_id else "verify_new_email"
        return RegisterForEventResponse(
            action=action,
            masked_email=_mask_email(email),
        )

    async def _create_guest_account(self, email: str, event_title: str) -> UUID:
        from app.core.security import hash_password
        from app.models.users import Role, User, UserRoleAssignment

        existing = (
            await self.db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing:
            return existing.id

        temp_password = secrets.token_urlsafe(12)
        user = User(
            email=email,
            password_hash=hash_password(temp_password),
        )
        self.db.add(user)
        await self.db.flush()

        role = (
            await self.db.execute(select(Role).where(Role.name == "user"))
        ).scalar_one_or_none()
        if role:
            self.db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
            await self.db.flush()

        from app.tasks.email_tasks import send_guest_account_created

        await send_guest_account_created.kiq(
            email, temp_password, event_title, settings.FRONTEND_URL
        )

        logger.info("guest_account_created", email=email, user_id=str(user.id))
        return user.id

    async def _is_association_member(self, user_id: UUID) -> bool:
        """True only if user is an ACTIVE doctor with an active subscription."""
        from sqlalchemy import func

        from app.core.enums import DoctorStatus
        from app.models.profiles import DoctorProfile

        dp = await self.db.execute(
            select(DoctorProfile.id).where(
                DoctorProfile.user_id == user_id,
                DoctorProfile.status == DoctorStatus.ACTIVE,
            ).limit(1)
        )
        if not dp.scalar_one_or_none():
            return False

        sub = await self.db.execute(
            select(Subscription.id).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                or_(
                    Subscription.ends_at.is_(None),
                    Subscription.ends_at > func.now(),
                ),
            ).limit(1)
        )
        return sub.scalar_one_or_none() is not None

    async def _issue_tokens(self, user_id: UUID) -> tuple[str, str]:
        """Generate JWT access + refresh tokens and store refresh in Redis."""
        from app.core.security import create_access_token, create_refresh_token, generate_token
        from app.models.users import Role, UserRoleAssignment

        role_result = await self.db.execute(
            select(Role)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(UserRoleAssignment.user_id == user_id)
        )
        role_names = [r.name for r in role_result.scalars().all()]
        priority = ("admin", "manager", "accountant", "doctor", "user")
        role_name = next((r for r in priority if r in role_names), "user")

        jti = generate_token(16)
        access_token = create_access_token(user_id, role_name)
        refresh_token = create_refresh_token(user_id, jti)

        refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
        await self.redis.set(f"refresh:{user_id}:{jti}", "1", ex=refresh_ttl)

        return access_token, refresh_token
