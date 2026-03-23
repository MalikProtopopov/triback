"""Certificate service — list, download, generate PDF with QR, stamp, signature."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.enums import DoctorStatus, SubscriptionStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.certificates import Certificate
from app.models.events import Event
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Subscription
from app.services.certificates import certificate_numbering, certificate_storage
from app.services.certificates.certificate_pdf import _generate_member_pdf

logger = structlog.get_logger(__name__)


class CertificateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _has_active_subscription(self, user_id: str) -> bool:
        result = await self.db.execute(
            select(Subscription.id).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                or_(
                    Subscription.ends_at.is_(None),
                    Subscription.ends_at > func.now(),
                ),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _get_active_profile(self, user_id: str) -> DoctorProfile:
        result = await self.db.execute(
            select(DoctorProfile).where(
                DoctorProfile.user_id == user_id,
                DoctorProfile.status == DoctorStatus.ACTIVE,
            )
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise ForbiddenError("Certificates available only for active doctors")
        return profile

    async def list_certificates(self, user_id: str) -> list[dict[str, Any]]:
        await self._get_active_profile(user_id)

        has_active_sub = await self._has_active_subscription(user_id)

        result = await self.db.execute(
            select(Certificate).where(
                Certificate.user_id == user_id,
                Certificate.is_active.is_(True),
            ).order_by(Certificate.generated_at.desc())
        )
        certs = result.scalars().all()
        certs = [
            c for c in certs
            if c.certificate_type != "member" or has_active_sub
        ]

        event_ids = list({c.event_id for c in certs if c.event_id})
        event_map: dict[UUID, Event] = {}
        if event_ids:
            ev_q = await self.db.execute(
                select(Event).where(Event.id.in_(event_ids))
            )
            for event_row in ev_q.scalars().all():
                event_map[event_row.id] = event_row

        qr_base = app_settings.CERTIFICATE_QR_BASE_URL or app_settings.FRONTEND_URL

        items: list[dict[str, Any]] = []
        for cert in certs:
            event_nested = None
            if cert.event_id:
                evt = event_map.get(cert.event_id)
                if evt:
                    event_nested = {"id": str(evt.id), "title": evt.title}

            api_base = (app_settings.PUBLIC_API_URL or "").rstrip("/")
            download_url = (
                f"{api_base}/api/v1/certificates/{cert.id}/download"
                if api_base
                else f"/api/v1/certificates/{cert.id}/download"
            )
            verify_url = f"{qr_base.rstrip('/')}/certificates/verify/{cert.certificate_number}"

            items.append({
                "id": str(cert.id),
                "certificate_type": cert.certificate_type,
                "year": cert.year,
                "event": event_nested,
                "certificate_number": cert.certificate_number,
                "is_active": cert.is_active,
                "generated_at": cert.generated_at.isoformat(),
                "download_url": download_url,
                "verify_url": verify_url,
            })

        return items

    async def get_certificate_pdf_bytes(
        self, user_id: str, cert_id: UUID
    ) -> tuple[bytes, str]:
        """Fetch the PDF from S3 and return (pdf_bytes, filename)."""
        await self._get_active_profile(user_id)

        cert = await self.db.get(Certificate, cert_id)
        if not cert or str(cert.user_id) != user_id:
            raise NotFoundError("Certificate not found")
        if not cert.is_active:
            raise ForbiddenError("Certificate is no longer active")
        if not cert.file_url:
            raise NotFoundError("Certificate file not found in storage")

        data = await certificate_storage.download_s3_bytes(cert.file_url)
        if not data:
            raise NotFoundError("Certificate file not found in storage")
        return data, f"{cert.certificate_number}.pdf"

    async def generate_membership_certificate(
        self,
        doctor_profile_id: UUID,
        year: int | None = None,
    ) -> Certificate:
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.id == doctor_profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        cert_settings = await certificate_numbering.get_cert_settings(self.db)
        cert_year = year or datetime.now(UTC).year

        full_name = " ".join(
            filter(None, [profile.last_name, profile.first_name, profile.middle_name])
        )

        existing_result = await self.db.execute(
            select(Certificate).where(
                Certificate.doctor_profile_id == doctor_profile_id,
                Certificate.certificate_type == "member",
                Certificate.year == cert_year,
            )
        )
        existing_cert = existing_result.scalar_one_or_none()

        if existing_cert:
            cert_number = existing_cert.certificate_number
        else:
            cert_number = await certificate_numbering.next_certificate_number(
                self.db, cert_settings.certificate_number_prefix, cert_year
            )

        logo_bytes = await certificate_storage.download_s3_bytes(
            cert_settings.logo_s3_key
        )
        stamp_bytes = await certificate_storage.download_s3_bytes(
            cert_settings.stamp_s3_key
        )
        signature_bytes = await certificate_storage.download_s3_bytes(
            cert_settings.signature_s3_key
        )
        background_bytes = await certificate_storage.download_s3_bytes(
            cert_settings.background_s3_key
        )

        body_text = (cert_settings.certificate_member_text or "").format(
            full_name=full_name, year=cert_year
        )
        validity_text = (cert_settings.validity_text_template or "").format(
            year=cert_year
        )

        qr_base = app_settings.CERTIFICATE_QR_BASE_URL or app_settings.FRONTEND_URL
        qr_url = f"{qr_base.rstrip('/')}/certificates/verify/{cert_number}"

        pdf_bytes = _generate_member_pdf(
            full_name=full_name,
            cert_number=cert_number,
            year=cert_year,
            body_text=body_text,
            validity_text=validity_text,
            president_name=cert_settings.president_full_name or "",
            president_title=cert_settings.president_title or "",
            qr_url=qr_url,
            logo_bytes=logo_bytes,
            stamp_bytes=stamp_bytes,
            signature_bytes=signature_bytes,
            background_bytes=background_bytes,
        )

        s3_key = f"certificates/{doctor_profile_id}/{cert_number}.pdf"
        await certificate_storage.put_certificate_pdf(s3_key, pdf_bytes)

        if existing_cert:
            if existing_cert.file_url != s3_key:
                await certificate_storage.delete_stored_file(existing_cert.file_url)
            existing_cert.file_url = s3_key
            existing_cert.is_active = True
            existing_cert.generated_at = datetime.now(UTC)
            await self.db.commit()
            await self.db.refresh(existing_cert)
            logger.info(
                "certificate_regenerated",
                cert_id=str(existing_cert.id),
                number=cert_number,
            )
            return existing_cert

        cert = Certificate(
            user_id=profile.user_id,
            doctor_profile_id=doctor_profile_id,
            certificate_type="member",
            year=cert_year,
            certificate_number=cert_number,
            file_url=s3_key,
            is_active=True,
        )
        self.db.add(cert)
        await self.db.commit()
        await self.db.refresh(cert)

        logger.info("certificate_generated", cert_id=str(cert.id), number=cert_number)
        return cert
