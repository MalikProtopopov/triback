"""Admin endpoints for certificate settings and certificate management."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.models.certificates import Certificate
from app.models.profiles import DoctorProfile
from app.schemas.certificate_settings import (
    CertificateSettingsResponse,
    CertificateSettingsUpdateRequest,
)
from app.services import file_service
from app.services.certificate_settings_service import CertificateSettingsService

router = APIRouter(prefix="/admin")

ADMIN_ONLY = require_role("admin")
ADMIN_MANAGER = require_role("admin", "manager")


# ══ Certificate Settings ═════════════════════════════════════════


@router.get(
    "/certificate-settings",
    response_model=CertificateSettingsResponse,
    summary="Получить настройки сертификатов",
    responses=error_responses(401, 403),
)
async def get_certificate_settings(
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = CertificateSettingsService(db)
    settings = await svc.get_settings()
    return svc.to_response(settings)


@router.patch(
    "/certificate-settings",
    response_model=CertificateSettingsResponse,
    summary="Обновить настройки сертификатов",
    responses=error_responses(401, 403, 422),
)
async def update_certificate_settings(
    body: CertificateSettingsUpdateRequest,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = CertificateSettingsService(db)
    settings = await svc.update_settings(body.model_dump(exclude_none=True))
    return svc.to_response(settings)


@router.post(
    "/certificate-settings/logo",
    response_model=CertificateSettingsResponse,
    summary="Загрузить логотип для сертификата",
    responses=error_responses(401, 403, 422),
)
async def upload_certificate_logo(
    file: UploadFile,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = CertificateSettingsService(db)
    settings = await svc.upload_asset("logo_s3_key", file)
    return svc.to_response(settings)


@router.post(
    "/certificate-settings/stamp",
    response_model=CertificateSettingsResponse,
    summary="Загрузить печать для сертификата",
    responses=error_responses(401, 403, 422),
)
async def upload_certificate_stamp(
    file: UploadFile,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = CertificateSettingsService(db)
    settings = await svc.upload_asset("stamp_s3_key", file)
    return svc.to_response(settings)


@router.post(
    "/certificate-settings/signature",
    response_model=CertificateSettingsResponse,
    summary="Загрузить подпись для сертификата",
    responses=error_responses(401, 403, 422),
)
async def upload_certificate_signature(
    file: UploadFile,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = CertificateSettingsService(db)
    settings = await svc.upload_asset("signature_s3_key", file)
    return svc.to_response(settings)


@router.post(
    "/certificate-settings/background",
    response_model=CertificateSettingsResponse,
    summary="Загрузить фон/watermark для сертификата",
    responses=error_responses(401, 403, 422),
)
async def upload_certificate_background(
    file: UploadFile,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = CertificateSettingsService(db)
    settings = await svc.upload_asset("background_s3_key", file)
    return svc.to_response(settings)


# ══ Doctor Certificate Management ════════════════════════════════


@router.get(
    "/doctors/{doctor_id}/certificates",
    summary="Список сертификатов врача",
    responses=error_responses(401, 403, 404),
)
async def list_doctor_certificates(
    doctor_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.id == doctor_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Doctor profile not found")

    certs_result = await db.execute(
        select(Certificate)
        .where(Certificate.doctor_profile_id == doctor_id)
        .order_by(Certificate.generated_at.desc())
    )
    certs = certs_result.scalars().all()

    items = []
    for cert in certs:
        items.append({
            "id": str(cert.id),
            "certificate_type": cert.certificate_type,
            "year": cert.year,
            "certificate_number": cert.certificate_number,
            "is_active": cert.is_active,
            "generated_at": cert.generated_at.isoformat(),
            "download_url": f"/api/v1/admin/certificates/{cert.id}/download",
        })
    return items


@router.get(
    "/certificates/{certificate_id}/download",
    summary="Скачать/предпросмотр сертификата",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF файл сертификата"},
        **error_responses(401, 403, 404),
    },
)
async def admin_download_certificate(
    certificate_id: UUID,
    disposition: str = Query("inline", pattern="^(inline|attachment)$"),
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    cert = await db.get(Certificate, certificate_id)
    if not cert:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Certificate not found")

    if not cert.file_url:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Certificate file not found in storage")

    session = file_service._get_s3_session()
    async with session.client(**file_service._s3_client_kwargs()) as s3:
        resp = await s3.get_object(
            Bucket=file_service.settings.S3_BUCKET, Key=cert.file_url
        )
        data: bytes = await resp["Body"].read()

    filename = f"{cert.certificate_number}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
        },
    )


@router.post(
    "/doctors/{doctor_id}/certificates/regenerate",
    summary="Перегенерировать сертификат врача",
    responses=error_responses(401, 403, 404, 422),
)
async def regenerate_doctor_certificate(
    doctor_id: UUID,
    body: dict[str, Any],
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    year = body.get("year", datetime.now(UTC).year)

    result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.id == doctor_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Doctor profile not found")

    from app.services.certificate_service import CertificateService
    svc = CertificateService(db)
    cert = await svc.generate_membership_certificate(doctor_id, year)
    return {
        "id": str(cert.id),
        "certificate_type": cert.certificate_type,
        "year": cert.year,
        "certificate_number": cert.certificate_number,
        "is_active": cert.is_active,
        "generated_at": cert.generated_at.isoformat(),
        "download_url": f"/api/v1/admin/certificates/{cert.id}/download",
    }


@router.patch(
    "/certificates/{certificate_id}",
    summary="Обновить статус сертификата",
    responses=error_responses(401, 403, 404, 422),
)
async def update_certificate(
    certificate_id: UUID,
    body: dict[str, Any],
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    cert = await db.get(Certificate, certificate_id)
    if not cert:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Certificate not found")

    if "is_active" in body:
        cert.is_active = bool(body["is_active"])

    await db.commit()
    await db.refresh(cert)
    return {
        "id": str(cert.id),
        "certificate_type": cert.certificate_type,
        "year": cert.year,
        "certificate_number": cert.certificate_number,
        "is_active": cert.is_active,
        "generated_at": cert.generated_at.isoformat(),
        "download_url": f"/api/v1/admin/certificates/{cert.id}/download",
    }


@router.post(
    "/certificate-settings/regenerate-all",
    summary="Перегенерировать все активные сертификаты текущего года",
    responses=error_responses(401, 403),
)
async def regenerate_all_certificates(
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    year = datetime.now(UTC).year
    result = await db.execute(
        select(Certificate).where(
            Certificate.certificate_type == "member",
            Certificate.year == year,
            Certificate.is_active.is_(True),
        )
    )
    certs = result.scalars().all()

    from app.tasks.certificate_tasks import generate_member_certificate_task

    dispatched = 0
    for cert in certs:
        await generate_member_certificate_task.kiq(
            str(cert.doctor_profile_id), year
        )
        dispatched += 1

    return {"dispatched": dispatched, "year": year}
