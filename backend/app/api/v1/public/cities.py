"""Public city endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.redis import get_redis
from app.schemas.public import CityWithDoctorsResponse
from app.services.city_public_service import CityPublicService

router = APIRouter()


@router.get("/cities", response_model=dict[str, Any], summary="Список городов")
async def list_cities(
    with_doctors: bool = Query(False, description="Если true — только города с врачами, с подсчётом"),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Возвращает список городов. С `with_doctors=true` дополнительно
    считает количество активных врачей в каждом городе."""
    svc = CityPublicService(db, redis)
    return await svc.list_cities(with_doctors=with_doctors)


@router.get(
    "/cities/{slug}",
    response_model=CityWithDoctorsResponse,
    summary="Город по slug",
    responses=error_responses(404),
)
async def get_city(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> CityWithDoctorsResponse:
    """Информация о городе по slug (включая количество врачей).

    - **404** — город не найден
    """
    svc = CityPublicService(db, redis)
    return await svc.get_city(slug)
