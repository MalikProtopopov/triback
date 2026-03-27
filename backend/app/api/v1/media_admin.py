"""Admin media library — upload images and list S3 keys for reuse."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.schemas.media_admin import MediaAssetListResponse, MediaUploadResponse
from app.services.media_admin_service import MediaAdminService

router = APIRouter(prefix="/admin")

ADMIN_MANAGER = require_role("admin", "manager")


@router.post(
    "/media",
    response_model=MediaUploadResponse,
    status_code=201,
    summary="Загрузить изображение в медиатеку",
    responses=error_responses(401, 403, 422),
)
async def upload_media(
    file: UploadFile = File(...),
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> MediaUploadResponse:
    """Загружает изображение в S3 и регистрирует запись. Возвращает ``s3_key`` для сохранения в контент-блоках."""
    uid = UUID(payload["sub"])
    svc = MediaAdminService(db)
    return await svc.upload(file, uid)


@router.get(
    "/media",
    response_model=MediaAssetListResponse,
    summary="Список изображений медиатеки",
    responses=error_responses(401, 403),
)
async def list_media(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> MediaAssetListResponse:
    """Пагинированный список зарегистрированных файлов с ``s3_key`` и публичным URL."""
    svc = MediaAdminService(db)
    return await svc.list_assets(limit=limit, offset=offset)
