"""Background tasks for certificate generation."""

from uuid import UUID

import structlog

from app.tasks import broker

logger = structlog.get_logger(__name__)


@broker.task(retry_on_error=True, max_retries=3)
async def generate_member_certificate_task(doctor_profile_id: str, year: int) -> str:
    """Generate (or regenerate) a membership certificate PDF in the background.

    Retries up to 3 times on failure. Logs errors and notifies admins via
    Telegram on final failure.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.certificate_service import CertificateService

    dp_id = UUID(doctor_profile_id)

    try:
        async with AsyncSessionLocal() as db:
            svc = CertificateService(db)
            cert = await svc.generate_membership_certificate(dp_id, year)
            logger.info(
                "certificate_task_ok",
                doctor_profile_id=doctor_profile_id,
                cert_id=str(cert.id),
                number=cert.certificate_number,
            )
            return str(cert.id)
    except Exception:
        logger.exception(
            "certificate_task_failed",
            doctor_profile_id=doctor_profile_id,
            year=year,
        )
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.telegram_integration_service import get_telegram_config
            from app.services.telegram_service import TelegramService

            async with AsyncSessionLocal() as db:
                config = await get_telegram_config(db)
                if config:
                    tg = TelegramService(bot_token=config[0], owner_chat_id=config[1])
                else:
                    tg = TelegramService()
                if tg._token and tg._owner_chat_id:
                    await tg.send_message(
                        int(tg._owner_chat_id),
                        f"Ошибка генерации сертификата:\n"
                        f"doctor_profile_id={doctor_profile_id}\nyear={year}",
                    )
        except Exception:
            pass
        raise
