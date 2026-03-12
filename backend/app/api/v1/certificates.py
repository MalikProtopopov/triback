"""Certificates router — doctor-facing endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_role
from app.schemas.certificates import CertificateListItem
from app.services.certificate_service import CertificateService

router = APIRouter(prefix="/certificates")


@router.get("", response_model=list[CertificateListItem])
async def list_certificates(
    payload: dict[str, Any] = require_role("doctor"),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    svc = CertificateService(db)
    return await svc.list_certificates(payload["sub"])


@router.get("/{certificate_id}/download")
async def download_certificate(
    certificate_id: UUID,
    payload: dict[str, Any] = require_role("doctor"),
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    svc = CertificateService(db)
    url = await svc.download_certificate(payload["sub"], certificate_id)
    return RedirectResponse(url=url, status_code=302)
