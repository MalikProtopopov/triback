"""Public (no-auth) certificate verification endpoint."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.models.certificate_settings import CertificateSettings
from app.models.certificates import Certificate
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Subscription
from app.schemas.certificates import CertificateVerifyResponse
from app.services.membership_arrears_service import (
    arrears_block_enabled,
    load_site_settings_dict,
    user_has_open_arrears,
)

router = APIRouter(prefix="/public/certificates")


@router.get(
    "/verify/{certificate_number}",
    response_model=CertificateVerifyResponse,
    summary="Проверка сертификата по номеру",
    responses={404: {"description": "Сертификат не найден"}},
)
async def verify_certificate(
    certificate_number: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Public endpoint for QR code verification. No authentication required.

    Returns certificate details and validity status. Used by the client
    frontend to render the ``/certificates/verify/{number}`` page.
    """
    result = await db.execute(
        select(Certificate).where(Certificate.certificate_number == certificate_number)
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise NotFoundError("Сертификат не найден")

    profile_result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.id == cert.doctor_profile_id)
    )
    profile = profile_result.scalar_one_or_none()

    doctor_full_name = ""
    doctor_slug = ""
    if profile:
        doctor_full_name = " ".join(
            filter(None, [profile.last_name, profile.first_name, profile.middle_name])
        )
        doctor_slug = profile.slug or ""

    now = datetime.now(UTC)
    is_valid = cert.is_active

    if is_valid:
        sub_result = await db.execute(
            select(Subscription.id).where(
                Subscription.user_id == cert.user_id,
                Subscription.status == "active",
                Subscription.ends_at > now,
            ).limit(1)
        )
        has_active_sub = sub_result.scalar_one_or_none() is not None
        if not has_active_sub:
            is_valid = False

    if is_valid:
        settings_data = await load_site_settings_dict(db)
        if arrears_block_enabled(settings_data):
            if await user_has_open_arrears(db, cert.user_id):
                is_valid = False

    invalid_reason = None
    if not is_valid:
        invalid_reason = "Врач более не является членом ассоциации"

    settings_result = await db.execute(
        select(CertificateSettings).where(CertificateSettings.id == 1)
    )
    settings = settings_result.scalar_one_or_none()

    return {
        "certificate_number": cert.certificate_number,
        "doctor_full_name": doctor_full_name,
        "doctor_slug": doctor_slug,
        "certificate_type": cert.certificate_type,
        "year": cert.year,
        "issued_at": cert.generated_at.isoformat(),
        "is_valid": is_valid,
        "invalid_reason": invalid_reason,
        "organization_name": settings.organization_full_name if settings else None,
        "president_full_name": settings.president_full_name if settings else None,
        "president_title": settings.president_title if settings else None,
    }
