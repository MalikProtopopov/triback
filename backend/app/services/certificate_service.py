"""Certificate service — list, download (presigned URL), generate PDF stub."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from uuid import UUID

import structlog
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DoctorStatus, SubscriptionStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.certificates import Certificate
from app.models.events import Event
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Subscription
from app.services import file_service

logger = structlog.get_logger(__name__)


class CertificateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _has_active_subscription(self, user_id: str) -> bool:
        from sqlalchemy import func, or_

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

    async def list_certificates(self, user_id: str) -> list[dict]:
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
            for evt in ev_q.scalars().all():
                event_map[evt.id] = evt

        items: list[dict] = []
        for cert in certs:
            event_nested = None
            if cert.event_id:
                evt = event_map.get(cert.event_id)
                if evt:
                    event_nested = {"id": str(evt.id), "title": evt.title}

            download_url = await file_service.get_presigned_url(cert.file_url, ttl=600)

            items.append({
                "id": str(cert.id),
                "certificate_type": cert.certificate_type,
                "year": cert.year,
                "event": event_nested,
                "certificate_number": cert.certificate_number,
                "is_active": cert.is_active,
                "generated_at": cert.generated_at.isoformat(),
                "download_url": download_url,
            })

        return items

    async def download_certificate(self, user_id: str, cert_id: UUID) -> str:
        """Return presigned URL for a specific certificate. Verify ownership."""
        await self._get_active_profile(user_id)

        cert = await self.db.get(Certificate, cert_id)
        if not cert or str(cert.user_id) != user_id or not cert.is_active:
            raise NotFoundError("Certificate not found")

        return await file_service.get_presigned_url(cert.file_url, ttl=600)

    async def generate_membership_certificate(
        self,
        doctor_profile_id: UUID,
        year: int | None = None,
    ) -> Certificate:
        """Generate a stub PDF membership certificate, upload to S3, create DB record."""
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.id == doctor_profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        cert_year = year or datetime.now(UTC).year
        cert_number = f"MBR-{cert_year}-{uuid.uuid4().hex[:8].upper()}"

        pdf_bytes = _generate_stub_pdf(
            f"{profile.last_name} {profile.first_name}",
            cert_number,
            cert_year,
        )

        s3_key = f"certificates/{doctor_profile_id}/{uuid.uuid4()}.pdf"
        session = file_service._get_s3_session()
        async with session.client(**file_service._s3_client_kwargs()) as s3:
            await s3.put_object(
                Bucket=file_service.settings.S3_BUCKET,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType="application/pdf",
            )

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

        logger.info("certificate_generated", cert_id=str(cert.id), number=cert_number)
        return cert


def _register_cyrillic_fonts() -> bool:
    """Try to register DejaVuSans for Cyrillic text. Returns True if available."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
    ]
    bold_paths = [p.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf") for p in font_paths]

    import os

    for path in font_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("DejaVuSans", path))
            for bp in bold_paths:
                if os.path.exists(bp):
                    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bp))
                    return True
            return True
    return False


_CYRILLIC_READY: bool | None = None


def _ensure_fonts() -> tuple[str, str]:
    """Return (regular_font, bold_font) names, registering Cyrillic if possible."""
    global _CYRILLIC_READY  # noqa: PLW0603
    if _CYRILLIC_READY is None:
        _CYRILLIC_READY = _register_cyrillic_fonts()
    if _CYRILLIC_READY:
        return ("DejaVuSans", "DejaVuSans-Bold")
    return ("Helvetica", "Helvetica-Bold")


def _generate_stub_pdf(full_name: str, cert_number: str, year: int) -> bytes:
    """Generate a membership certificate PDF with Cyrillic support."""
    regular, bold = _ensure_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    from reportlab.lib.colors import HexColor

    border_color = HexColor("#1a5276")
    c.setStrokeColor(border_color)
    c.setLineWidth(3)
    c.rect(40, 40, width - 80, height - 80)
    c.setLineWidth(1)
    c.rect(50, 50, width - 100, height - 100)

    c.setFont(bold, 28)
    c.setFillColor(border_color)
    c.drawCentredString(width / 2, height - 140, "СЕРТИФИКАТ")

    c.setFont(regular, 16)
    c.setFillColor(HexColor("#2c3e50"))
    c.drawCentredString(width / 2, height - 175, "ЧЛЕНА АССОЦИАЦИИ ТРИХОЛОГОВ")

    c.setFont(regular, 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 220, "Настоящим подтверждается, что")

    c.setFont(bold, 22)
    c.setFillColor(HexColor("#1a5276"))
    c.drawCentredString(width / 2, height - 260, full_name)

    c.setFont(regular, 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 300, "является действительным членом")
    c.drawCentredString(width / 2, height - 320, "Ассоциации трихологов")

    c.setFont(regular, 11)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(width / 2, height - 380, f"Номер сертификата: {cert_number}")
    c.drawCentredString(width / 2, height - 400, f"Год: {year}")

    c.setFont(regular, 10)
    c.setFillColor(HexColor("#aaaaaa"))
    c.drawCentredString(width / 2, 80, "Ассоциация трихологов — trichology.ru")

    c.save()
    return buf.getvalue()


def generate_event_certificate_pdf(
    full_name: str, event_title: str, event_date: str, cert_number: str
) -> bytes:
    """Generate an event participation certificate PDF."""
    regular, bold = _ensure_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    from reportlab.lib.colors import HexColor

    border_color = HexColor("#1a5276")
    c.setStrokeColor(border_color)
    c.setLineWidth(3)
    c.rect(40, 40, width - 80, height - 80)
    c.setLineWidth(1)
    c.rect(50, 50, width - 100, height - 100)

    c.setFont(bold, 28)
    c.setFillColor(border_color)
    c.drawCentredString(width / 2, height - 140, "СЕРТИФИКАТ УЧАСТНИКА")

    c.setFont(regular, 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 190, "Настоящим подтверждается, что")

    c.setFont(bold, 22)
    c.setFillColor(HexColor("#1a5276"))
    c.drawCentredString(width / 2, height - 230, full_name)

    c.setFont(regular, 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 270, "принял(а) участие в мероприятии")

    c.setFont(bold, 16)
    c.setFillColor(HexColor("#2c3e50"))
    c.drawCentredString(width / 2, height - 310, event_title[:60])

    c.setFont(regular, 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 340, f"Дата: {event_date}")

    c.setFont(regular, 11)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(width / 2, height - 400, f"Номер: {cert_number}")

    c.setFont(regular, 10)
    c.setFillColor(HexColor("#aaaaaa"))
    c.drawCentredString(width / 2, 80, "Ассоциация трихологов — trichology.ru")

    c.save()
    return buf.getvalue()
