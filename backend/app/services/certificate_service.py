"""Certificate service — list, download, generate PDF with QR, stamp, signature."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from uuid import UUID

import qrcode
import structlog
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.enums import DoctorStatus, SubscriptionStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.certificate_settings import CertificateSettings
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
        from sqlalchemy import or_

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

        qr_base = app_settings.CERTIFICATE_QR_BASE_URL or app_settings.FRONTEND_URL

        items: list[dict] = []
        for cert in certs:
            event_nested = None
            if cert.event_id:
                evt = event_map.get(cert.event_id)
                if evt:
                    event_nested = {"id": str(evt.id), "title": evt.title}

            download_url = f"/api/v1/certificates/{cert.id}/download"
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

        data = await self._download_s3_bytes(cert.file_url)
        if not data:
            raise NotFoundError("Certificate file not found in storage")
        return data, f"{cert.certificate_number}.pdf"

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def _get_cert_settings(self) -> CertificateSettings:
        result = await self.db.execute(
            select(CertificateSettings).where(CertificateSettings.id == 1)
        )
        settings = result.scalar_one_or_none()
        if not settings:
            settings = CertificateSettings(id=1)
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
        return settings

    async def _next_certificate_number(self, prefix: str, year: int) -> str:
        result = await self.db.execute(
            select(func.count()).select_from(Certificate).where(
                Certificate.certificate_type == "member",
                Certificate.year == year,
            )
        )
        count = result.scalar() or 0
        seq = count + 1
        return f"{prefix}-{year}-{seq:06d}"

    async def _download_s3_bytes(self, s3_key: str | None) -> bytes | None:
        if not s3_key:
            return None
        try:
            session = file_service._get_s3_session()
            async with session.client(**file_service._s3_client_kwargs()) as s3:
                resp = await s3.get_object(
                    Bucket=file_service.settings.S3_BUCKET, Key=s3_key
                )
                return await resp["Body"].read()
        except Exception:
            logger.warning("s3_asset_download_failed", s3_key=s3_key)
            return None

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

        cert_settings = await self._get_cert_settings()
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
            cert_number = await self._next_certificate_number(
                cert_settings.certificate_number_prefix, cert_year
            )

        logo_bytes = await self._download_s3_bytes(cert_settings.logo_s3_key)
        stamp_bytes = await self._download_s3_bytes(cert_settings.stamp_s3_key)
        signature_bytes = await self._download_s3_bytes(cert_settings.signature_s3_key)
        background_bytes = await self._download_s3_bytes(cert_settings.background_s3_key)

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
        session = file_service._get_s3_session()
        async with session.client(**file_service._s3_client_kwargs()) as s3:
            await s3.put_object(
                Bucket=file_service.settings.S3_BUCKET,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType="application/pdf",
            )

        if existing_cert:
            if existing_cert.file_url != s3_key:
                try:
                    await file_service.delete_file(existing_cert.file_url)
                except Exception:
                    pass
            existing_cert.file_url = s3_key
            existing_cert.is_active = True
            existing_cert.generated_at = datetime.now(UTC)  # type: ignore[assignment]
            await self.db.commit()
            await self.db.refresh(existing_cert)
            logger.info("certificate_regenerated", cert_id=str(existing_cert.id), number=cert_number)
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


# ======================================================================
# PDF Generation
# ======================================================================

def _register_cyrillic_fonts() -> tuple[str, str, str] | None:
    """Try to register DejaVu fonts and return (regular, bold, italic) names."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
    ]

    import os

    regular_path = None
    for path in font_paths:
        if os.path.exists(path):
            regular_path = path
            break

    if not regular_path:
        return None

    pdfmetrics.registerFont(TTFont("DejaVuSans", regular_path))
    regular = "DejaVuSans"
    bold = regular
    italic = regular

    bold_path = regular_path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
    if os.path.exists(bold_path):
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
        bold = "DejaVuSans-Bold"

    oblique_path = regular_path.replace("DejaVuSans.ttf", "DejaVuSans-Oblique.ttf")
    if os.path.exists(oblique_path):
        pdfmetrics.registerFont(TTFont("DejaVuSans-Oblique", oblique_path))
        italic = "DejaVuSans-Oblique"

    return regular, bold, italic


_CYRILLIC_FONTS: tuple[str, str, str] | None = None


def _ensure_fonts() -> tuple[str, str, str]:
    """Return (regular, bold, italic) font names."""
    global _CYRILLIC_FONTS  # noqa: PLW0603
    if _CYRILLIC_FONTS is None:
        result = _register_cyrillic_fonts()
        if result:
            _CYRILLIC_FONTS = result
        else:
            _CYRILLIC_FONTS = ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique")
    return _CYRILLIC_FONTS


def _bytes_to_image_reader(data: bytes | None) -> ImageReader | None:
    if not data:
        return None
    try:
        return ImageReader(io.BytesIO(data))
    except Exception:
        return None


def _generate_qr_image(url: str, box_size: int = 6) -> ImageReader:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _draw_border(c: canvas.Canvas, width: float, height: float) -> None:
    """Draw a brown ornamental double border."""
    brown = HexColor("#6B4226")
    c.setStrokeColor(brown)

    c.setLineWidth(3)
    c.rect(25, 25, width - 50, height - 50)

    c.setLineWidth(1.5)
    c.rect(32, 32, width - 64, height - 64)

    c.setLineWidth(0.5)
    c.rect(37, 37, width - 74, height - 74)


def _wrap_text(text: str, max_width: float, font_name: str, font_size: float) -> list[str]:
    """Simple word-wrap for centered text."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip()
        if stringWidth(test, font_name, font_size) <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines or [""]


def _generate_member_pdf(
    full_name: str,
    cert_number: str,
    year: int,
    body_text: str,
    validity_text: str,
    president_name: str,
    president_title: str,
    qr_url: str,
    logo_bytes: bytes | None = None,
    stamp_bytes: bytes | None = None,
    signature_bytes: bytes | None = None,
    background_bytes: bytes | None = None,
) -> bytes:
    regular, bold, italic = _ensure_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    _draw_border(c, width, height)

    # Background watermark
    bg_img = _bytes_to_image_reader(background_bytes)
    if bg_img:
        c.saveState()
        c.setFillAlpha(0.08)
        bg_w, bg_h = 400, 250
        c.drawImage(
            bg_img,
            (width - bg_w) / 2, (height - bg_h) / 2 - 30,
            width=bg_w, height=bg_h,
            mask="auto",
            preserveAspectRatio=True,
        )
        c.restoreState()

    y_cursor = height - 70

    # Logo
    logo_img = _bytes_to_image_reader(logo_bytes)
    if logo_img:
        logo_w, logo_h = 90, 90
        c.drawImage(
            logo_img,
            (width - logo_w) / 2, y_cursor - logo_h,
            width=logo_w, height=logo_h,
            mask="auto",
            preserveAspectRatio=True,
        )
        y_cursor -= logo_h + 15
    else:
        y_cursor -= 20

    # "СЕРТИФИКАТ" heading
    dark_brown = HexColor("#5C3A1E")
    c.setFont(italic, 32)
    c.setFillColor(dark_brown)
    c.drawCentredString(width / 2, y_cursor, "СЕРТИФИКАТ")
    y_cursor -= 45

    # Doctor full name
    c.setFont(bold, 22)
    c.setFillColor(HexColor("#1a1a1a"))
    name_lines = _wrap_text(full_name, width - 120, bold, 22)
    for line in name_lines:
        c.drawCentredString(width / 2, y_cursor, line)
        y_cursor -= 30
    y_cursor -= 10

    # Body text (multi-line, centered)
    text_color = HexColor("#333333")
    c.setFont(regular, 11)
    c.setFillColor(text_color)
    max_text_width = width - 120
    body_lines = _wrap_text(body_text, max_text_width, regular, 11)
    for line in body_lines:
        c.drawCentredString(width / 2, y_cursor, line)
        y_cursor -= 16
    y_cursor -= 10

    # Validity text
    if validity_text:
        c.setFont(bold, 13)
        c.setFillColor(dark_brown)
        c.drawCentredString(width / 2, y_cursor, validity_text)
        y_cursor -= 30

    # Bottom section: QR left, stamp+signature right
    bottom_y = 60
    margin_x = 55

    # QR code — bottom left
    qr_img = _generate_qr_image(qr_url, box_size=5)
    qr_size = 85
    c.drawImage(qr_img, margin_x, bottom_y, width=qr_size, height=qr_size, mask="auto")
    c.setFont(regular, 7)
    c.setFillColor(HexColor("#888888"))
    c.drawString(margin_x, bottom_y - 10, "проверить сертификат")

    # Stamp + Signature — bottom right
    right_block_x = width - margin_x - 180
    stamp_img = _bytes_to_image_reader(stamp_bytes)
    sig_img = _bytes_to_image_reader(signature_bytes)

    if stamp_img:
        stamp_size = 100
        c.drawImage(
            stamp_img,
            right_block_x, bottom_y + 15,
            width=stamp_size, height=stamp_size,
            mask="auto",
            preserveAspectRatio=True,
        )

    if sig_img:
        sig_w, sig_h = 120, 40
        c.drawImage(
            sig_img,
            right_block_x + 60, bottom_y + 55,
            width=sig_w, height=sig_h,
            mask="auto",
            preserveAspectRatio=True,
        )

    # President info text — bottom right
    c.setFont(regular, 9)
    c.setFillColor(HexColor("#333333"))
    pres_x = right_block_x + 10
    if president_title:
        c.drawString(pres_x, bottom_y + 5, president_title)
    if president_name:
        c.drawString(pres_x, bottom_y - 8, president_name)

    c.save()
    return buf.getvalue()


def generate_event_certificate_pdf(
    full_name: str, event_title: str, event_date: str, cert_number: str
) -> bytes:
    regular, bold, italic = _ensure_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    _draw_border(c, width, height)

    c.setFont(italic, 28)
    c.setFillColor(HexColor("#5C3A1E"))
    c.drawCentredString(width / 2, height - 140, "СЕРТИФИКАТ УЧАСТНИКА")

    c.setFont(regular, 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 190, "Настоящим подтверждается, что")

    c.setFont(bold, 22)
    c.setFillColor(HexColor("#1a1a1a"))
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
    c.drawCentredString(width / 2, 80, "Профессиональное общество трихологов")

    c.save()
    return buf.getvalue()
