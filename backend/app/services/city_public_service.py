"""Public city service — list and detail for guest access."""

from __future__ import annotations

import json
from typing import Any

import structlog
from redis.asyncio import Redis
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DoctorStatus, SubscriptionStatus
from app.core.exceptions import NotFoundError
from app.models.cities import City
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Subscription
from app.schemas.public import CityResponse, CityWithDoctorsResponse

logger = structlog.get_logger(__name__)

CITIES_CACHE_TTL = 300


def _has_active_subscription() -> Any:
    return (
        select(Subscription.id)
        .where(
            Subscription.user_id == DoctorProfile.user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            or_(
                Subscription.ends_at.is_(None),
                Subscription.ends_at > func.now(),
            ),
        )
        .correlate(DoctorProfile)
        .exists()
    )


class CityPublicService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    async def list_cities(self, *, with_doctors: bool = False) -> dict[str, Any]:
        cache_key = f"cache:cities:{with_doctors}"
        cached = await self.redis.get(cache_key)
        if cached:
            parsed: dict[str, Any] = json.loads(cached)
            return parsed

        if with_doctors:
            items = await self._cities_with_doctors()
        else:
            items = await self._cities_plain()

        result: dict[str, Any] = {"data": items}
        await self.redis.set(cache_key, json.dumps(result, default=str), ex=CITIES_CACHE_TTL)
        return result

    async def _cities_plain(self) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(City).where(City.is_active.is_(True)).order_by(City.name)
            )
        ).scalars().all()
        return [
            CityResponse(id=c.id, name=c.name, slug=c.slug).model_dump(mode="json")
            for c in rows
        ]

    async def _cities_with_doctors(self) -> list[dict[str, Any]]:
        doctor_count = (
            func.count(DoctorProfile.id)
            .filter(DoctorProfile.status == DoctorStatus.ACTIVE, _has_active_subscription())
            .label("doctors_count")
        )
        q = (
            select(City.id, City.name, City.slug, doctor_count)
            .outerjoin(DoctorProfile, DoctorProfile.city_id == City.id)
            .where(City.is_active.is_(True))
            .group_by(City.id)
            .having(doctor_count > 0)
            .order_by(City.name)
        )
        rows = (await self.db.execute(q)).all()
        return [
            CityWithDoctorsResponse(
                id=r.id, name=r.name, slug=r.slug, doctors_count=r.doctors_count
            ).model_dump(mode="json")
            for r in rows
        ]

    async def get_city(self, slug: str) -> CityWithDoctorsResponse:
        doctor_count = (
            func.count(DoctorProfile.id)
            .filter(DoctorProfile.status == DoctorStatus.ACTIVE, _has_active_subscription())
            .label("doctors_count")
        )
        q = (
            select(City.id, City.name, City.slug, doctor_count)
            .outerjoin(DoctorProfile, DoctorProfile.city_id == City.id)
            .where(and_(City.is_active.is_(True), City.slug == slug))
            .group_by(City.id)
        )
        row = (await self.db.execute(q)).one_or_none()
        if not row:
            raise NotFoundError("City not found")
        return CityWithDoctorsResponse(
            id=row.id, name=row.name, slug=row.slug, doctors_count=row.doctors_count
        )
