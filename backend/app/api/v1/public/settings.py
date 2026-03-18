"""Public settings endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.settings_admin import PublicSettingsResponse
from app.services.settings_service import SettingsAdminService

router = APIRouter()


@router.get(
    "/settings/public",
    response_model=PublicSettingsResponse,
    summary="Публичные настройки",
)
async def get_public_settings(
    db: AsyncSession = Depends(get_db_session),
) -> PublicSettingsResponse:
    """Контакты, ссылка на бота и др. публичные настройки. Без авторизации."""
    svc = SettingsAdminService(db)
    data = await svc.get_public_settings()
    return PublicSettingsResponse(data=data)
