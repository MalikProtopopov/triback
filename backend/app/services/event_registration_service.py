"""Event registration service — register, pay, manage seats."""

from __future__ import annotations

import secrets
from decimal import Decimal
from uuid import UUID

import structlog
from redis.asyncio import Redis
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppValidationError, ConflictError, NotFoundError
from app.models.events import Event, EventRegistration, EventTariff
from app.models.subscriptions import Payment, Subscription
from app.schemas.event_registration import RegisterForEventRequest, RegisterForEventResponse
from app.services.payment_service import YooKassaClient

logger = structlog.get_logger(__name__)


class EventRegistrationService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:  # type: ignore[type-arg]
        self.db = db
        self.redis = redis
        self.yookassa = YooKassaClient()

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
        if event.status not in ("upcoming", "ongoing"):
            raise AppValidationError("Registration is closed for this event")

        if tariff.seats_limit is not None and tariff.seats_taken >= tariff.seats_limit:
            raise AppValidationError("No seats available for this tariff")

        actual_user_id = user_id
        user_email: str | None = None

        if actual_user_id:
            from app.models.users import User

            user = await self.db.get(User, actual_user_id)
            if user:
                user_email = user.email
        else:
            actual_user_id = await self._ensure_guest_account(body)
            user_email = body.guest_email

        has_active_sub = await self._has_active_subscription(actual_user_id)
        if has_active_sub:
            applied_price = float(tariff.member_price)
            is_member_price = True
        else:
            applied_price = float(tariff.price)
            is_member_price = False

        reg = EventRegistration(
            user_id=actual_user_id,
            event_id=event_id,
            event_tariff_id=tariff.id,
            applied_price=applied_price,
            is_member_price=is_member_price,
            status="pending",
            guest_full_name=body.guest_full_name,
            guest_email=body.guest_email,
            guest_workplace=body.guest_workplace,
            guest_specialization=body.guest_specialization,
            fiscal_email=body.fiscal_email,
        )
        self.db.add(reg)
        await self.db.flush()

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
            user_id=actual_user_id,
            amount=applied_price,
            product_type="event",
            payment_provider="yookassa",
            status="pending",
            event_registration_id=reg.id,
            idempotency_key=body.idempotency_key,
            description=f"{event.title} — {tariff.name}",
        )
        self.db.add(payment)
        await self.db.flush()

        payment_url: str | None = None
        if applied_price > 0:
            receipt_email = body.fiscal_email or user_email or body.guest_email or ""
            from app.services.subscription_service import _build_receipt

            receipt = _build_receipt(
                email=receipt_email,
                description=f"{event.title} — {tariff.name}",
                amount=Decimal(str(applied_price)),
            )

            return_url = f"{settings.YOOKASSA_RETURN_URL}?payment_id={payment.id}"
            yookassa_resp = await self.yookassa.create_payment(
                amount=Decimal(str(applied_price)),
                description=payment.description or "",
                metadata={
                    "internal_payment_id": str(payment.id),
                    "product_type": "event",
                    "user_id": str(actual_user_id),
                    "event_id": str(event_id),
                    "registration_id": str(reg.id),
                },
                idempotency_key=body.idempotency_key,
                return_url=return_url,
                receipt=receipt,
            )
            payment.external_payment_id = yookassa_resp.get("id")
            confirmation = yookassa_resp.get("confirmation", {})
            payment.external_payment_url = confirmation.get("confirmation_url")
            payment_url = payment.external_payment_url
        else:
            payment.status = "succeeded"  # type: ignore[assignment]
            reg.status = "confirmed"  # type: ignore[assignment]

        await self.db.commit()

        return RegisterForEventResponse(
            registration_id=reg.id,
            payment_url=payment_url,
            applied_price=applied_price,
            is_member_price=is_member_price,
        )

    async def _has_active_subscription(self, user_id: UUID) -> bool:
        result = await self.db.execute(
            select(Subscription.id).where(
                Subscription.user_id == user_id,
                Subscription.status == "active",
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _ensure_guest_account(self, body: RegisterForEventRequest) -> UUID:
        """S21: Create a temporary account for unauthenticated event registration."""
        if not body.guest_email:
            raise AppValidationError("Email is required for guest registration")

        from app.core.security import hash_password
        from app.models.users import Role, User, UserRoleAssignment

        existing = (
            await self.db.execute(
                select(User).where(User.email == body.guest_email)
            )
        ).scalar_one_or_none()
        if existing:
            return existing.id

        temp_password = secrets.token_urlsafe(12)
        user = User(
            email=body.guest_email,
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

        from app.tasks.email_tasks import send_custom_email

        await send_custom_email.kiq(
            body.guest_email,
            "Ваш аккаунт на сайте Ассоциации трихологов",
            f"Для вас создан аккаунт.\nВременный пароль: {temp_password}\n"
            "Рекомендуем сменить пароль после входа.",
        )

        logger.info("guest_account_created", email=body.guest_email, user_id=str(user.id))
        return user.id
