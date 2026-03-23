"""Certificate settings row and sequential certificate numbers."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate_settings import CertificateSettings
from app.models.certificates import Certificate


async def get_cert_settings(db: AsyncSession) -> CertificateSettings:
    result = await db.execute(
        select(CertificateSettings).where(CertificateSettings.id == 1)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = CertificateSettings(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def next_certificate_number(db: AsyncSession, prefix: str, year: int) -> str:
    result = await db.execute(
        select(func.count()).select_from(Certificate).where(
            Certificate.certificate_type == "member",
            Certificate.year == year,
        )
    )
    count = result.scalar() or 0
    seq = count + 1
    return f"{prefix}-{year}-{seq:06d}"
