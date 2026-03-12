"""Email tasks — TaskIQ-decorated stubs (replace bodies with real SMTP later)."""

import structlog

from app.tasks import broker

logger = structlog.get_logger(__name__)


@broker.task  # type: ignore[misc]
async def send_verification_email(email: str, token: str) -> None:
    logger.info("send_verification_email", email=email, token=token)


@broker.task  # type: ignore[misc]
async def send_password_reset_email(email: str, token: str) -> None:
    logger.info("send_password_reset_email", email=email, token=token)


@broker.task  # type: ignore[misc]
async def send_email_change_confirmation(email: str, token: str) -> None:
    logger.info("send_email_change_confirmation", email=email, token=token)


@broker.task  # type: ignore[misc]
async def send_moderation_result_notification(
    email: str, status: str, comment: str | None = None
) -> None:
    logger.info(
        "send_moderation_result_notification", email=email, status=status, comment=comment
    )


@broker.task  # type: ignore[misc]
async def send_draft_result_notification(
    email: str, status: str, rejection_reason: str | None = None
) -> None:
    logger.info(
        "send_draft_result_notification", email=email, status=status, reason=rejection_reason
    )


@broker.task  # type: ignore[misc]
async def send_reminder_notification(email: str, message: str | None = None) -> None:
    logger.info("send_reminder_notification", email=email, message=message)


@broker.task  # type: ignore[misc]
async def send_custom_email(email: str, subject: str, body: str) -> None:
    logger.info("send_custom_email", email=email, subject=subject)


@broker.task  # type: ignore[misc]
async def send_payment_succeeded_notification(
    email: str, amount: float, product_type: str, receipt_url: str | None = None
) -> None:
    logger.info(
        "send_payment_succeeded_notification",
        email=email,
        amount=amount,
        product_type=product_type,
        receipt_url=receipt_url,
    )


@broker.task  # type: ignore[misc]
async def send_payment_failed_notification(email: str) -> None:
    logger.info("send_payment_failed_notification", email=email)


@broker.task  # type: ignore[misc]
async def send_event_verification_code(
    email: str, code: str, event_title: str
) -> None:
    logger.info("send_event_verification_code", email=email, event=event_title)


@broker.task  # type: ignore[misc]
async def send_guest_account_created(
    email: str, temp_password: str, event_title: str, frontend_url: str
) -> None:
    logger.info("send_guest_account_created", email=email, event=event_title)
